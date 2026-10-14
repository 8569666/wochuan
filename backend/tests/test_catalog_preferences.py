async def dictionaries(client):
    category = await client.post("/api/v1/categories", json={"code": "TESTDRESS", "name": "连衣裙"})
    fabric = await client.post(
        "/api/v1/fabrics", json={"code": "COTTON", "name": "纯棉", "composition": "100%棉"}
    )
    assert category.status_code == fabric.status_code == 201
    return category.json()["data"], fabric.json()["data"]


async def test_category_fabric_memory_only_changes_on_success(authenticated_client, matrix):
    client = authenticated_client
    category, fabric = await dictionaries(client)
    body = {**matrix, "category_id": category["id"], "fabric_id": fabric["id"]}
    result = await client.post("/api/v1/products", json=body)
    assert result.status_code == 201
    assert result.json()["data"]["fabric_composition"] == "100%棉"
    detail = (await client.get(f"/api/v1/categories/{category['id']}")).json()["data"]
    assert detail["last_fabric_id"] == fabric["id"]
    other = (
        await client.post(
            "/api/v1/fabrics", json={"code": "WOOL", "name": "羊毛", "composition": "100%羊毛"}
        )
    ).json()["data"]
    failed = await client.post("/api/v1/products", json={**body, "fabric_id": other["id"]})
    assert failed.status_code == 409
    assert (await client.get(f"/api/v1/categories/{category['id']}")).json()["data"][
        "last_fabric_id"
    ] == fabric["id"]


async def test_product_requires_valid_dictionary_and_ignores_disabled_default(
    authenticated_client, matrix
):
    client = authenticated_client
    missing = {**matrix}
    missing.pop("category_id", None)
    assert (await client.post("/api/v1/products", json=missing)).status_code == 422
    assert (
        await client.post("/api/v1/products", json={**matrix, "category_id": 999999999})
    ).status_code == 422
    category, fabric = await dictionaries(client)
    body = {**matrix, "category_id": category["id"], "fabric_id": fabric["id"]}
    result = await client.post("/api/v1/products", json=body)
    assert result.status_code == 201
    await client.patch(f"/api/v1/fabrics/{fabric['id']}", json={"status": "INACTIVE"})
    assert (
        await client.post("/api/v1/products", json={**body, "code": "NEWCODE"})
    ).status_code == 422
    # Existing archived references remain editable; historical fabric text is retained.
    assert (
        await client.patch(
            f"/api/v1/products/{result.json()['data']['id']}", json={"name": "更新款名"}
        )
    ).status_code == 200


async def test_cannot_unlink_category_or_write_unlisted_fabric(authenticated_client, matrix):
    client = authenticated_client
    assert (
        await client.post("/api/v1/products", json={**matrix, "fabric_composition": "任意输入"})
    ).status_code == 422
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    assert (
        await client.patch(f"/api/v1/products/{product['id']}", json={"category_id": None})
    ).status_code == 422


async def test_favorites_shared_order_max_ten_and_active_only(authenticated_client, matrix):
    client = authenticated_client
    ids = matrix["color_ids"][::-1]
    result = await client.put("/api/v1/catalog-preferences/colors", json={"ids": ids})
    assert result.status_code == 200
    assert (await client.get("/api/v1/catalog-preferences/colors")).json()["data"]["ids"] == ids
    assert (
        await client.put("/api/v1/catalog-preferences/colors", json={"ids": ids * 4})
    ).status_code == 422
    await client.patch(f"/api/v1/colors/{ids[0]}", json={"status": "INACTIVE"})
    assert (
        await client.put("/api/v1/catalog-preferences/colors", json={"ids": ids})
    ).status_code == 422
    assert (await client.get("/api/v1/catalog-preferences/colors")).json()["data"]["ids"] == ids[1:]
    group = matrix["size_group_id"]
    assert (
        await client.put("/api/v1/catalog-preferences/size-groups", json={"ids": [group]})
    ).status_code == 200


async def test_append_color_keeps_existing_skus_and_is_atomic(authenticated_client, matrix):
    client = authenticated_client
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    color = (await client.post("/api/v1/colors", json={"code": "BLUE", "name": "蓝色"})).json()[
        "data"
    ]
    sizes = list(dict.fromkeys(s["size_id"] for s in product["skus"]))
    additions = [
        {"color_id": color["id"], "size_id": size, "retail_price": "299.00"} for size in sizes
    ]
    body = {"new_skus": additions}
    # Missing a size must reject the entire append.
    assert (
        await client.patch(f"/api/v1/products/{product['id']}", json={"new_skus": additions[:-1]})
    ).status_code == 422
    # A barcode collision must roll back both new cells and edits to existing prices.
    bad = [dict(cell) for cell in additions]
    bad[-1]["barcode"] = product["skus"][0]["barcode"]
    failed = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={
            "new_skus": bad,
            "sku_prices": [{"id": product["skus"][0]["id"], "retail_price": "1.00"}],
        },
    )
    assert failed.status_code == 409
    unchanged = (await client.get(f"/api/v1/products/{product['id']}")).json()["data"]
    assert unchanged["skus"] == product["skus"]
    result = await client.patch(f"/api/v1/products/{product['id']}", json=body)
    assert result.status_code == 200
    actual = result.json()["data"]["skus"]
    assert len(actual) == 16
    assert [s for s in actual if s["color_id"] != color["id"]] == product["skus"]
    assert (await client.patch(f"/api/v1/products/{product['id']}", json=body)).status_code == 409


async def test_parallel_appends_do_not_duplicate_dimensions(authenticated_client, matrix):
    import asyncio

    client = authenticated_client
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    color = (await client.post("/api/v1/colors", json={"code": "EXTRA", "name": "新增色"})).json()[
        "data"
    ]
    sizes = list(dict.fromkeys(s["size_id"] for s in product["skus"]))
    body = {
        "new_skus": [
            {"color_id": color["id"], "size_id": size, "retail_price": "299.00"} for size in sizes
        ]
    }
    results = await asyncio.gather(
        *[client.patch(f"/api/v1/products/{product['id']}", json=body) for _ in range(2)]
    )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert len((await client.get(f"/api/v1/products/{product['id']}")).json()["data"]["skus"]) == 16
