import asyncio

from sqlalchemy import func, select

from app.modules.catalog.models import SKU, Product


async def test_three_colors_four_sizes_create_twelve_skus(authenticated_client, matrix):
    response = await authenticated_client.post("/api/v1/products", json=matrix)
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["skus"]) == 12
    assert len({s["code"] for s in data["skus"]}) == 12
    assert all(s["barcode"] == s["code"] and s["retail_price"] == "599.00" for s in data["skus"])
    barcode = data["skus"][0]["barcode"]
    assert (await authenticated_client.get(f"/api/v1/products?keyword={barcode}")).json()["data"][
        "total"
    ] == 1
    assert (
        await authenticated_client.get(f"/api/v1/products/{data['id']}/skus")
    ).status_code == 200


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
        assert (
            await authenticated_client.post("/api/v1/products", json=dict(matrix, tag_price=price))
        ).status_code == 422
    assert (
        await authenticated_client.post("/api/v1/products", json=dict(matrix, code="X" * 64))
    ).status_code == 422


async def test_referenced_dictionary_code_immutable(authenticated_client, matrix):
    assert (await authenticated_client.post("/api/v1/products", json=matrix)).status_code == 201
    response = await authenticated_client.patch(
        f"/api/v1/colors/{matrix['color_ids'][0]}", json={"code": "NEW"}
    )
    assert response.status_code == 409


async def test_inactive_dictionary_preserves_existing_detail(authenticated_client, matrix):
    product = (await authenticated_client.post("/api/v1/products", json=matrix)).json()["data"]
    await authenticated_client.patch(
        f"/api/v1/colors/{matrix['color_ids'][0]}", json={"status": "INACTIVE"}
    )
    detail = (await authenticated_client.get(f"/api/v1/products/{product['id']}")).json()["data"]
    assert len(detail["skus"]) == 12
    matrix["code"] = "ANOTHER"
    assert (await authenticated_client.post("/api/v1/products", json=matrix)).status_code == 422


async def test_concurrent_product_code_unique(authenticated_client, matrix):
    responses = await asyncio.gather(
        *[authenticated_client.post("/api/v1/products", json=matrix) for _ in range(2)]
    )
    assert sorted(r.status_code for r in responses) == [201, 409]


async def test_unreferenced_group_sizes_can_be_edited(authenticated_client, matrix):
    response = await authenticated_client.patch(
        f"/api/v1/size-groups/{matrix['size_group_id']}",
        json={"sizes": [{"code": "FREE", "name": "均码"}]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["sizes"][0]["status"] == "ACTIVE"


async def test_product_price_updates_without_changing_dimensions(authenticated_client, matrix):
    client = authenticated_client
    data = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    response = await client.patch(
        f"/api/v1/products/{data['id']}",
        json={
            "name": "更新款名",
            "sku_prices": [{"id": data["skus"][0]["id"], "retail_price": "199.00"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["skus"][0]["retail_price"] == "199.00"
    assert len(response.json()["data"]["skus"]) == 12
