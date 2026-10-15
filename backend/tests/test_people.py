from datetime import UTC, datetime, timedelta

import httpx

TODAY = (datetime.now(UTC) + timedelta(hours=8)).date().isoformat()
PASSWORD = "Staff!Example#123"


async def create(client, path, body):
    result = await client.post("/api/v1/people/" + path, json=body)
    assert result.status_code == 201, result.text
    return result.json()["data"]


async def setup_people(client):
    company = await create(
        client, "org-units", {"code": "COMPANY", "name": "我川公司", "kind": "COMPANY"}
    )
    first = await create(
        client,
        "org-units",
        {"code": "FIRST", "name": "第一部门", "kind": "DEPARTMENT", "parent_id": company["id"]},
    )
    second = await create(
        client,
        "org-units",
        {"code": "SECOND", "name": "第二部门", "kind": "DEPARTMENT", "parent_id": company["id"]},
    )
    position = await create(client, "positions", {"code": "STAFF", "name": "业务专员"})
    employee = await create(
        client,
        "employees",
        {
            "code": "E001",
            "name": "员工甲",
            "phone": "13800000001",
            "personnel_type": "EMPLOYEE",
            "status": "PROBATION",
            "org_unit_id": first["id"],
            "position_id": position["id"],
            "hire_date": "2026-01-01",
        },
    )
    return company, first, second, position, employee


async def test_organization_tree_and_employee_invariants(authenticated_client):
    client = authenticated_client
    company, first, second, position, employee = await setup_people(client)
    assert employee["company_id"] == company["id"]
    assert (
        await client.patch(
            f"/api/v1/people/org-units/{company['id']}", json={"parent_id": first["id"]}
        )
    ).status_code == 422
    assert (
        await client.patch(f"/api/v1/people/org-units/{first['id']}", json={"status": "INACTIVE"})
    ).status_code == 409
    assert (
        await client.patch(
            f"/api/v1/people/positions/{position['id']}", json={"status": "INACTIVE"}
        )
    ).status_code == 409
    duplicate = await client.post(
        "/api/v1/people/employees",
        json={
            "code": "E001",
            "name": "重复员工",
            "org_unit_id": first["id"],
            "position_id": position["id"],
            "hire_date": "2026-01-01",
        },
    )
    assert duplicate.status_code == 409
    assert (
        await client.patch(f"/api/v1/people/employees/{employee['id']}", json={"status": "LEFT"})
    ).status_code == 422
    tree = (await client.get("/api/v1/people/org-units/tree")).json()["data"]
    assert tree[0]["id"] == company["id"] and len(tree[0]["children"]) == 2


async def test_confirmation_transfer_leave_and_session_revocation(authenticated_client):
    client = authenticated_client
    company, first, second, position, employee = await setup_people(client)
    role = await create(
        client, "roles", {"code": "SELFROLE", "name": "本人档案", "permissions": ["employee.self"]}
    )
    account = await create(
        client,
        f"employees/{employee['id']}/account",
        {"username": "staff-one", "password": PASSWORD, "enabled": True},
    )
    assert "password_hash" not in account and "password" not in account
    grants = {"grants": [{"role_id": role["id"], "scope_type": "SELF", "scope_ids": []}]}
    assert (
        await client.put(f"/api/v1/people/accounts/{account['id']}/grants", json=grants)
    ).status_code == 200
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://test", headers={"Origin": "http://test"}
    ) as staff:
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "staff-one", "password": PASSWORD}
            )
        ).status_code == 200
        assert (await staff.get("/api/v1/people/employees/me")).json()["data"]["id"] == employee[
            "id"
        ]
        confirm = await client.post(
            f"/api/v1/people/employees/{employee['id']}/events",
            json={"kind": "CONFIRM", "effective_date": TODAY, "reason": "试用通过"},
        )
        assert confirm.status_code == 201
        assert confirm.json()["data"]["status"] == "ACTIVE"
        transfer = await client.post(
            f"/api/v1/people/employees/{employee['id']}/events",
            json={
                "kind": "TRANSFER",
                "effective_date": TODAY,
                "org_unit_id": second["id"],
                "position_id": position["id"],
                "reason": "部门调整",
            },
        )
        assert transfer.status_code == 201
        assert (await staff.get("/api/v1/auth/me")).status_code == 401
        detail = (await client.get(f"/api/v1/people/employees/{employee['id']}")).json()["data"]
        assert len(detail["assignments"]) == 2 and detail["org_unit_id"] == second["id"]
        assert detail["assignments"][0]["org_unit_id"] == first["id"]
        assert detail["account"]["grants"] == []
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "staff-one", "password": PASSWORD}
            )
        ).status_code == 200
        leave = await client.post(
            f"/api/v1/people/employees/{employee['id']}/events",
            json={
                "kind": "LEAVE",
                "effective_date": TODAY,
                "reason": "个人安排",
                "handover_notes": "已交接待办",
            },
        )
        assert leave.status_code == 201 and leave.json()["data"]["status"] == "LEFT"
        assert (await staff.get("/api/v1/auth/me")).status_code == 401
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "staff-one", "password": PASSWORD}
            )
        ).status_code == 401
        assert (
            await client.patch(f"/api/v1/people/accounts/{account['id']}", json={"enabled": True})
        ).status_code == 422
    detail = (await client.get(f"/api/v1/people/employees/{employee['id']}")).json()["data"]
    assert [event["kind"] for event in detail["events"]] == ["CONFIRM", "TRANSFER", "LEAVE"]
    assert detail["account"]["status"] == "INACTIVE"


async def test_manager_cycles_and_future_events_rejected(authenticated_client):
    client = authenticated_client
    company, first, second, position, employee = await setup_people(client)
    subordinate = await create(
        client,
        "employees",
        {
            "code": "E002",
            "name": "员工乙",
            "org_unit_id": first["id"],
            "position_id": position["id"],
            "manager_id": employee["id"],
            "hire_date": "2026-01-01",
        },
    )
    body = {
        "kind": "TRANSFER",
        "effective_date": TODAY,
        "org_unit_id": first["id"],
        "position_id": position["id"],
        "manager_id": subordinate["id"],
        "reason": "不能成环",
    }
    assert (
        await client.post(f"/api/v1/people/employees/{employee['id']}/events", json=body)
    ).status_code == 422
    tomorrow = (datetime.now(UTC) + timedelta(hours=8, days=1)).date().isoformat()
    assert (
        await client.post(
            f"/api/v1/people/employees/{employee['id']}/events",
            json={**body, "manager_id": None, "effective_date": tomorrow},
        )
    ).status_code == 422


async def test_role_account_grants_validated_and_normal_staff_cannot_escalate(authenticated_client):
    client = authenticated_client
    _, first, _, _, employee = await setup_people(client)
    assert (
        await client.post(
            "/api/v1/people/roles",
            json={"code": "BAD", "name": "非法权限", "permissions": ["unknown.permission"]},
        )
    ).status_code == 422
    role = await create(
        client,
        "roles",
        {
            "code": "PRIVILEGED",
            "name": "授权配置",
            "permissions": ["role.manage", "account.manage"],
        },
    )
    account = await create(
        client,
        f"employees/{employee['id']}/account",
        {"username": "ordinary", "password": PASSWORD},
    )
    assert (
        await client.put(
            f"/api/v1/people/accounts/{account['id']}/grants",
            json={
                "grants": [{"role_id": role["id"], "scope_type": "STORES", "scope_ids": [999999]}]
            },
        )
    ).status_code == 422
    assert (
        await client.put(
            f"/api/v1/people/accounts/{account['id']}/grants",
            json={
                "grants": [{"role_id": role["id"], "scope_type": "ALL", "scope_ids": [first["id"]]}]
            },
        )
    ).status_code == 422
    assert (
        await client.put(
            f"/api/v1/people/accounts/{account['id']}/grants",
            json={"grants": [{"role_id": role["id"], "scope_type": "ALL", "scope_ids": []}]},
        )
    ).status_code == 200
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://test", headers={"Origin": "http://test"}
    ) as staff:
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "ordinary", "password": PASSWORD}
            )
        ).status_code == 200
        assert (
            await staff.post(
                "/api/v1/people/roles",
                json={"code": "HACK", "name": "越权", "permissions": ["catalog.cost"]},
            )
        ).status_code == 403
        assert (
            await staff.put(f"/api/v1/people/accounts/{account['id']}/grants", json={"grants": []})
        ).status_code == 403
    assert (
        await client.patch("/api/v1/people/accounts/1", json={"enabled": False})
    ).status_code in [403, 404, 409]


async def test_pending_employee_and_disabled_role_cannot_keep_access(authenticated_client):
    client = authenticated_client
    _, first, _, position, employee = await setup_people(client)
    pending = await create(
        client,
        "employees",
        {
            "code": "WAIT",
            "name": "待入职",
            "status": "PENDING",
            "org_unit_id": first["id"],
            "position_id": position["id"],
            "hire_date": TODAY,
        },
    )
    assert (
        await client.post(
            f"/api/v1/people/employees/{pending['id']}/account",
            json={"username": "pending", "password": PASSWORD},
        )
    ).status_code == 422
    account = await create(
        client, f"employees/{employee['id']}/account", {"username": "active", "password": PASSWORD}
    )
    role = await create(
        client, "roles", {"code": "ORGREAD", "name": "组织查看", "permissions": ["org.read"]}
    )
    assert (
        await client.put(
            f"/api/v1/people/accounts/{account['id']}/grants",
            json={"grants": [{"role_id": role["id"], "scope_type": "ALL", "scope_ids": []}]},
        )
    ).status_code == 200
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://test", headers={"Origin": "http://test"}
    ) as staff:
        await staff.post("/api/v1/auth/login", json={"username": "active", "password": PASSWORD})
        assert (await staff.get("/api/v1/people/org-units/tree")).status_code == 200
        assert (
            await client.patch(f"/api/v1/people/roles/{role['id']}", json={"status": "INACTIVE"})
        ).status_code == 200
        assert (await staff.get("/api/v1/people/org-units/tree")).status_code in [401, 403]


async def test_onboarding_reset_password_and_audit_do_not_expose_credentials(
    authenticated_client, db_session
):
    from sqlalchemy import select

    from app.modules.audit.models import AuditLog

    client = authenticated_client
    _, first, _, position, _ = await setup_people(client)
    pending = await create(
        client,
        "employees",
        {
            "code": "PENDING2",
            "name": "待入职二",
            "status": "PENDING",
            "org_unit_id": first["id"],
            "position_id": position["id"],
            "hire_date": TODAY,
        },
    )
    event = await client.post(
        f"/api/v1/people/employees/{pending['id']}/events",
        json={"kind": "ONBOARD", "effective_date": TODAY, "reason": "到岗"},
    )
    assert event.status_code == 201 and event.json()["data"]["status"] == "PROBATION"
    account = await create(
        client,
        f"employees/{pending['id']}/account",
        {"username": "reset-check", "password": PASSWORD},
    )
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://test", headers={"Origin": "http://test"}
    ) as staff:
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "reset-check", "password": PASSWORD}
            )
        ).status_code == 200
        updated = await client.patch(
            f"/api/v1/people/accounts/{account['id']}", json={"password": "NewSynthetic!2026#"}
        )
        assert updated.status_code == 200
        assert (await staff.get("/api/v1/auth/me")).status_code == 401
        assert (
            await staff.post(
                "/api/v1/auth/login", json={"username": "reset-check", "password": PASSWORD}
            )
        ).status_code == 401
        assert (
            await staff.post(
                "/api/v1/auth/login",
                json={"username": "reset-check", "password": "NewSynthetic!2026#"},
            )
        ).status_code == 200
    logs = (await db_session.scalars(select(AuditLog.changes))).all()
    assert (
        PASSWORD not in str(logs)
        and "NewSynthetic!2026#" not in str(logs)
        and "password_hash" not in str(logs)
    )


async def test_hr_scope_cannot_read_or_transfer_outside_organization(authenticated_client):
    client = authenticated_client
    _, first, second, position, employee = await setup_people(client)
    outsider = await create(
        client,
        "employees",
        {
            "code": "OUTSIDE",
            "name": "外部门员工",
            "org_unit_id": second["id"],
            "position_id": position["id"],
            "hire_date": "2026-01-01",
        },
    )
    account = await create(
        client,
        f"employees/{employee['id']}/account",
        {"username": "scoped-hr", "password": PASSWORD},
    )
    role = await create(
        client,
        "roles",
        {
            "code": "SCOPED_HR",
            "name": "部门人事",
            "permissions": ["employee.read", "employee.transfer", "org.read"],
        },
    )
    assert (
        await client.put(
            f"/api/v1/people/accounts/{account['id']}/grants",
            json={
                "grants": [
                    {"role_id": role["id"], "scope_type": "ORG_TREE", "scope_ids": [first["id"]]}
                ]
            },
        )
    ).status_code == 200
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://test", headers={"Origin": "http://test"}
    ) as staff:
        await staff.post("/api/v1/auth/login", json={"username": "scoped-hr", "password": PASSWORD})
        listing = (await staff.get("/api/v1/people/employees")).json()["data"]
        assert listing["total"] == 1 and listing["items"][0]["id"] == employee["id"]
        assert (await staff.get(f"/api/v1/people/employees/{outsider['id']}")).status_code == 404
        assert (
            await staff.post(
                f"/api/v1/people/employees/{employee['id']}/events",
                json={"kind": "TRANSFER", "effective_date": TODAY, "org_unit_id": second["id"]},
            )
        ).status_code == 403
