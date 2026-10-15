from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.mysql import insert

from app.common.archives import archive_router, find_record, list_records, record_data
from app.common.responses import payload
from app.common.schemas import partial_schema
from app.models import utcnow
from app.modules.access.service import AccessDep, redact_cost, require_permission
from app.modules.audit.service import record_audit
from app.modules.auth.service import SessionDep
from app.modules.catalog.models import (
    SKU,
    CatalogPreference,
    Category,
    Color,
    Fabric,
    Product,
    SizeGroup,
)
from app.modules.catalog.schemas import (
    CategoryCreate,
    ColorCreate,
    ColorUpdate,
    FabricCreate,
    PreferenceUpdate,
    ProductCreate,
    ProductUpdate,
    SizeGroupCreate,
    SizeGroupUpdate,
)
from app.modules.catalog.service import (
    authorize_product_change,
    create_product,
    group_data,
    product_data,
    save_group,
    update_product,
    validate_color,
)
from app.modules.organization.models import Store, Warehouse
from app.modules.suppliers.models import Supplier

router = APIRouter(tags=["商品"])
router.include_router(archive_router("/colors", Color, ColorCreate, ColorUpdate, validate_color))
router.include_router(
    archive_router("/categories", Category, CategoryCreate, partial_schema(CategoryCreate))
)
router.include_router(
    archive_router("/fabrics", Fabric, FabricCreate, partial_schema(FabricCreate))
)


def preference_model(kind):
    if kind not in {"colors", "size-groups"}:
        raise HTTPException(404, "常用选项类型不存在")
    return Color if kind == "colors" else SizeGroup


@router.get("/catalog-preferences/{kind}")
async def preference_detail(kind: str, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.read", global_scope=False)
    model = preference_model(kind)
    preference = await session.scalar(
        select(CatalogPreference).where(CatalogPreference.kind == kind)
    )
    active = list(
        (
            await session.scalars(
                select(model.id).where(model.status == "ACTIVE").order_by(model.id)
            )
        ).all()
    )
    return payload(
        {
            "ids": [identifier for identifier in preference.ids if identifier in active]
            if preference
            else active[:10]
        }
    )


@router.put("/catalog-preferences/{kind}")
async def preference_update(
    kind: str, body: PreferenceUpdate, session: SessionDep, user: AccessDep
):
    require_permission(user, "catalog.write", global_scope=True)
    model = preference_model(kind)
    active = (
        await session.scalars(
            select(model.id)
            .where(model.id.in_(body.ids), model.status == "ACTIVE")
            .order_by(model.id)
            .with_for_update()
        )
    ).all()
    if set(active) != set(body.ids):
        raise HTTPException(422, "常用列表只能包含有效选项")
    statement = insert(CatalogPreference).values(
        kind=kind, ids=body.ids, created_at=utcnow(), updated_at=utcnow()
    )
    await session.execute(statement.on_duplicate_key_update(ids=body.ids, updated_at=utcnow()))
    preference = await session.scalar(
        select(CatalogPreference).where(CatalogPreference.kind == kind).with_for_update()
    )
    record_audit(
        session,
        user.id,
        "UPDATE",
        CatalogPreference.__tablename__,
        preference.id,
        {"kind": kind, "ids": body.ids},
    )
    await session.commit()
    return payload({"ids": body.ids})


@router.get("/size-groups")
async def groups(
    session: SessionDep,
    user: AccessDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    require_permission(user, "catalog.read", global_scope=False)
    result = await list_records(session, SizeGroup, keyword, status, page, page_size)
    for item in result["items"]:
        item.update(await group_data(session, await session.get(SizeGroup, item["id"])))
    return payload(result)


@router.get("/size-groups/{record_id}")
async def group_detail(record_id: int, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.read", global_scope=False)
    return payload(await group_data(session, await find_record(session, SizeGroup, record_id)))


@router.post("/size-groups", status_code=201)
async def create_group(body: SizeGroupCreate, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.write", global_scope=True)
    return payload(await save_group(session, user, body), code=201)


@router.patch("/size-groups/{record_id}")
async def update_group(record_id: int, body: SizeGroupUpdate, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.write", global_scope=True)
    return payload(
        await save_group(session, user, body, await find_record(session, SizeGroup, record_id))
    )


@router.get("/products")
async def products(
    session: SessionDep,
    user: AccessDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    require_permission(user, "catalog.read", global_scope=False)
    filters = []
    if keyword:
        barcode_ids = select(SKU.product_id).where(SKU.barcode.contains(keyword, autoescape=True))
        filters.append(
            or_(
                Product.code.contains(keyword, autoescape=True),
                Product.name.contains(keyword, autoescape=True),
                Product.id.in_(barcode_ids),
            )
        )
    if status:
        filters.append(Product.status == status)
    total = await session.scalar(select(func.count()).select_from(Product).where(*filters))
    items = (
        await session.scalars(
            select(Product)
            .where(*filters)
            .order_by(Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    data = []
    for item in items:
        count = await session.scalar(
            select(func.count()).select_from(SKU).where(SKU.product_id == item.id)
        )
        data.append({**redact_cost(record_data(item), user), "sku_count": count})
    return payload({"items": data, "total": total, "page": page, "page_size": page_size})


@router.post("/products", status_code=201)
async def new_product(body: ProductCreate, session: SessionDep, user: AccessDep):
    return payload(await create_product(session, user, body), code=201)


@router.get("/products/{record_id}")
async def product_detail(record_id: int, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.read", global_scope=False)
    return payload(
        await product_data(session, await find_record(session, Product, record_id), user)
    )


@router.patch("/products/{record_id}")
async def product_update(record_id: int, body: ProductUpdate, session: SessionDep, user: AccessDep):
    authorize_product_change(user, body)
    return payload(
        await update_product(session, user, await find_record(session, Product, record_id), body)
    )


@router.get("/products/{record_id}/skus")
async def product_skus(record_id: int, session: SessionDep, user: AccessDep):
    require_permission(user, "catalog.read", global_scope=False)
    return payload(
        (await product_data(session, await find_record(session, Product, record_id), user))["skus"]
    )


@router.get("/dashboard/summary")
async def summary(session: SessionDep, user: AccessDep):
    require_permission(user, "dashboard.read", global_scope=False)
    result = {}
    for name, model in [
        ("stores", Store),
        ("warehouses", Warehouse),
        ("suppliers", Supplier),
        ("products", Product),
        ("skus", SKU),
    ]:
        read_permission = {
            "stores": "store.read",
            "warehouses": "warehouse.read",
            "suppliers": "supplier.read",
            "products": "catalog.read",
            "skus": "catalog.read",
        }[name]
        if not user.has(read_permission):
            result[name] = 0
            continue
        query = select(func.count()).select_from(model)
        ids = (
            user.store_ids(read_permission)
            if name == "stores"
            else user.warehouse_ids(read_permission)
            if name == "warehouses"
            else None
        )
        if ids is not None:
            query = query.where(model.id.in_(ids))
        result[name] = await session.scalar(query)
    return payload(result)
