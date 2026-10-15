from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select

from app.common.archives import find_record, record_data
from app.common.responses import payload
from app.modules.auth.service import AdminDep, SessionDep
from app.modules.catalog.models import SKU, Color, Product, Size
from app.modules.inventory.models import (
    PurchaseReceipt,
    PurchaseReceiptLine,
    StockBalance,
    StockMovement,
)
from app.modules.organization.models import Warehouse
from app.modules.suppliers.models import Supplier

router = APIRouter(tags=["采购与库存"])
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


async def page_rows(session, query, page, page_size):
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await session.execute(query.offset((page - 1) * page_size).limit(page_size))).all()
    return total, rows


def sku_fields():
    return [
        SKU.barcode,
        Product.id.label("product_id"),
        Product.code.label("product_code"),
        Product.name.label("product_name"),
        Color.name.label("color_name"),
        Size.name.label("size_name"),
        Warehouse.name.label("warehouse_name"),
    ]


@router.get("/purchase-receipts")
async def receipts(
    session: SessionDep,
    user: AdminDep,
    keyword: str = "",
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
):
    query = (
        select(
            PurchaseReceipt,
            Supplier.name.label("supplier_name"),
            Warehouse.name.label("warehouse_name"),
            Product.code.label("product_code"),
            Product.name.label("product_name"),
        )
        .join(Supplier, PurchaseReceipt.supplier_id == Supplier.id)
        .join(Warehouse, PurchaseReceipt.warehouse_id == Warehouse.id)
        .join(Product, PurchaseReceipt.product_id == Product.id)
        .where(PurchaseReceipt.status == "POSTED")
    )
    if keyword:
        query = query.where(
            or_(
                PurchaseReceipt.number.contains(keyword, autoescape=True),
                Product.code.contains(keyword, autoescape=True),
                Product.name.contains(keyword, autoescape=True),
                Supplier.name.contains(keyword, autoescape=True),
            )
        )
    if warehouse_id:
        query = query.where(PurchaseReceipt.warehouse_id == warehouse_id)
    total, rows = await page_rows(
        session, query.order_by(PurchaseReceipt.id.desc()), page, page_size
    )
    return payload(
        {
            "items": [
                {
                    **record_data(row[0]),
                    **{
                        key: value
                        for key, value in row._mapping.items()
                        if key != "PurchaseReceipt"
                    },
                }
                for row in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/purchase-receipts/{record_id}")
async def receipt_detail(record_id: int, session: SessionDep, user: AdminDep):
    receipt = await find_record(session, PurchaseReceipt, record_id)
    if receipt.status != "POSTED":
        raise HTTPException(404, "采购入库单不存在")
    supplier = await find_record(session, Supplier, receipt.supplier_id)
    warehouse = await find_record(session, Warehouse, receipt.warehouse_id)
    rows = (
        await session.execute(
            select(
                PurchaseReceiptLine,
                SKU.barcode,
                Color.name.label("color_name"),
                Size.name.label("size_name"),
            )
            .join(SKU, PurchaseReceiptLine.sku_id == SKU.id)
            .join(Color, SKU.color_id == Color.id)
            .join(Size, SKU.size_id == Size.id)
            .where(PurchaseReceiptLine.receipt_id == record_id)
            .order_by(PurchaseReceiptLine.id)
        )
    ).all()
    return payload(
        {
            **record_data(receipt),
            "supplier_name": supplier.name,
            "warehouse_name": warehouse.name,
            "lines": [
                {
                    **record_data(row[0]),
                    "barcode": row.barcode,
                    "color_name": row.color_name,
                    "size_name": row.size_name,
                }
                for row in rows
            ],
        }
    )


@router.get("/inventory/movements")
async def movements(
    session: SessionDep,
    user: AdminDep,
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
):
    query = (
        select(StockMovement, PurchaseReceipt.number.label("receipt_number"), *sku_fields())
        .join(PurchaseReceiptLine, StockMovement.receipt_line_id == PurchaseReceiptLine.id)
        .join(PurchaseReceipt, PurchaseReceiptLine.receipt_id == PurchaseReceipt.id)
        .join(SKU, StockMovement.sku_id == SKU.id)
        .join(Product, SKU.product_id == Product.id)
        .join(Color, SKU.color_id == Color.id)
        .join(Size, SKU.size_id == Size.id)
        .join(Warehouse, StockMovement.warehouse_id == Warehouse.id)
    )
    if warehouse_id:
        query = query.where(StockMovement.warehouse_id == warehouse_id)
    total, rows = await page_rows(session, query.order_by(StockMovement.id.desc()), page, page_size)
    return payload(
        {
            "items": [
                {
                    **record_data(row[0]),
                    **{key: value for key, value in row._mapping.items() if key != "StockMovement"},
                }
                for row in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/inventory")
async def inventory(
    session: SessionDep,
    user: AdminDep,
    keyword: str = "",
    warehouse_id: Annotated[int | None, Query(gt=0)] = None,
    page: PageNumber = 1,
    page_size: PageSize = 20,
):
    query = (
        select(StockBalance, *sku_fields())
        .join(SKU, StockBalance.sku_id == SKU.id)
        .join(Product, SKU.product_id == Product.id)
        .join(Color, SKU.color_id == Color.id)
        .join(Size, SKU.size_id == Size.id)
        .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
    )
    if warehouse_id:
        query = query.where(StockBalance.warehouse_id == warehouse_id)
    if keyword:
        query = query.where(
            or_(
                SKU.barcode.contains(keyword, autoescape=True),
                Product.code.contains(keyword, autoescape=True),
                Product.name.contains(keyword, autoescape=True),
            )
        )
    total, rows = await page_rows(session, query.order_by(StockBalance.id.desc()), page, page_size)
    items = []
    for row in rows:
        item = {
            **record_data(row[0]),
            **{key: value for key, value in row._mapping.items() if key != "StockBalance"},
        }
        item["average_cost"] = format(row[0].average_cost, ".4f")
        item["total_cost"] = format(row[0].total_cost, ".4f")
        items.append(item)
    return payload({"items": items, "total": total, "page": page, "page_size": page_size})
