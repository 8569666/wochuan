from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.common.archives import commit_record, find_record, record_data
from app.modules.catalog.models import SKU, Color, Product, Size, SizeGroup


async def validate_color(session, values, existing):
    if existing and values.get("code", existing.code) != existing.code:
        await session.execute(select(Color).where(Color.id == existing.id).with_for_update())
        if await session.scalar(select(SKU.id).where(SKU.color_id == existing.id).limit(1)):
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
        await session.execute(
            select(SizeGroup).where(SizeGroup.id == existing.id).with_for_update()
        )
        referenced = await session.scalar(
            select(Product.id).where(Product.size_group_id == existing.id).limit(1)
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
    group = await session.scalar(
        select(SizeGroup).where(SizeGroup.id == body.size_group_id).with_for_update()
    )
    if not group or group.status != "ACTIVE":
        raise HTTPException(422, "请选择有效尺码组")
    sizes = (
        await session.scalars(
            select(Size).where(Size.group_id == group.id, Size.status == "ACTIVE")
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
    values = body.model_dump(exclude={"color_ids", "skus"})
    product = Product(**values)
    session.add(product)
    try:
        await session.flush()
        session.add_all([SKU(product_id=product.id, **item) for item in sku_values])
        await commit_record(
            session, product, actor, {"code": product.code, "sku_count": len(sku_values)}, "CREATE"
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "款号或条码重复，请检查后重试") from None
    except Exception:
        await session.rollback()
        raise
    return await product_data(session, product)


async def update_product(session, actor, product, body):
    values = body.model_dump(exclude_unset=True)
    if "code" in values and values["code"] != product.code:
        raise HTTPException(409, "商品款号已经生成规格，不能修改")
    sku_prices = values.pop("sku_prices", None)
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
    await commit_record(session, product, actor, {**values, "sku_prices": sku_prices}, "UPDATE")
    return await product_data(session, product)
