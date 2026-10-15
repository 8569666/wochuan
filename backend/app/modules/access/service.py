from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select

from app.modules.access.models import Role, UserRoleGrant
from app.modules.auth.service import CurrentUserDep, SessionDep

PERMISSION_CATALOG = {
    "dashboard.read": "查看仪表盘",
    "org.read": "查看组织",
    "org.manage": "管理组织",
    "position.read": "查看岗位",
    "position.manage": "管理岗位",
    "employee.read": "查看员工",
    "employee.manage": "管理员工",
    "employee.transfer": "员工调岗",
    "employee.leave": "员工离职",
    "employee.self": "查看本人档案",
    "account.manage": "管理账号",
    "role.manage": "管理角色",
    "audit.read": "查看操作日志",
    "store.read": "查看门店",
    "store.write": "管理门店",
    "warehouse.read": "查看仓库",
    "warehouse.write": "管理仓库",
    "supplier.read": "查看供应商",
    "supplier.write": "管理供应商",
    "catalog.read": "查看商品",
    "catalog.write": "管理商品",
    "catalog.cost": "查看采购成本",
    "purchase.read": "查看采购单",
    "purchase.receive": "采购入库",
    "inventory.read": "查看库存",
}
SCOPE_TYPES = ["ALL", "ORG_TREE", "STORES", "WAREHOUSES", "HOME", "SELF"]


class AccessContext:
    def __init__(self, user, employee=None, grants=(), org_units=(), warehouses=(), employees=()):
        self.user = user
        self.id = user.id
        self.is_admin = user.role == "ADMIN"
        self.employee_id = user.employee_id
        self.employee = employee
        self.grants = list(grants)
        self.org_units = list(org_units)
        self.warehouses = list(warehouses)
        self.employees = list(employees)
        self.permissions = set(PERMISSION_CATALOG) if self.is_admin else {"employee.self"}
        self.global_permissions = set(PERMISSION_CATALOG) if self.is_admin else set()
        for role, grant in self.grants:
            # Ordinary roles never grant account or role administration.
            permissions = set(role.permissions) - {"account.manage", "role.manage"}
            self.permissions.update(permissions)
            if grant.scope_type == "ALL":
                self.global_permissions.update(permissions)

    def has(self, permission, global_scope=False):
        return permission in (self.global_permissions if global_scope else self.permissions)

    def _tree(self, roots):
        ids = set(roots)
        while True:
            expanded = ids | {org.id for org in self.org_units if org.parent_id in ids}
            if expanded == ids:
                return ids
            ids = expanded

    def _scope(self, permission, target):
        if self.is_admin or permission in self.global_permissions:
            return None
        if permission == "employee.self":
            return {self.employee_id} if target == "employee" and self.employee_id else set()
        result = set()
        for role, grant in self.grants:
            if permission not in role.permissions or permission not in self.permissions:
                continue
            kind, ids = grant.scope_type, set(grant.scope_ids)
            orgs, stores, warehouses = set(), set(), set()
            if kind in {"HOME", "ORG_TREE"}:
                roots = {self.employee.org_unit_id} if kind == "HOME" and self.employee else ids
                orgs = self._tree(roots)
            elif kind == "STORES":
                stores = ids
                orgs = self._tree({o.id for o in self.org_units if o.store_id in stores})
            elif kind == "WAREHOUSES":
                warehouses = ids
                orgs = self._tree({o.id for o in self.org_units if o.warehouse_id in warehouses})
            elif kind == "SELF":
                if target == "employee" and self.employee_id:
                    result.add(self.employee_id)
                continue
            stores |= {o.store_id for o in self.org_units if o.id in orgs and o.store_id}
            warehouses |= {
                o.warehouse_id for o in self.org_units if o.id in orgs and o.warehouse_id
            }
            warehouses |= {w.id for w in self.warehouses if w.store_id in stores}
            if target == "org":
                result |= orgs
            elif target == "store":
                result |= stores
            elif target == "warehouse":
                result |= warehouses
            else:
                result |= {e.id for e in self.employees if e.org_unit_id in orgs}
        return result

    def org_unit_ids(self, permission):
        return self._scope(permission, "org")

    def store_ids(self, permission):
        return self._scope(permission, "store")

    def warehouse_ids(self, permission):
        return self._scope(permission, "warehouse")

    def employee_ids(self, permission):
        return self._scope(permission, "employee")

    def allows_org(self, permission, identifier):
        ids = self.org_unit_ids(permission)
        return ids is None or identifier in ids

    def allows_store(self, permission, identifier):
        ids = self.store_ids(permission)
        return ids is None or identifier in ids

    def allows_warehouse(self, permission, identifier):
        ids = self.warehouse_ids(permission)
        return ids is None or identifier in ids

    def allows_employee(self, permission, identifier):
        ids = self.employee_ids(permission)
        return ids is None or identifier in ids


def require_permission(access, permission, global_scope=False):
    if not access.has(permission, global_scope):
        raise HTTPException(403, "没有操作权限")


async def build_access(session, user):
    from app.modules.organization.models import Warehouse
    from app.modules.people.models import Employee, OrgUnit

    if user.role == "ADMIN":
        return AccessContext(user)
    employee = await session.get(Employee, user.employee_id) if user.employee_id else None
    if not employee or employee.status not in {"ACTIVE", "PROBATION"}:
        raise HTTPException(401, "员工账号已失效，请重新登录")
    grants = (
        await session.execute(
            select(Role, UserRoleGrant)
            .join(UserRoleGrant, Role.id == UserRoleGrant.role_id)
            .where(UserRoleGrant.user_id == user.id, Role.status == "ACTIVE")
        )
    ).all()
    orgs = (await session.scalars(select(OrgUnit).where(OrgUnit.status == "ACTIVE"))).all()
    warehouses = (await session.scalars(select(Warehouse))).all()
    employees = (await session.scalars(select(Employee))).all()
    return AccessContext(user, employee, grants, orgs, warehouses, employees)


async def get_access(session: SessionDep, user: CurrentUserDep):
    return await build_access(session, user)


AccessDep = Annotated[AccessContext, Depends(get_access)]


def redact_cost(data, access, warehouse_id=None):
    result = dict(data)
    if not access.has("catalog.cost", global_scope=True):
        result.pop("purchase_base_price", None)
    visible = (
        access.has("catalog.cost", global_scope=True)
        if warehouse_id is None
        else access.allows_warehouse("catalog.cost", warehouse_id)
    )
    if not visible:
        for key in (
            "purchase_base_price",
            "unit_cost",
            "total_amount",
            "amount",
            "average_cost",
            "total_cost",
        ):
            result.pop(key, None)
    return result
