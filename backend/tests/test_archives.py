import asyncio


async def test_archive_crud_pagination_and_inactive(authenticated_client):
    client = authenticated_client
    created = await client.post("/api/v1/stores", json={"code": " shop01 ", "name": "一号店"})
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["code"] == "SHOP01"
    assert (await client.patch(f'/api/v1/stores/{data["id"]}', json={"name": "新店名", "status": "INACTIVE"})).status_code == 200
    result = (await client.get("/api/v1/stores?keyword=新店名&status=INACTIVE")).json()["data"]
    assert result["total"] == 1
    assert result["page_size"] == 20
    assert (await client.get("/api/v1/stores?page_size=101")).status_code == 422
    assert (await client.post("/api/v1/suppliers", json={"code": "SUP01", "name": "服装供应商"})).status_code == 201


async def test_store_warehouse_binding_rules(authenticated_client):
    client = authenticated_client
    store = (await client.post("/api/v1/stores", json={"code": "S1", "name": "门店"})).json()["data"]
    base = {"code": "WH1", "name": "店仓", "type": "STORE"}
    assert (await client.post("/api/v1/warehouses", json=base)).status_code == 422
    base["store_id"] = store["id"]
    assert (await client.post("/api/v1/warehouses", json=base)).status_code == 201
    base["code"] = "WH2"
    assert (await client.post("/api/v1/warehouses", json=base)).status_code == 409
    base["type"] = "CENTRAL"
    assert (await client.post("/api/v1/warehouses", json=base)).status_code == 422


async def test_concurrent_duplicate_code(authenticated_client):
    client = authenticated_client
    results = await asyncio.gather(*[client.post("/api/v1/stores", json={"code": "ONE", "name": "门店"}) for _ in range(2)])
    assert sorted(result.status_code for result in results) == [201, 409]
    assert (await client.get("/api/v1/stores")).json()["data"]["total"] == 1


async def test_archive_requires_admin(client):
    assert (await client.get("/api/v1/stores")).status_code == 401
    assert (await client.post("/api/v1/stores", json={"code": "X", "name": "店"})).status_code == 401
