from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.common.archives import record_data
from app.modules.access.models import Role, UserRoleGrant
from app.modules.access.service import PERMISSION_CATALOG, require_permission
from app.modules.audit.service import record_audit
from app.modules.auth.models import LoginSession, User
from app.modules.auth.security import hash_password
from app.modules.organization.models import Store, Warehouse
from app.modules.people.models import Assignment, Employee, OrgUnit, PersonnelEvent, Position

ACTIVE = {"ACTIVE", "PROBATION"}


def today():
    return (datetime.now(UTC) + timedelta(hours=8)).date()


def admin(access):
    if not access.is_admin:
        raise HTTPException(403, "只有系统管理员可以配置账号和授权")


async def get(session, model, identifier, lock=False):
    stmt = select(model).where(model.id == identifier)
    if lock:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    record = await session.scalar(stmt)
    if not record:
        raise HTTPException(404, "档案不存在")
    return record


async def active(session, model, identifier):
    if not identifier:
        raise HTTPException(422, "关联档案不能为空")
    record = await session.get(model, identifier)
    if not record or record.status != "ACTIVE":
        raise HTTPException(422, "关联档案未启用")
    return record


async def save(session, record, access, changes, action="UPDATE"):
    try:
        await session.flush()
        record_audit(session, access.id, action, record.__tablename__, record.id, changes)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "编码、账号或关联关系重复") from None


async def company_for(session, org_id):
    visited = set()
    while org_id:
        if org_id in visited:
            raise HTTPException(422, "组织不能形成循环")
        visited.add(org_id)
        org = await active(session, OrgUnit, org_id)
        if org.kind == "COMPANY":
            return org.id
        org_id = org.parent_id
    raise HTTPException(422, "组织必须归属公司")


async def validate_org(session, values, existing, access):
    merged = record_data(existing) if existing else {}
    merged.update(values)
    kind, parent = merged["kind"], merged.get("parent_id")
    if (kind == "COMPANY") != (parent is None):
        raise HTTPException(422, "公司必须是根组织，其他组织必须选择上级")
    if existing and kind != existing.kind:
        raise HTTPException(422, "组织类型创建后不可修改")
    seen = {existing.id} if existing else set()
    while parent:
        if parent in seen:
            raise HTTPException(422, "组织不能形成循环")
        seen.add(parent)
        node = await active(session, OrgUnit, parent)
        parent = node.parent_id
    if existing and merged.get("parent_id") != existing.parent_id:
        # Moving occupied branches would silently change company and HOME scopes.
        occupied = await session.scalar(
            select(Employee.id).where(Employee.org_unit_id == existing.id).limit(1)
        )
        children = await session.scalar(
            select(OrgUnit.id).where(OrgUnit.parent_id == existing.id).limit(1)
        )
        if occupied or children:
            raise HTTPException(409, "已有人员或子组织的节点不能直接移动，请使用人员调岗")
        if not access.is_admin:
            raise HTTPException(403, "移动组织需系统管理员操作")
    for key, expected, model in [
        ("store_id", "STORE", Store),
        ("warehouse_id", "WAREHOUSE", Warehouse),
    ]:
        identifier = merged.get(key)
        if kind == expected and not identifier:
            raise HTTPException(422, "请选择对应业务档案")
        if identifier and kind != expected:
            raise HTTPException(422, "组织类型与关联业务档案不符")
        if identifier:
            await active(session, model, identifier)
        if (not existing and identifier) or (existing and identifier != getattr(existing, key)):
            admin(access)
    if merged.get("status") == "INACTIVE":
        if existing:
            child = await session.scalar(
                select(OrgUnit.id)
                .where(OrgUnit.parent_id == existing.id, OrgUnit.status == "ACTIVE")
                .limit(1)
            )
            employee = await session.scalar(
                select(Employee.id)
                .where(Employee.org_unit_id == existing.id, Employee.status != "LEFT")
                .limit(1)
            )
            if child or employee:
                raise HTTPException(409, "组织下仍有有效子组织或未离职员工")


async def validate_manager(session, manager_id, company_id, employee_id=None):
    seen = {employee_id} if employee_id else set()
    current = manager_id
    while current:
        if current in seen:
            raise HTTPException(422, "直属上级不能形成循环")
        seen.add(current)
        manager = await get(session, Employee, current)
        if manager.company_id != company_id or manager.status not in ACTIVE:
            raise HTTPException(422, "直属上级必须是同公司在职员工")
        current = manager.manager_id


async def org_data(session, org):
    result = record_data(org)
    if org.store_id:
        business = await session.get(Store, org.store_id)
        result["name"] = business.name
    elif org.warehouse_id:
        business = await session.get(Warehouse, org.warehouse_id)
        result["name"] = business.name
    return result


async def account_data(session, account):
    result = {
        key: getattr(account, key)
        for key in ["id", "username", "display_name", "employee_id", "status", "role"]
    }
    result["enabled"] = account.status == "ACTIVE"
    rows = (
        await session.execute(
            select(UserRoleGrant, Role)
            .join(Role, Role.id == UserRoleGrant.role_id)
            .where(UserRoleGrant.user_id == account.id)
            .order_by(UserRoleGrant.id)
        )
    ).all()
    result["grants"] = [{**record_data(grant), "role_name": role.name} for grant, role in rows]
    return result


async def employee_data(session, employee, access, detail=False):
    result = record_data(employee)
    for key, model, identifier in [
        ("company_name", OrgUnit, employee.company_id),
        ("org_unit_name", OrgUnit, employee.org_unit_id),
        ("position_name", Position, employee.position_id),
        ("manager_name", Employee, employee.manager_id),
    ]:
        item = await session.get(model, identifier) if identifier else None
        result[key] = (
            (await org_data(session, item))["name"]
            if item and model is OrgUnit
            else item.name
            if item
            else None
        )
    if detail:
        assignments = (
            await session.scalars(
                select(Assignment)
                .where(Assignment.employee_id == employee.id)
                .order_by(Assignment.effective_from, Assignment.id)
            )
        ).all()
        result["assignments"] = []
        for assignment in assignments:
            item = record_data(assignment)
            for key, model, identifier in [
                ("org_unit_name", OrgUnit, assignment.org_unit_id),
                ("position_name", Position, assignment.position_id),
                ("manager_name", Employee, assignment.manager_id),
            ]:
                linked = await session.get(model, identifier) if identifier else None
                item[key] = linked.name if linked else None
            result["assignments"].append(item)
        events = (
            await session.scalars(
                select(PersonnelEvent)
                .where(PersonnelEvent.employee_id == employee.id)
                .order_by(PersonnelEvent.effective_date, PersonnelEvent.id)
            )
        ).all()
        result["events"] = [record_data(event) for event in events]
        if access.is_admin:
            account = await session.scalar(select(User).where(User.employee_id == employee.id))
            result["account"] = await account_data(session, account) if account else None
    return result


async def validate_grants(session, grants):
    seen = set()
    for grant in grants:
        key = (grant.role_id, grant.scope_type)
        if key in seen:
            raise HTTPException(422, "同一角色和范围类型不能重复")
        seen.add(key)
        await active(session, Role, grant.role_id)
        ids = grant.scope_ids
        if len(set(ids)) != len(ids) or any(identifier <= 0 for identifier in ids):
            raise HTTPException(422, "范围编号必须为不重复正整数")
        if grant.scope_type in {"ALL", "HOME", "SELF"}:
            if ids:
                raise HTTPException(422, "此范围不接受指定编号")
        else:
            if not ids:
                raise HTTPException(422, "请选择授权范围")
            model = {"ORG_TREE": OrgUnit, "STORES": Store, "WAREHOUSES": Warehouse}[
                grant.scope_type
            ]
            for identifier in ids:
                await active(session, model, identifier)


async def revoke_sessions(session, user_id):
    await session.execute(delete(LoginSession).where(LoginSession.user_id == user_id))


async def replace_grants(session, account, grants):
    await validate_grants(session, grants)
    await session.execute(delete(UserRoleGrant).where(UserRoleGrant.user_id == account.id))
    for grant in grants:
        session.add(UserRoleGrant(user_id=account.id, **grant.model_dump()))
    await revoke_sessions(session, account.id)


async def create_employee(session, body, access):
    require_permission(access, "employee.manage")
    values = body.model_dump()
    if not access.allows_org("employee.manage", body.org_unit_id):
        raise HTTPException(403, "没有该组织的人员管理权限")
    company_id = await company_for(session, body.org_unit_id)
    if body.company_id and body.company_id != company_id:
        raise HTTPException(422, "公司与组织不匹配")
    values["company_id"] = company_id
    await active(session, Position, body.position_id)
    await validate_manager(session, body.manager_id, company_id)
    if body.status != "PENDING" and body.hire_date > today():
        raise HTTPException(422, "未到入职日期，请使用待入职状态")
    employee = Employee(**values)
    session.add(employee)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "工号已存在") from None
    session.add(
        Assignment(
            employee_id=employee.id,
            org_unit_id=employee.org_unit_id,
            position_id=employee.position_id,
            manager_id=employee.manager_id,
            effective_from=employee.hire_date,
        )
    )
    await save(session, employee, access, jsonable_encoder(values), "CREATE")
    return await employee_data(session, employee, access)


async def personnel_event(session, employee_id, body, access):
    permission = {"TRANSFER": "employee.transfer", "LEAVE": "employee.leave"}.get(
        body.kind, "employee.manage"
    )
    require_permission(access, permission)
    employee = await get(session, Employee, employee_id, lock=True)
    if not access.allows_employee(permission, employee.id):
        raise HTTPException(404, "档案不存在")
    account = await session.scalar(
        select(User)
        .where(User.employee_id == employee.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    effective = body.effective_date
    assignment = await session.scalar(
        select(Assignment)
        .where(Assignment.employee_id == employee.id, Assignment.effective_to.is_(None))
        .with_for_update()
    )
    last_event = await session.scalar(
        select(PersonnelEvent.effective_date)
        .where(PersonnelEvent.employee_id == employee.id)
        .order_by(PersonnelEvent.effective_date.desc())
        .limit(1)
    )
    if (
        effective > today()
        or effective < employee.hire_date
        or (assignment and effective < assignment.effective_from)
        or (last_event and effective < last_event)
    ):
        raise HTTPException(422, "异动日期必须已生效且不早于入职和上次异动")
    if employee.status == "LEFT":
        raise HTTPException(409, "离职员工不能直接异动")
    if body.kind != "TRANSFER" and (
        body.grants is not None
        or any(key in body.model_fields_set for key in ["org_unit_id", "position_id", "manager_id"])
    ):
        raise HTTPException(422, "仅调岗可更改任职及授权")
    before = jsonable_encoder(record_data(employee))
    if body.kind == "ONBOARD":
        if employee.status != "PENDING":
            raise HTTPException(409, "仅待入职员工可办理入职")
        employee.status = "PROBATION"
    elif body.kind == "CONFIRM":
        if employee.status != "PROBATION":
            raise HTTPException(409, "仅试用员工可转正")
        employee.status, employee.confirmation_date = "ACTIVE", effective
    elif body.kind == "TRANSFER":
        if employee.status not in ACTIVE:
            raise HTTPException(409, "仅在职员工可调岗")
        org_id, position_id = (
            body.org_unit_id or employee.org_unit_id,
            body.position_id or employee.position_id,
        )
        manager_id = (
            body.manager_id if "manager_id" in body.model_fields_set else employee.manager_id
        )
        if not access.allows_org(permission, org_id):
            raise HTTPException(403, "没有目标组织的调岗权限")
        if await company_for(session, org_id) != employee.company_id:
            raise HTTPException(422, "本批暂不支持跨公司调岗")
        await active(session, Position, position_id)
        await validate_manager(session, manager_id, employee.company_id, employee.id)
        if body.grants is not None:
            admin(access)
            if not account:
                raise HTTPException(422, "员工尚无账号，无法配置授权")
            await validate_grants(session, body.grants)
        if assignment:
            assignment.effective_to = effective
        employee.org_unit_id, employee.position_id, employee.manager_id = (
            org_id,
            position_id,
            manager_id,
        )
        session.add(
            Assignment(
                employee_id=employee.id,
                org_unit_id=org_id,
                position_id=position_id,
                manager_id=manager_id,
                effective_from=effective,
            )
        )
        if account:
            await replace_grants(session, account, body.grants or [])
    else:
        if body.handover_employee_id:
            handover = await get(session, Employee, body.handover_employee_id)
            if (
                handover.id == employee.id
                or handover.company_id != employee.company_id
                or handover.status not in ACTIVE
            ):
                raise HTTPException(422, "交接人必须为同公司其他在职员工")
        employee.status, employee.left_date = "LEFT", effective
        if assignment:
            assignment.effective_to = effective
        if account:
            account.status = "INACTIVE"
            await revoke_sessions(session, account.id)
    after = jsonable_encoder(record_data(employee))
    event = PersonnelEvent(
        employee_id=employee.id,
        actor_id=access.id,
        kind=body.kind,
        effective_date=effective,
        reason=body.reason,
        handover_employee_id=body.handover_employee_id,
        handover_notes=body.handover_notes,
        before_data=before,
        after_data=after,
    )
    session.add(event)
    await save(
        session,
        event,
        access,
        {"before": before, "after": after, "kind": body.kind, "reason": body.reason},
        body.kind,
    )
    return await employee_data(session, employee, access, detail=True)


def validate_role(values):
    permissions = values.get("permissions")
    if permissions is not None and (
        len(permissions) != len(set(permissions)) or set(permissions) - set(PERMISSION_CATALOG)
    ):
        raise HTTPException(422, "权限代码无效或重复")


async def create_account(session, employee_id, body, access):
    admin(access)
    employee = await get(session, Employee, employee_id, lock=True)
    if body.enabled and employee.status not in ACTIVE:
        raise HTTPException(422, "仅在职员工可启用账号")
    account = User(
        username=body.username,
        display_name=employee.name,
        password_hash=hash_password(body.password.get_secret_value()),
        role="STAFF",
        status="ACTIVE" if body.enabled else "INACTIVE",
        employee_id=employee.id,
    )
    session.add(account)
    await save(
        session,
        account,
        access,
        {"employee_id": employee.id, "username": body.username, "enabled": body.enabled},
        "CREATE_ACCOUNT",
    )
    return await account_data(session, account)
