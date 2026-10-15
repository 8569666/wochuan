from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from app.common.archives import list_records, record_data
from app.common.responses import payload
from app.modules.access.models import Role, UserRoleGrant
from app.modules.access.service import (
    PERMISSION_CATALOG,
    SCOPE_TYPES,
    AccessDep,
    require_permission,
)
from app.modules.auth.models import User
from app.modules.auth.security import hash_password
from app.modules.auth.service import SessionDep
from app.modules.people import schemas as s
from app.modules.people.models import Employee, OrgUnit, Position
from app.modules.people.service import (
    ACTIVE,
    account_data,
    admin,
    create_account,
    create_employee,
    employee_data,
    get,
    org_data,
    personnel_event,
    replace_grants,
    revoke_sessions,
    save,
    validate_org,
    validate_role,
)

router = APIRouter(prefix="/people", tags=["people"])
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


def check_employee(access, employee_id, permission="employee.read"):
    require_permission(access, permission)
    if not access.allows_employee(permission, employee_id):
        raise HTTPException(404, "档案不存在")


@router.get("/permissions")
async def permissions(access: AccessDep):
    admin(access)
    names = {
        "ALL": "全部数据",
        "ORG_TREE": "指定组织及下级",
        "STORES": "指定门店",
        "WAREHOUSES": "指定仓库",
        "HOME": "当前任职组织及下级",
        "SELF": "本人",
    }
    return payload(
        {
            "permissions": [
                {"code": code, "name": name, "group": code.split(".")[0]}
                for code, name in PERMISSION_CATALOG.items()
            ],
            "scope_types": [{"code": code, "name": names[code]} for code in SCOPE_TYPES],
        }
    )


@router.get("/org-units/tree")
async def org_tree(session: SessionDep, access: AccessDep):
    require_permission(access, "org.read")
    ids = access.org_unit_ids("org.read")
    stmt = select(OrgUnit).order_by(OrgUnit.id)
    if ids is not None:
        stmt = stmt.where(OrgUnit.id.in_(ids))
    rows = (await session.scalars(stmt)).all()
    items = {row.id: {**await org_data(session, row), "children": []} for row in rows}
    roots = []
    for item in items.values():
        if item["parent_id"] in items:
            items[item["parent_id"]]["children"].append(item)
        else:
            roots.append(item)
    return payload(roots)


@router.get("/org-units")
async def org_list(
    session: SessionDep,
    access: AccessDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    require_permission(access, "org.read")
    ids = access.org_unit_ids("org.read")
    result = await list_records(
        session,
        OrgUnit,
        keyword,
        status,
        page,
        page_size,
        OrgUnit.id.in_(ids) if ids is not None else None,
    )
    for item in result["items"]:
        item.update(await org_data(session, await get(session, OrgUnit, item["id"])))
    return payload(result)


@router.post("/org-units", status_code=201)
async def org_create(body: s.OrgCreate, session: SessionDep, access: AccessDep):
    require_permission(access, "org.manage")
    if not access.is_admin and (
        not body.parent_id or not access.allows_org("org.manage", body.parent_id)
    ):
        raise HTTPException(403, "没有上级组织的管理权限")
    values = body.model_dump()
    await validate_org(session, values, None, access)
    record = OrgUnit(**values)
    session.add(record)
    await save(session, record, access, values, "CREATE")
    return payload(await org_data(session, record), code=201)


@router.patch("/org-units/{identifier}")
async def org_update(identifier: int, body: s.OrgUpdate, session: SessionDep, access: AccessDep):
    require_permission(access, "org.manage")
    if not access.allows_org("org.manage", identifier):
        raise HTTPException(404, "档案不存在")
    record = await get(session, OrgUnit, identifier, lock=True)
    values = body.model_dump(exclude_unset=True)
    reject_nulls(values, {"code", "name", "status", "kind"})
    await validate_org(session, values, record, access)
    if values.get("parent_id") and not access.allows_org("org.manage", values["parent_id"]):
        raise HTTPException(403, "没有目标上级组织的管理权限")
    for key, value in values.items():
        setattr(record, key, value)
    await save(session, record, access, values)
    return payload(await org_data(session, record))


def reject_nulls(values, required):
    if any(value is None for key, value in values.items() if key in required):
        raise HTTPException(422, "必填字段不能为空")


@router.get("/positions")
async def positions(
    session: SessionDep,
    access: AccessDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    require_permission(access, "position.read")
    return payload(await list_records(session, Position, keyword, status, page, page_size))


@router.post("/positions", status_code=201)
async def position_create(body: s.ArchiveCreate, session: SessionDep, access: AccessDep):
    require_permission(access, "position.manage", global_scope=True)
    record = Position(**body.model_dump())
    session.add(record)
    await save(session, record, access, body.model_dump(), "CREATE")
    return payload(record_data(record), code=201)


@router.patch("/positions/{identifier}")
async def position_update(
    identifier: int, body: s.OrgUpdate, session: SessionDep, access: AccessDep
):
    require_permission(access, "position.manage", global_scope=True)
    record = await get(session, Position, identifier, lock=True)
    values = body.model_dump(exclude_unset=True)
    if set(values) - {"code", "name", "status"}:
        raise HTTPException(422, "岗位只接受编码、名称和状态")
    reject_nulls(values, {"code", "name", "status"})
    if values.get("status") == "INACTIVE" and await session.scalar(
        select(Employee.id)
        .where(Employee.position_id == identifier, Employee.status != "LEFT")
        .limit(1)
    ):
        raise HTTPException(409, "岗位仍有未离职员工")
    for key, value in values.items():
        setattr(record, key, value)
    await save(session, record, access, values)
    return payload(record_data(record))


@router.get("/employees/me")
async def my_profile(session: SessionDep, access: AccessDep):
    if not access.employee_id:
        return payload(None)
    return payload(
        await employee_data(
            session, await get(session, Employee, access.employee_id), access, detail=True
        )
    )


@router.get("/employees")
async def employees(
    session: SessionDep,
    access: AccessDep,
    keyword: str = "",
    status: Literal["PENDING", "PROBATION", "ACTIVE", "LEFT"] | None = None,
    org_unit_id: int | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    require_permission(access, "employee.read")
    filters = []
    if keyword:
        filters.append(
            or_(
                Employee.code.contains(keyword, autoescape=True),
                Employee.name.contains(keyword, autoescape=True),
            )
        )
    if status:
        filters.append(Employee.status == status)
    if org_unit_id:
        filters.append(Employee.org_unit_id == org_unit_id)
    ids = access.employee_ids("employee.read")
    if ids is not None:
        filters.append(Employee.id.in_(ids))
    total = await session.scalar(select(func.count()).select_from(Employee).where(*filters))
    rows = (
        await session.scalars(
            select(Employee)
            .where(*filters)
            .order_by(Employee.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return payload(
        {
            "items": [await employee_data(session, row, access) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/employees", status_code=201)
async def employee_create(body: s.EmployeeCreate, session: SessionDep, access: AccessDep):
    return payload(await create_employee(session, body, access), code=201)


@router.get("/employees/{identifier}")
async def employee_detail(identifier: int, session: SessionDep, access: AccessDep):
    if identifier != access.employee_id:
        check_employee(access, identifier)
    return payload(
        await employee_data(session, await get(session, Employee, identifier), access, detail=True)
    )


@router.patch("/employees/{identifier}")
async def employee_update(
    identifier: int, body: s.EmployeeUpdate, session: SessionDep, access: AccessDep
):
    check_employee(access, identifier, "employee.manage")
    employee = await get(session, Employee, identifier, lock=True)
    values = body.model_dump(exclude_unset=True)
    reject_nulls(values, {"name", "personnel_type"})
    for key, value in values.items():
        setattr(employee, key, value)
    if "name" in values:
        account = await session.scalar(
            select(User).where(User.employee_id == identifier).with_for_update()
        )
        if account:
            account.display_name = employee.name
    await save(session, employee, access, values)
    return payload(await employee_data(session, employee, access))


@router.post("/employees/{identifier}/events", status_code=201)
async def event_create(
    identifier: int, body: s.EventCreate, session: SessionDep, access: AccessDep
):
    return payload(await personnel_event(session, identifier, body, access), code=201)


@router.post("/employees/{identifier}/account", status_code=201)
async def account_create(
    identifier: int, body: s.AccountCreate, session: SessionDep, access: AccessDep
):
    return payload(await create_account(session, identifier, body, access), code=201)


async def staff_account(session, identifier):
    # Resolve employee before user so login, transfer and account changes use one lock order.
    account = await get(session, User, identifier)
    if account.role != "STAFF" or not account.employee_id:
        raise HTTPException(403, "内置管理员账号不能通过人员模块修改")
    employee = await get(session, Employee, account.employee_id, lock=True)
    account = await get(session, User, identifier, lock=True)
    return account, employee


@router.patch("/accounts/{identifier}")
async def account_update(
    identifier: int, body: s.AccountUpdate, session: SessionDep, access: AccessDep
):
    admin(access)
    account, employee = await staff_account(session, identifier)
    if body.enabled and employee.status not in ACTIVE:
        raise HTTPException(422, "仅在职员工可启用账号")
    changes = {}
    if body.enabled is not None:
        account.status = "ACTIVE" if body.enabled else "INACTIVE"
        changes["enabled"] = body.enabled
    if body.password is not None:
        account.password_hash = hash_password(body.password.get_secret_value())
        changes["password_reset"] = True
    await revoke_sessions(session, account.id)
    await save(session, account, access, changes, "UPDATE_ACCOUNT")
    return payload(await account_data(session, account))


@router.put("/accounts/{identifier}/grants")
async def account_grants(
    identifier: int, body: s.GrantsUpdate, session: SessionDep, access: AccessDep
):
    admin(access)
    account, employee = await staff_account(session, identifier)
    if employee.status not in ACTIVE:
        raise HTTPException(422, "仅在职员工可配置授权")
    await replace_grants(session, account, body.grants)
    await save(session, account, access, body.model_dump(), "UPDATE_GRANTS")
    return payload(await account_data(session, account))


@router.get("/roles")
async def roles(
    session: SessionDep,
    access: AccessDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    admin(access)
    return payload(await list_records(session, Role, keyword, status, page, page_size))


@router.post("/roles", status_code=201)
async def role_create(body: s.RoleCreate, session: SessionDep, access: AccessDep):
    admin(access)
    values = body.model_dump()
    validate_role(values)
    record = Role(**values)
    session.add(record)
    await save(session, record, access, values, "CREATE")
    return payload(record_data(record), code=201)


@router.patch("/roles/{identifier}")
async def role_update(identifier: int, body: s.RoleUpdate, session: SessionDep, access: AccessDep):
    admin(access)
    record = await get(session, Role, identifier, lock=True)
    values = body.model_dump(exclude_unset=True)
    reject_nulls(values, {"code", "name", "status", "permissions"})
    validate_role(values)
    for key, value in values.items():
        setattr(record, key, value)
    ids = (
        await session.scalars(
            select(UserRoleGrant.user_id).where(UserRoleGrant.role_id == identifier)
        )
    ).all()
    for user_id in ids:
        await revoke_sessions(session, user_id)
    await save(session, record, access, values)
    return payload(record_data(record))
