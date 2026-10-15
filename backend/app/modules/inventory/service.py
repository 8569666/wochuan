import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from app.common.archives import record_data
from app.models import utcnow
from app.modules.audit.service import record_audit
from app.modules.catalog.models import SKU
from app.modules.inventory.models import (
    PurchaseReceipt,
    PurchaseReceiptLine,
    StockBalance,
    StockMovement,
)
from app.modules.organization.models import Store, Warehouse
from app.modules.suppliers.models import Supplier


async def prepare_receipt(session, actor, body, product_id=None):
    receiving = body.receiving
    if not receiving:
        return None, None
    # The warehouse row serializes receipts, including their idempotency claim.
    warehouse = await session.scalar(
        select(Warehouse).where(Warehouse.id == receiving.warehouse_id).with_for_update()
    )
    supplier = await session.scalar(
        select(Supplier).where(Supplier.id == receiving.supplier_id).with_for_update()
    )
    if not warehouse or not supplier:
        raise HTTPException(422, "请选择有效供应商和收货仓库")
    content = body.model_dump(mode="json")
    content["receiving"].pop("request_id")
    digest = hashlib.sha256(
        json.dumps(
            {"actor": actor.id, "product": product_id, "body": content},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    statement = insert(PurchaseReceipt).values(
        number=f"PI{(datetime.now(UTC) + timedelta(hours=8)):%Y%m%d}-{secrets.token_hex(8).upper()}",
        request_id=str(receiving.request_id),
        fingerprint=digest,
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        actor_id=actor.id,
        # Delay the product FK until catalog has acquired the product write lock.
        product_id=None,
        status="DRAFT",
        unit_cost=receiving.unit_cost,
        total_quantity=0,
        total_amount=Decimal("0"),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    await session.execute(statement.on_duplicate_key_update(request_id=PurchaseReceipt.request_id))
    receipt = await session.scalar(
        select(PurchaseReceipt)
        .where(PurchaseReceipt.request_id == str(receiving.request_id))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not receipt or receipt.fingerprint != digest:
        raise HTTPException(409, "该进货请求已使用，请刷新查看原采购入库单；修改内容后需重新发起")
    if receipt.status == "POSTED":
        return receipt, receipt.product_id
    if warehouse.status != "ACTIVE" or supplier.status != "ACTIVE":
        raise HTTPException(422, "供应商或收货仓库已停用")
    if warehouse.store_id:
        store = await session.scalar(
            select(Store).where(Store.id == warehouse.store_id).with_for_update()
        )
        if not store or store.status != "ACTIVE":
            raise HTTPException(422, "收货店仓所属门店已停用")
    return receipt, None


async def post_receipt(session, actor, product, receiving, receipt):
    if not receipt:
        return
    if product.status != "ACTIVE":
        raise HTTPException(422, "停用商品不能采购入库")
    total_quantity = sum(cell.quantity for cell in receiving.quantities)
    if receiving.unit_cost * total_quantity >= Decimal("1000000000000000000"):
        raise HTTPException(422, "本次采购总金额超过允许范围，请拆分入库")
    await session.flush()
    skus = (
        await session.scalars(
            select(SKU).where(SKU.product_id == product.id).order_by(SKU.id).with_for_update()
        )
    ).all()
    by_cell = {(sku.color_id, sku.size_id): sku for sku in skus}
    requested = []
    for cell in receiving.quantities:
        sku = by_cell.get((cell.color_id, cell.size_id))
        if not sku:
            raise HTTPException(422, "进货数量包含不属于本商品的规格")
        requested.append((sku, cell.quantity))
    total_quantity = 0
    for sku, quantity in sorted(requested, key=lambda pair: pair[0].id):
        statement = insert(StockBalance).values(
            warehouse_id=receipt.warehouse_id,
            sku_id=sku.id,
            quantity=0,
            average_cost=Decimal("0"),
            total_cost=Decimal("0"),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        await session.execute(statement.on_duplicate_key_update(quantity=StockBalance.quantity))
        balance = await session.scalar(
            select(StockBalance)
            .where(StockBalance.warehouse_id == receipt.warehouse_id, StockBalance.sku_id == sku.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        before = balance.quantity
        after = before + quantity
        if after > 9000000000000000:
            raise HTTPException(422, "库存数量超过允许范围")
        amount = receiving.unit_cost * quantity
        total_cost = balance.total_cost + amount
        if total_cost >= Decimal("100000000000000000000"):
            raise HTTPException(422, "库存金额超过允许范围")
        balance.quantity = after
        balance.total_cost = total_cost
        balance.average_cost = (total_cost / after).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        line = PurchaseReceiptLine(
            receipt_id=receipt.id,
            sku_id=sku.id,
            quantity=quantity,
            unit_cost=receiving.unit_cost,
            amount=amount,
        )
        session.add(line)
        await session.flush()
        session.add(
            StockMovement(
                receipt_line_id=line.id,
                warehouse_id=receipt.warehouse_id,
                sku_id=sku.id,
                actor_id=actor.id,
                before_quantity=before,
                quantity=quantity,
                after_quantity=after,
                amount=amount,
            )
        )
        total_quantity += quantity
    receipt.product_id = product.id
    receipt.total_quantity = total_quantity
    receipt.total_amount = receiving.unit_cost * total_quantity
    receipt.status = "POSTED"
    record_audit(
        session,
        actor.id,
        "POST",
        "werp_purchase_receipts",
        receipt.id,
        {
            "number": receipt.number,
            "product_id": product.id,
            "quantity": total_quantity,
            "amount": receipt.total_amount,
        },
    )


def receipt_summary(receipt):
    return record_data(receipt) if receipt else None
