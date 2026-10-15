"""Personnel organization and scoped roles."""

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

from alembic import op

revision = "0004_people_access"
down_revision = "0003_product_receiving"
branch_labels = None
depends_on = None
OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


def base(archive=False):
    cols = [
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
    ]
    if archive:
        cols += [
            sa.Column("code", sa.String(64), nullable=False, unique=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
        ]
    return cols


def fk(name, target, nullable=False, unique=False, ondelete=None):
    return sa.Column(
        name,
        sa.BigInteger(),
        sa.ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        unique=unique,
    )


def upgrade():
    op.create_table(
        "werp_org_units",
        *base(True),
        sa.Column("kind", sa.String(24), nullable=False),
        fk("parent_id", "werp_org_units.id", True, ondelete="SET NULL"),
        fk("store_id", "werp_stores.id", True, True),
        fk("warehouse_id", "werp_warehouses.id", True, True),
        **OPTIONS,
    )
    op.create_table("werp_positions", *base(True), **OPTIONS)
    op.create_table(
        "werp_employees",
        *base(True),
        sa.Column("phone", sa.String(32)),
        sa.Column("personnel_type", sa.String(24), nullable=False),
        fk("company_id", "werp_org_units.id"),
        fk("org_unit_id", "werp_org_units.id"),
        fk("position_id", "werp_positions.id"),
        fk("manager_id", "werp_employees.id", True, ondelete="SET NULL"),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("confirmation_date", sa.Date()),
        sa.Column("left_date", sa.Date()),
        **OPTIONS,
    )
    op.add_column("werp_users", sa.Column("employee_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_users_employee", "werp_users", "werp_employees", ["employee_id"], ["id"]
    )
    op.create_unique_constraint("uq_users_employee", "werp_users", ["employee_id"])
    op.create_table(
        "werp_roles", *base(True), sa.Column("permissions", sa.JSON(), nullable=False), **OPTIONS
    )
    op.create_table(
        "werp_user_role_grants",
        *base(),
        fk("user_id", "werp_users.id"),
        fk("role_id", "werp_roles.id"),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_ids", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", "scope_type"),
        **OPTIONS,
    )
    op.create_table(
        "werp_assignments",
        *base(),
        fk("employee_id", "werp_employees.id"),
        fk("org_unit_id", "werp_org_units.id"),
        fk("position_id", "werp_positions.id"),
        fk("manager_id", "werp_employees.id", True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        **OPTIONS,
    )
    op.create_table(
        "werp_personnel_events",
        *base(),
        fk("employee_id", "werp_employees.id"),
        fk("actor_id", "werp_users.id"),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(255)),
        fk("handover_employee_id", "werp_employees.id", True),
        sa.Column("handover_notes", sa.Text()),
        sa.Column("before_data", sa.JSON(), nullable=False),
        sa.Column("after_data", sa.JSON(), nullable=False),
        **OPTIONS,
    )
    roles = sa.table(
        "werp_roles",
        sa.column("code"),
        sa.column("name"),
        sa.column("status"),
        sa.column("permissions", sa.JSON()),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    presets = [
        (
            "HR",
            "人事管理员",
            [
                "org.read",
                "org.manage",
                "position.read",
                "position.manage",
                "employee.read",
                "employee.manage",
                "employee.transfer",
                "employee.leave",
                "employee.self",
            ],
        ),
        (
            "STORE_MANAGER",
            "店长",
            [
                "dashboard.read",
                "store.read",
                "warehouse.read",
                "catalog.read",
                "inventory.read",
                "purchase.read",
                "employee.read",
                "employee.self",
            ],
        ),
        (
            "WAREHOUSE",
            "仓管员",
            [
                "warehouse.read",
                "supplier.read",
                "catalog.read",
                "inventory.read",
                "purchase.read",
                "purchase.receive",
                "catalog.cost",
                "employee.self",
            ],
        ),
        (
            "BUYER",
            "采购员",
            [
                "supplier.read",
                "supplier.write",
                "catalog.read",
                "catalog.write",
                "catalog.cost",
                "purchase.read",
                "purchase.receive",
                "inventory.read",
                "employee.self",
            ],
        ),
        ("STAFF", "普通员工", ["employee.self"]),
    ]
    op.bulk_insert(
        roles,
        [
            dict(code=c, name=n, status="ACTIVE", permissions=p, created_at=now, updated_at=now)
            for c, n, p in presets
        ],
    )


def downgrade():
    for table in [
        "werp_personnel_events",
        "werp_assignments",
        "werp_user_role_grants",
        "werp_roles",
    ]:
        op.drop_table(table)
    op.drop_constraint("fk_users_employee", "werp_users", type_="foreignkey")
    op.drop_constraint("uq_users_employee", "werp_users", type_="unique")
    op.drop_column("werp_users", "employee_id")
    for table in ["werp_employees", "werp_positions", "werp_org_units"]:
        op.drop_table(table)
