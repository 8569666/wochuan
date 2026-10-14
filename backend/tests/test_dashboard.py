async def test_dashboard_counts_real_data(authenticated_client):
    client = authenticated_client
    assert (await client.get("/api/v1/dashboard/summary")).json()["data"]["stores"] == 0
    await client.post("/api/v1/stores", json={"code": "S1", "name": "门店"})
    result = (await client.get("/api/v1/dashboard/summary")).json()["data"]
    assert result["stores"] == 1
    assert result["products"] == 0
