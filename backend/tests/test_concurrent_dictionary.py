from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.database import make_database
from app.modules.auth.models import User
from app.modules.catalog.models import SKU, Color, Product, SizeGroup
from app.modules.catalog.schemas import SizeGroupUpdate
from app.modules.catalog.service import save_group, validate_color


@pytest.mark.parametrize("kind", ["color", "group"])
async def test_reference_check_sees_product_committed_after_authentication_snapshot(
    kind, matrix, db_session, test_settings
):
    engine, factory = make_database(test_settings)
    model = Color if kind == "color" else SizeGroup
    identifier = matrix["color_ids"][0] if kind == "color" else matrix["size_group_id"]
    async with factory() as editor:
        # Transaction B establishes its snapshot before transaction A creates a reference.
        actor = await editor.scalar(select(User).where(User.username == "tester"))
        existing = await editor.get(model, identifier)
        original_code = existing.code
        # Transaction A holds the dictionary row lock and commits a new product reference.
        await db_session.execute(select(model).where(model.id == identifier).with_for_update())
        product = Product(
            code="CONCURRENT",
            name="并发商品",
            category="裙装",
            year=2026,
            season="春夏",
            tag_price=Decimal("599.00"),
            size_group_id=matrix["size_group_id"],
        )
        db_session.add(product)
        await db_session.flush()
        cell = matrix["skus"][0]
        db_session.add(
            SKU(
                product_id=product.id,
                color_id=cell["color_id"],
                size_id=cell["size_id"],
                code="CONCURRENT-SKU",
                barcode="CONCURRENT-SKU",
                retail_price=Decimal("599.00"),
            )
        )
        await db_session.commit()
        # B's ordinary reads still see its old snapshot; the service must use current reads.
        with pytest.raises(HTTPException) as failure:
            if kind == "color":
                await validate_color(editor, {"code": "CHANGED"}, existing)
            else:
                await save_group(editor, actor, SizeGroupUpdate(code="CHANGED"), existing)
        assert failure.value.status_code == 409
        await editor.rollback()
        await db_session.refresh(await db_session.get(model, identifier))
        assert (await db_session.get(model, identifier)).code == original_code
    await engine.dispose()
