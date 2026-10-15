from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.common.archives import commit_record, find_record, record_data
from app.modules.catalog.models import SKU, Category, Color, Fabric, Product, Size, SizeGroup
from app.modules.inventory.service import post_receipt, prepare_receipt, receipt_summary


async def resolve_product_dictionaries(session, values, existing=None):
    if "category_id" in values and values["category_id"] is None:
        raise HTTPException(422, "品类不能为空")
    category_id = values.get("category_id", existing.category_id if existing else None)
    fabric_id = values.get("fabric_id", existing.fabric_id if existing else None)
    if values.get("fabric_composition") and not fabric_id:
        raise HTTPException(422, "面料成分必须从面料档案选择")
    category = None
    if category_id:
        category = await session.scalar(
            select(Category)
            .where(Category.id == category_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not category or (
            category.status != "ACTIVE" and (not existing or category_id != existing.category_id)
        ):
            raise HTTPException(422, "请选择有效品类")
        values["category"] = category.name
    if fabric_id:
        fabric = await session.scalar(
            select(Fabric)
            .where(Fabric.id == fabric_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not fabric or (
            fabric.status != "ACTIVE" and (not existing or fabric_id != existing.fabric_id)
        ):
            raise HTTPException(422, "请选择有效面料成分")
        values["fabric_composition"] = fabric.composition
    elif "fabric_id" in values:
        values["fabric_composition"] = None
    if category and (not existing or "category_id" in values or "fabric_id" in values):
        category.last_fabric_id = fabric_id


async def append_product_colors(session, product, additions):
    current = (
        await session.scalars(select(SKU).where(SKU.product_id == product.id).with_for_update())
    ).all()
    previous_colors = {sku.color_id for sku in current}
    size_ids = {sku.size_id for sku in current}
    color_ids = {cell["color_id"] for cell in additions}
    if color_ids & previous_colors:
        raise HTTPException(409, "颜色已存在，请刷新商品后重试")
    if len(previous_colors | color_ids) > 30:
        raise HTTPException(422, "一个商品最多选择30种颜色")
    sizes = (
        await session.scalars(
            select(Size).where(Size.id.in_(size_ids)).order_by(Size.id).with_for_update()
        )
    ).all()
    colors = (
        await session.scalars(
            select(Color).where(Color.id.in_(color_ids)).order_by(Color.id).with_for_update()
        )
    ).all()
    if len(colors) != len(color_ids) or any(color.status != "ACTIVE" for color in colors):
        raise HTTPException(422, "请选择有效颜色")
    expected = {(color_id, size_id) for color_id in color_ids for size_id in size_ids}
    actual = {(cell["color_id"], cell["size_id"]) for cell in additions}
    if not expected or expected != actual or len(additions) != len(expected):
        raise HTTPException(422, "新增颜色必须覆盖商品原有全部尺码且不能重复")
    color_map = {color.id: color for color in colors}
    size_map = {size.id: size for size in sizes}
    for cell in additions:
        code = f"{product.code}-{color_map[cell['color_id']].code}-{size_map[cell['size_id']].code}"
        if len(code) > 64:
            raise HTTPException(422, "生成的规格编码超过64字符")
        session.add(
            SKU(
                product_id=product.id,
                **{**cell, "code": code, "barcode": cell.get("barcode") or code},
            )
        )


async def validate_color(session, values, existing):
    if existing and "code" in values:
        await session.refresh(existing, with_for_update=True)
        if values["code"] == existing.code:
            return
        if await session.scalar(
            select(SKU.id).where(SKU.color_id == existing.id).limit(1).with_for_update()
        ):
            raise HTTPException(409, "颜色已被商品引用，编码不能修改")


async def group_data(session, group):
    result = record_data(group)
    sizes = (
        await session.scalars(
            select(Size).where(Size.group_id == group.id).order_by(Size.position, Size.id)
        )
    ).all()
    result["sizes"] = [record_data(size) for size in sizes]
    return result


async def save_group(session, user, body, existing=None):
    values = body.model_dump(exclude_unset=bool(existing))
    sizes = values.pop("sizes", None)
    if existing:
        await session.refresh(existing, with_for_update=True)
        referenced = await session.scalar(
            select(Product.id)
            .where(Product.size_group_id == existing.id)
            .limit(1)
            .with_for_update()
        )
        if referenced and (sizes is not None or values.get("code", existing.code) != existing.code):
            raise HTTPException(409, "尺码组已被商品引用，编码和尺码项不能修改")
        group = existing
        for key, value in values.items():
            if value is None:
                raise HTTPException(422, "必填字段不能为空")
            setattr(group, key, value)
        if sizes is not None:
            await session.execute(delete(Size).where(Size.group_id == group.id))
    else:
        group = SizeGroup(**values)
        session.add(group)
    try:
        await session.flush()
        if sizes is not None:
            for position, size in enumerate(sizes):
                session.add(
                    Size(
                        group_id=group.id,
                        position=position,
                        code=size["code"],
                        name=size["name"],
                        status=size.get("status", "ACTIVE"),
                    )
                )
        await commit_record(
            session, group, user, {**values, "sizes": sizes}, "UPDATE" if existing else "CREATE"
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "编码或关联关系重复，请检查后重试") from None
    except Exception:
        await session.rollback()
        raise
    return await group_data(session, group)


async def product_data(session, product):
    result = record_data(product)
    rows = (
        await session.execute(
            select(SKU, Color, Size)
            .join(Color, SKU.color_id == Color.id)
            .join(Size, SKU.size_id == Size.id)
            .where(SKU.product_id == product.id)
            .order_by(Color.id, Size.position, SKU.id)
        )
    ).all()
    result["skus"] = [
        {**record_data(sku), "color": record_data(color), "size": record_data(size)}
        for sku, color, size in rows
    ]
    return result


async def create_product(session, actor, body):
    receipt, replay_id = await prepare_receipt(session, actor, body)
    if replay_id:
        await session.commit()
        result = await product_data(session, await find_record(session, Product, replay_id))
        result["receipt"] = receipt_summary(receipt)
        return result
    group = await session.scalar(
        select(SizeGroup).where(SizeGroup.id == body.size_group_id).with_for_update()
    )
    if not group or group.status != "ACTIVE":
        raise HTTPException(422, "请选择有效尺码组")
    sizes = (
        await session.scalars(
            select(Size)
            .where(Size.group_id == group.id, Size.status == "ACTIVE")
            .order_by(Size.id)
            .with_for_update()
        )
    ).all()
    colors = (
        await session.scalars(
            select(Color).where(Color.id.in_(body.color_ids)).order_by(Color.id).with_for_update()
        )
    ).all()
    if (
        len(set(body.color_ids)) != len(body.color_ids)
        or len(colors) != len(body.color_ids)
        or any(color.status != "ACTIVE" for color in colors)
    ):
        raise HTTPException(422, "颜色重复或已停用，请重新选择")
    expected = {(color.id, size.id) for color in colors for size in sizes}
    actual = {(sku.color_id, sku.size_id) for sku in body.skus}
    if actual != expected or len(body.skus) != len(expected):
        raise HTTPException(422, "颜色尺码矩阵必须完整且不能重复")
    color_map = {color.id: color for color in colors}
    size_map = {size.id: size for size in sizes}
    sku_values = []
    for item in body.skus:
        code = f"{body.code}-{color_map[item.color_id].code}-{size_map[item.size_id].code}"
        if len(code) > 64:
            raise HTTPException(422, "生成的规格编码超过64字符，请缩短款号或字典编码")
        sku_values.append({**item.model_dump(), "code": code, "barcode": item.barcode or code})
    values = body.model_dump(exclude={"color_ids", "skus", "receiving"})
    await resolve_product_dictionaries(session, values)
    product = Product(**values)
    session.add(product)
    try:
        await session.flush()
        session.add_all([SKU(product_id=product.id, **item) for item in sku_values])
        await post_receipt(session, actor, product, body.receiving, receipt)
        await commit_record(
            session, product, actor, {"code": product.code, "sku_count": len(sku_values)}, "CREATE"
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "款号或条码重复，请检查后重试") from None
    except Exception:
        await session.rollback()
        raise
    result = await product_data(session, product)
    result["receipt"] = receipt_summary(receipt)
    return result


async def update_product(session, actor, product, body):
    try:
        return await _update_product(session, actor, product, body)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "款号、条码或规格重复，请检查后重试") from None


async def _update_product(session, actor, product, body):
    receipt, replay_id = await prepare_receipt(session, actor, body, product.id)
    if replay_id:
        await session.commit()
        await session.refresh(product)
        result = await product_data(session, product)
        result["receipt"] = receipt_summary(receipt)
        return result
    await session.execute(
        select(SizeGroup).where(SizeGroup.id == product.size_group_id).with_for_update()
    )
    await session.refresh(product, with_for_update=True)
    values = body.model_dump(exclude_unset=True)
    values.pop("receiving", None)
    if "code" in values and values["code"] != product.code:
        raise HTTPException(409, "商品款号已经生成规格，不能修改")
    sku_prices = values.pop("sku_prices", None)
    additions = values.pop("new_skus", None)
    if additions:
        await append_product_colors(session, product, additions)
    await resolve_product_dictionaries(session, values, product)
    for key, value in values.items():
        if value is None and not Product.__table__.columns[key].nullable:
            raise HTTPException(422, "必填字段不能为空")
        setattr(product, key, value)
    if sku_prices is not None:
        if len({item["id"] for item in sku_prices}) != len(sku_prices):
            raise HTTPException(422, "规格价格不能重复")
        for item in sku_prices:
            sku = await find_record(session, SKU, item["id"])
            if sku.product_id != product.id:
                raise HTTPException(422, "规格不属于当前商品")
            sku.retail_price = item["retail_price"]
    await post_receipt(session, actor, product, body.receiving, receipt)
    await commit_record(
        session,
        product,
        actor,
        {**values, "sku_prices": sku_prices, "new_skus": additions},
        "UPDATE",
    )
    result = await product_data(session, product)
    result["receipt"] = receipt_summary(receipt)
    return result
