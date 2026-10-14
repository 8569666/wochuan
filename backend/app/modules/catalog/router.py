from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.common.archives import archive_router, find_record, list_records, record_data
from app.common.responses import payload
from app.modules.auth.service import AdminDep, SessionDep
from app.modules.catalog.models import SKU, Color, Product, SizeGroup
from app.modules.catalog.schemas import (
    ColorCreate,
    ColorUpdate,
    ProductCreate,
    ProductUpdate,
    SizeGroupCreate,
    SizeGroupUpdate,
)
from app.modules.catalog.service import (
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


@router.get("/size-groups")
async def groups(
    session: SessionDep,
    user: AdminDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    result = await list_records(session, SizeGroup, keyword, status, page, page_size)
    for item in result["items"]:
        item.update(await group_data(session, await session.get(SizeGroup, item["id"])))
    return payload(result)


@router.get("/size-groups/{record_id}")
async def group_detail(record_id: int, session: SessionDep, user: AdminDep):
    return payload(await group_data(session, await find_record(session, SizeGroup, record_id)))


@router.post("/size-groups", status_code=201)
async def create_group(body: SizeGroupCreate, session: SessionDep, user: AdminDep):
    return payload(await save_group(session, user, body), code=201)


@router.patch("/size-groups/{record_id}")
async def update_group(record_id: int, body: SizeGroupUpdate, session: SessionDep, user: AdminDep):
    return payload(
        await save_group(session, user, body, await find_record(session, SizeGroup, record_id))
    )


@router.get("/products")
async def products(
    session: SessionDep,
    user: AdminDep,
    keyword: str = "",
    status: Literal["ACTIVE", "INACTIVE"] | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
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
        data.append({**record_data(item), "sku_count": count})
    return payload({"items": data, "total": total, "page": page, "page_size": page_size})


@router.post("/products", status_code=201)
async def new_product(body: ProductCreate, session: SessionDep, user: AdminDep):
    return payload(await create_product(session, user, body), code=201)


@router.get("/products/{record_id}")
async def product_detail(record_id: int, session: SessionDep, user: AdminDep):
    return payload(await product_data(session, await find_record(session, Product, record_id)))


@router.patch("/products/{record_id}")
async def product_update(record_id: int, body: ProductUpdate, session: SessionDep, user: AdminDep):
    return payload(
        await update_product(session, user, await find_record(session, Product, record_id), body)
    )


@router.get("/products/{record_id}/skus")
async def product_skus(record_id: int, session: SessionDep, user: AdminDep):
    return payload(
        (await product_data(session, await find_record(session, Product, record_id)))["skus"]
    )


@router.get("/dashboard/summary")
async def summary(session: SessionDep, user: AdminDep):
    result = {}
    for name, model in [
        ("stores", Store),
        ("warehouses", Warehouse),
        ("suppliers", Supplier),
        ("products", Product),
        ("skus", SKU),
    ]:
        result[name] = await session.scalar(select(func.count()).select_from(model))
    return payload(result)
