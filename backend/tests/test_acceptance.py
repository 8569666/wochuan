from sqlalchemy import func, select

from app.modules.audit.models import AuditLog
from app.modules.catalog.models import SKU


async def test_foundation_end_to_end_persistent_records(authenticated_client, matrix, db_session):
    client = authenticated_client
    stores = []
    for code, name in [("SHOP01", "杭州旗舰店"), ("SHOP02", "滨江标准店")]:
        response = await client.post("/api/v1/stores", json={"code": code, "name": name})
        assert response.status_code == 201
        stores.append(response.json()["data"])
    assert (
        await client.post("/api/v1/warehouses", json={"code": "CENTRAL", "name": "中央总仓"})
    ).status_code == 201
    for index, store in enumerate(stores):
        assert (
            await client.post(
                "/api/v1/warehouses",
                json={
                    "code": f"WH{index}",
                    "name": store["name"] + "仓",
                    "type": "STORE",
                    "store_id": store["id"],
                },
            )
        ).status_code == 201
    assert (
        await client.post("/api/v1/suppliers", json={"code": "SUP01", "name": "杭州服装供应商"})
    ).status_code == 201
    result = await client.post("/api/v1/products", json=matrix)
    assert result.status_code == 201
    product = result.json()["data"]
    assert len(product["skus"]) == 12
    detail = await client.get(f"/api/v1/products/{product['id']}")
    assert detail.json()["data"]["code"] == matrix["code"]
    assert await db_session.scalar(select(func.count()).select_from(SKU)) == 12
    assert await db_session.scalar(select(func.count()).select_from(AuditLog)) >= 10
    counts = (await client.get("/api/v1/dashboard/summary")).json()["data"]
    assert counts == {"stores": 2, "warehouses": 3, "suppliers": 1, "products": 1, "skus": 12}
