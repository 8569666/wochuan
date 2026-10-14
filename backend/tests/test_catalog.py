import asyncio

import pytest
from sqlalchemy import func, select

from app.modules.catalog.models import Product, SKU


@pytest.fixture
async def matrix(authenticated_client):
    client = authenticated_client
    colors = []
    for i, name in enumerate(["米白", "樱花粉", "曜石黑"], 1):
        response = await client.post("/api/v1/colors", json={"code": f"C{i}", "name": name})
        assert response.status_code == 201
        colors.append(response.json()["data"])
    group = await client.post("/api/v1/size-groups", json={"code": "WOMEN", "name": "女装标准尺码", "sizes": [{"code": code, "name": code} for code in ["S", "M", "L", "XL"]]})
    assert group.status_code == 201
    group = group.json()["data"]
    return {"code": "2026S-DR088", "name": "法式收腰连衣裙", "category": "连衣裙", "year": 2026, "season": "春夏", "tag_price": "599.00", "purchase_base_price": "140.00", "color_ids": [c["id"] for c in colors], "size_group_id": group["id"], "skus": [{"color_id": c["id"], "size_id": s["id"], "retail_price": "599.00"} for c in colors for s in group["sizes"]]}


async def test_three_colors_four_sizes_create_twelve_skus(authenticated_client, matrix):
    response = await authenticated_client.post("/api/v1/products", json=matrix)
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["skus"]) == 12
    assert len({s["code"] for s in data["skus"]}) == 12
    assert all(s["barcode"] == s["code"] and s["retail_price"] == "599.00" for s in data["skus"])
    barcode = data["skus"][0]["barcode"]
    assert (await authenticated_client.get(f"/api/v1/products?keyword={barcode}")).json()["data"]["total"] == 1
    assert (await authenticated_client.get(f'/api/v1/products/{data["id"]}/skus')).status_code == 200


async def test_duplicate_barcode_rolls_back_whole_product(authenticated_client, matrix, db_session):
    matrix["skus"][0]["barcode"] = "DUPLICATE"
    matrix["skus"][1]["barcode"] = "DUPLICATE"
    response = await authenticated_client.post("/api/v1/products", json=matrix)
    assert response.status_code == 409
    assert await db_session.scalar(select(func.count()).select_from(Product)) == 0
    assert await db_session.scalar(select(func.count()).select_from(SKU)) == 0


async def test_missing_or_repeated_matrix_cell_is_422(authenticated_client, matrix):
    missing = dict(matrix, skus=matrix["skus"][:-1])
    assert (await authenticated_client.post("/api/v1/products", json=missing)).status_code == 422
    repeated = dict(matrix, skus=matrix["skus"][:-1] + [matrix["skus"][0]])
    assert (await authenticated_client.post("/api/v1/products", json=repeated)).status_code == 422


async def test_decimal_precision_and_code_length(authenticated_client, matrix):
    for price in ["-1", "1.001"]:
        assert (await authenticated_client.post("/api/v1/products", json=dict(matrix, tag_price=price))).status_code == 422
    assert (await authenticated_client.post("/api/v1/products", json=dict(matrix, code="X" * 64))).status_code == 422


async def test_referenced_dictionary_code_immutable(authenticated_client, matrix):
    assert (await authenticated_client.post("/api/v1/products", json=matrix)).status_code == 201
    response = await authenticated_client.patch(f'/api/v1/colors/{matrix["color_ids"][0]}', json={"code": "NEW"})
    assert response.status_code == 409


async def test_inactive_dictionary_preserves_existing_detail(authenticated_client, matrix):
    product = (await authenticated_client.post("/api/v1/products", json=matrix)).json()["data"]
    await authenticated_client.patch(f'/api/v1/colors/{matrix["color_ids"][0]}', json={"status": "INACTIVE"})
    detail = (await authenticated_client.get(f'/api/v1/products/{product["id"]}')).json()["data"]
    assert len(detail["skus"]) == 12
    matrix["code"] = "ANOTHER"
    assert (await authenticated_client.post("/api/v1/products", json=matrix)).status_code == 422


async def test_concurrent_product_code_unique(authenticated_client, matrix):
    responses = await asyncio.gather(*[authenticated_client.post("/api/v1/products", json=matrix) for _ in range(2)])
    assert sorted(r.status_code for r in responses) == [201, 409]
