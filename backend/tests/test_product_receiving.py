import asyncio
from uuid import uuid4

import pytest


async def receiving_context(client, matrix, quantity=3, cost="100.00"):
    supplier = (
        await client.post("/api/v1/suppliers", json={"code": "IN-SUP", "name": "进货供应商"})
    ).json()["data"]
    warehouse = (
        await client.post("/api/v1/warehouses", json={"code": "IN-WH", "name": "进货总仓"})
    ).json()["data"]
    return {
        "request_id": str(uuid4()),
        "supplier_id": supplier["id"],
        "warehouse_id": warehouse["id"],
        "unit_cost": cost,
        "quantities": [
            {
                "color_id": matrix["skus"][0]["color_id"],
                "size_id": matrix["skus"][0]["size_id"],
                "quantity": quantity,
            }
        ],
    }


async def test_product_and_purchase_stock_ledger_commit_together(authenticated_client, matrix):
    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    body = {**matrix, "receiving": receiving}
    result = await client.post("/api/v1/products", json=body)
    assert result.status_code == 201
    product = result.json()["data"]
    receipt = (await client.get("/api/v1/purchase-receipts")).json()["data"]
    assert receipt["total"] == 1
    detail = (await client.get(f"/api/v1/purchase-receipts/{receipt['items'][0]['id']}")).json()[
        "data"
    ]
    assert (
        detail["status"] == "POSTED"
        and detail["total_quantity"] == 3
        and detail["total_amount"] == "300.00"
    )
    stocks = (await client.get("/api/v1/inventory")).json()["data"]["items"]
    assert len(stocks) == 1 and stocks[0]["quantity"] == 3
    assert stocks[0]["average_cost"] == "100.0000" and stocks[0]["total_cost"] == "300.0000"
    movement = (await client.get("/api/v1/inventory/movements")).json()["data"]["items"][0]
    assert (movement["before_quantity"], movement["quantity"], movement["after_quantity"]) == (
        0,
        3,
        3,
    )
    # Later receipt uses purchase cost, not retail price, and updates weighted average.
    second = {
        **receiving,
        "request_id": str(uuid4()),
        "unit_cost": "160.00",
        "quantities": [{**receiving["quantities"][0], "quantity": 2}],
    }
    assert (
        await client.patch(f"/api/v1/products/{product['id']}", json={"receiving": second})
    ).status_code == 200
    stock = (await client.get("/api/v1/inventory")).json()["data"]["items"][0]
    assert (stock["quantity"], stock["average_cost"], stock["total_cost"]) == (
        5,
        "124.0000",
        "620.0000",
    )


async def test_request_replay_and_concurrent_receipts_never_double_stock(
    authenticated_client, matrix
):
    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    body = {**matrix, "receiving": receiving}
    responses = await asyncio.gather(
        *[client.post("/api/v1/products", json=body) for _ in range(2)]
    )
    assert [response.status_code for response in responses] == [201, 201]
    product_id = responses[0].json()["data"]["id"]
    assert responses[1].json()["data"]["id"] == product_id
    assert (await client.get("/api/v1/inventory")).json()["data"]["items"][0]["quantity"] == 3
    assert (
        await client.post("/api/v1/products", json={**body, "name": "不能改请求"})
    ).status_code == 409
    requests = [{**receiving, "request_id": str(uuid4())} for _ in range(2)]
    results = await asyncio.gather(
        *[
            client.patch(f"/api/v1/products/{product_id}", json={"receiving": request})
            for request in requests
        ]
    )
    assert all(result.status_code == 200 for result in results)
    assert (await client.get("/api/v1/inventory")).json()["data"]["items"][0]["quantity"] == 9
    assert (await client.get("/api/v1/purchase-receipts")).json()["data"]["total"] == 3


async def test_save_without_receiving_does_not_create_inventory(authenticated_client, matrix):
    client = authenticated_client
    assert (await client.post("/api/v1/products", json=matrix)).status_code == 201
    assert (await client.get("/api/v1/inventory")).json()["data"]["total"] == 0
    assert (await client.get("/api/v1/purchase-receipts")).json()["data"]["total"] == 0


@pytest.mark.parametrize("failure", ["barcode", "unknown-sku", "fraction", "warehouse"])
async def test_invalid_receiving_rolls_back_all_product_changes(
    authenticated_client, matrix, failure
):
    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    body = {**matrix, "skus": [dict(cell) for cell in matrix["skus"]], "receiving": receiving}
    expected = 422
    if failure == "barcode":
        body["skus"][0]["barcode"] = "DUPLICATE"
        body["skus"][1]["barcode"] = "DUPLICATE"
        expected = 409
    elif failure == "unknown-sku":
        receiving["quantities"][0]["size_id"] = 999999
    elif failure == "fraction":
        receiving["quantities"][0]["quantity"] = 1.5
    else:
        receiving["warehouse_id"] = 999999
    assert (await client.post("/api/v1/products", json=body)).status_code == expected
    assert (await client.get("/api/v1/products")).json()["data"]["total"] == 0
    assert (await client.get("/api/v1/inventory")).json()["data"]["total"] == 0
    assert (await client.get("/api/v1/purchase-receipts")).json()["data"]["total"] == 0


async def test_color_append_receiving_is_one_transaction(authenticated_client, matrix):
    client = authenticated_client
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    receiving = await receiving_context(client, matrix)
    color = (
        await client.post("/api/v1/colors", json={"code": "RECEIVE", "name": "新进货色"})
    ).json()["data"]
    size_ids = list(dict.fromkeys(sku["size_id"] for sku in product["skus"]))
    additions = [
        {"color_id": color["id"], "size_id": size, "retail_price": "199.00"} for size in size_ids
    ]
    receiving["quantities"] = [
        {"color_id": cell["color_id"], "size_id": cell["size_id"], "quantity": 2}
        for cell in additions
    ]
    result = await client.patch(
        f"/api/v1/products/{product['id']}", json={"new_skus": additions, "receiving": receiving}
    )
    assert result.status_code == 200 and len(result.json()["data"]["skus"]) == 16
    assert (
        sum(
            item["quantity"]
            for item in (await client.get("/api/v1/inventory")).json()["data"]["items"]
        )
        == 8
    )
    replay = await client.patch(
        f"/api/v1/products/{product['id']}", json={"new_skus": additions, "receiving": receiving}
    )
    assert replay.status_code == 200
    assert (await client.get("/api/v1/purchase-receipts")).json()["data"]["total"] == 1


async def test_parallel_receipts_different_suppliers_and_warehouses(
    authenticated_client, matrix, monkeypatch
):
    from app.modules.catalog import service

    client = authenticated_client
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    first = await receiving_context(client, matrix)
    supplier = (
        await client.post("/api/v1/suppliers", json={"code": "SECOND", "name": "第二供应商"})
    ).json()["data"]
    warehouse = (
        await client.post("/api/v1/warehouses", json={"code": "SECOND", "name": "第二仓库"})
    ).json()["data"]
    second = {
        **first,
        "request_id": str(uuid4()),
        "supplier_id": supplier["id"],
        "warehouse_id": warehouse["id"],
    }
    original = service.prepare_receipt
    ready = asyncio.Event()
    waiting = 0

    async def synchronized_prepare(*args, **kwargs):
        nonlocal waiting
        result = await original(*args, **kwargs)
        waiting += 1
        if waiting == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 5)
        return result

    monkeypatch.setattr(service, "prepare_receipt", synchronized_prepare)
    results = await asyncio.gather(
        *[
            client.patch(f"/api/v1/products/{product['id']}", json={"receiving": body})
            for body in [first, second]
        ]
    )
    assert [result.status_code for result in results] == [200, 200]
    assert (
        sum(
            item["quantity"]
            for item in (await client.get("/api/v1/inventory")).json()["data"]["items"]
        )
        == 6
    )


async def test_receipt_total_amount_overflow_returns_validation_error(authenticated_client, matrix):
    client = authenticated_client
    receiving = await receiving_context(client, matrix, cost="9999999999.99")
    extra = (await client.post("/api/v1/colors", json={"code": "EXTRA", "name": "第四色"})).json()[
        "data"
    ]
    group = (
        await client.post(
            "/api/v1/size-groups",
            json={
                "code": "MANY",
                "name": "26码",
                "sizes": [{"code": f"S{i}", "name": f"S{i}"} for i in range(26)],
            },
        )
    ).json()["data"]
    color_ids = [*matrix["color_ids"], extra["id"]]
    cells = [
        {"color_id": color, "size_id": size["id"], "retail_price": "1.00"}
        for color in color_ids
        for size in group["sizes"]
    ]
    receiving["quantities"] = [
        {"color_id": cell["color_id"], "size_id": cell["size_id"], "quantity": 1000000}
        for cell in cells[:101]
    ]
    body = {
        **matrix,
        "size_group_id": group["id"],
        "color_ids": color_ids,
        "skus": cells,
        "receiving": receiving,
    }
    result = await client.post("/api/v1/products", json=body)
    assert result.status_code == 422
    assert "金额" in result.json()["message"]
    assert (await client.get("/api/v1/products")).json()["data"]["total"] == 0
    assert (await client.get("/api/v1/inventory")).json()["data"]["total"] == 0
    assert (await client.get("/api/v1/purchase-receipts")).json()["data"]["total"] == 0
