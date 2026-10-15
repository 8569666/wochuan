from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.access.service import AccessContext, require_permission


def context(grants):
    return AccessContext(
        SimpleNamespace(id=7, role="STAFF", employee_id=9),
        SimpleNamespace(id=9, org_unit_id=2, company_id=1),
        grants,
        [
            SimpleNamespace(id=1, parent_id=None, store_id=None, warehouse_id=None),
            SimpleNamespace(id=2, parent_id=1, store_id=10, warehouse_id=None),
            SimpleNamespace(id=3, parent_id=2, store_id=None, warehouse_id=20),
        ],
        [SimpleNamespace(id=20, store_id=10), SimpleNamespace(id=21, store_id=11)],
        [SimpleNamespace(id=9, org_unit_id=2), SimpleNamespace(id=8, org_unit_id=3)],
    )


def grant(permissions, scope_type, scope_ids=()):
    return (
        SimpleNamespace(permissions=permissions),
        SimpleNamespace(scope_type=scope_type, scope_ids=list(scope_ids)),
    )


def test_scope_union_never_borrows_an_unrelated_roles_warehouses():
    access = context(
        [grant(["inventory.read"], "WAREHOUSES", [20]), grant(["catalog.cost"], "WAREHOUSES", [21])]
    )
    assert access.warehouse_ids("inventory.read") == {20}
    assert access.warehouse_ids("catalog.cost") == {21}
    assert not access.allows_warehouse("catalog.cost", 20)
    assert not access.has("catalog.cost", global_scope=True)


def test_home_scope_tracks_org_descendants_and_their_warehouse():
    access = context([grant(["employee.read", "inventory.read"], "HOME")])
    assert access.org_unit_ids("employee.read") == {2, 3}
    assert access.employee_ids("employee.read") == {8, 9}
    assert access.warehouse_ids("inventory.read") == {20}
    assert access.employee_ids("employee.self") == {9}


def test_scoped_catalog_writer_cannot_edit_global_shared_dictionary():
    access = context([grant(["catalog.write"], "STORES", [10])])
    with pytest.raises(HTTPException) as error:
        require_permission(access, "catalog.write", global_scope=True)
    assert error.value.status_code == 403


def test_admin_has_global_and_all_data_access_without_grants():
    access = AccessContext(SimpleNamespace(id=1, role="ADMIN", employee_id=None))
    assert access.has("catalog.write", global_scope=True)
    assert access.warehouse_ids("inventory.read") is None


def test_cost_redaction_uses_the_cost_grant_for_each_warehouse():
    from app.modules.access.service import redact_cost

    access = context(
        [grant(["inventory.read"], "ALL"), grant(["catalog.cost"], "WAREHOUSES", [20])]
    )
    values = {
        "quantity": 3,
        "unit_cost": "5",
        "total_amount": "15",
        "purchase_base_price": "5",
        "average_cost": "5",
        "amount": "15",
    }
    assert redact_cost(values, access, 21) == {"quantity": 3}
    assert redact_cost(values, access, 20)["unit_cost"] == "5"
    assert "purchase_base_price" not in redact_cost(values, access)


@pytest.mark.asyncio
async def test_staff_store_scope_filters_list_total_and_detail(client, db_session):
    from datetime import date

    from app.modules.access.models import Role, UserRoleGrant
    from app.modules.auth.models import User
    from app.modules.auth.security import hash_password
    from app.modules.organization.models import Store
    from app.modules.people.models import Employee, OrgUnit, Position

    company = OrgUnit(code="CO", name="公司", kind="COMPANY", status="ACTIVE")
    first, other = Store(code="S1", name="本店"), Store(code="S2", name="其他店")
    position = Position(code="P1", name="店员")
    db_session.add_all([company, first, other, position])
    await db_session.flush()
    employee = Employee(
        code="E1",
        name="员工",
        personnel_type="EMPLOYEE",
        status="ACTIVE",
        company_id=company.id,
        org_unit_id=company.id,
        position_id=position.id,
        hire_date=date(2026, 10, 1),
    )
    db_session.add(employee)
    await db_session.flush()
    user = User(
        username="staff",
        password_hash=hash_password("Test!Password#123"),
        role="STAFF",
        employee_id=employee.id,
    )
    role = Role(code="STORE", name="本店读", permissions=["store.read"])
    db_session.add_all([user, role])
    await db_session.flush()
    db_session.add(
        UserRoleGrant(user_id=user.id, role_id=role.id, scope_type="STORES", scope_ids=[first.id])
    )
    await db_session.commit()
    response = await client.post(
        "/api/v1/auth/login", json={"username": "staff", "password": "Test!Password#123"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_admin"] is False
    response = await client.get("/api/v1/stores")
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["id"] == first.id
    assert (await client.get(f"/api/v1/stores/{other.id}")).status_code == 404
    employee.status = "LEFT"
    await db_session.commit()
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def staff_login(client, session, specifications):
    from datetime import date

    from app.modules.access.models import Role, UserRoleGrant
    from app.modules.auth.models import User
    from app.modules.auth.security import hash_password
    from app.modules.people.models import Employee, OrgUnit, Position

    company = OrgUnit(code="TEST-CO", name="公司", kind="COMPANY")
    position = Position(code="TEST-P", name="店员")
    session.add_all([company, position])
    await session.flush()
    employee = Employee(
        code="TEST-E",
        name="员工",
        personnel_type="EMPLOYEE",
        status="ACTIVE",
        company_id=company.id,
        org_unit_id=company.id,
        position_id=position.id,
        hire_date=date(2026, 10, 1),
    )
    session.add(employee)
    await session.flush()
    user = User(
        username="scoped",
        password_hash=hash_password("Test!Password#123"),
        role="STAFF",
        employee_id=employee.id,
    )
    session.add(user)
    await session.flush()
    for index, (permissions, scope_type, ids) in enumerate(specifications):
        role = Role(code=f"ROLE-{index}", name="测试角色", permissions=permissions)
        session.add(role)
        await session.flush()
        session.add(
            UserRoleGrant(user_id=user.id, role_id=role.id, scope_type=scope_type, scope_ids=ids)
        )
    await session.commit()
    response = await client.post(
        "/api/v1/auth/login", json={"username": "scoped", "password": "Test!Password#123"}
    )
    assert response.status_code == 200


async def test_inventory_and_purchase_scope_and_cost_are_independent(
    authenticated_client, matrix, db_session
):
    from uuid import uuid4

    from test_product_receiving import receiving_context

    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    product = (
        await client.post("/api/v1/products", json={**matrix, "receiving": receiving})
    ).json()["data"]
    second_warehouse = (
        await client.post("/api/v1/warehouses", json={"code": "OTHER", "name": "其他仓"})
    ).json()["data"]
    other_receiving = {
        **receiving,
        "warehouse_id": second_warehouse["id"],
        "request_id": str(uuid4()),
    }
    assert (
        await client.patch(f"/api/v1/products/{product['id']}", json={"receiving": other_receiving})
    ).status_code == 200
    receipts = (await client.get("/api/v1/purchase-receipts")).json()["data"]["items"]
    foreign_receipt_id = next(
        r["id"] for r in receipts if r["warehouse_id"] == second_warehouse["id"]
    )
    await staff_login(
        client,
        db_session,
        [
            (
                ["inventory.read", "purchase.read", "catalog.read"],
                "WAREHOUSES",
                [receiving["warehouse_id"]],
            ),
            (["catalog.cost"], "WAREHOUSES", [second_warehouse["id"]]),
        ],
    )
    for endpoint in ("inventory", "inventory/movements", "purchase-receipts"):
        response = await client.get(f"/api/v1/{endpoint}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        item = data["items"][0]
        assert item["warehouse_id"] == receiving["warehouse_id"]
        assert (
            not {"average_cost", "total_cost", "unit_cost", "total_amount", "amount"} & item.keys()
        )
        assert (
            await client.get(f"/api/v1/{endpoint}", params={"warehouse_id": second_warehouse["id"]})
        ).json()["data"]["total"] == 0
    assert (await client.get(f"/api/v1/purchase-receipts/{foreign_receipt_id}")).status_code == 404
    own_receipt = next(r for r in receipts if r["warehouse_id"] == receiving["warehouse_id"])
    detail = (await client.get(f"/api/v1/purchase-receipts/{own_receipt['id']}")).json()["data"]
    assert "unit_cost" not in detail and "amount" not in detail["lines"][0]
    detail = (await client.get(f"/api/v1/products/{product['id']}")).json()["data"]
    assert "purchase_base_price" not in detail


async def test_catalog_write_alone_cannot_receive_stock(authenticated_client, matrix, db_session):
    from test_product_receiving import receiving_context

    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    await staff_login(client, db_session, [(["catalog.write"], "ALL", [])])
    response = await client.patch(
        f"/api/v1/products/{product['id']}", json={"receiving": receiving}
    )
    assert response.status_code == 403
    assert (
        await client.patch(f"/api/v1/products/{product['id']}", json={"name": "修改名称"})
    ).status_code == 200


async def test_receiving_only_permission_cannot_modify_product_or_other_warehouse(
    authenticated_client, matrix, db_session
):
    from uuid import uuid4

    from test_product_receiving import receiving_context

    client = authenticated_client
    receiving = await receiving_context(client, matrix)
    product = (await client.post("/api/v1/products", json=matrix)).json()["data"]
    await staff_login(
        client, db_session, [(["purchase.receive"], "WAREHOUSES", [receiving["warehouse_id"]])]
    )
    path = f"/api/v1/products/{product['id']}"
    assert (
        await client.patch(path, json={"name": "越权", "receiving": receiving})
    ).status_code == 403
    assert (
        await client.patch(path, json={"receiving": {**receiving, "warehouse_id": 999999}})
    ).status_code == 403
    response = await client.patch(
        path, json={"receiving": {**receiving, "request_id": str(uuid4())}}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "purchase_base_price" not in data
    assert "unit_cost" not in data["receipt"]
