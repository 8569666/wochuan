from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.common.responses import payload
from app.modules.access.service import AccessDep, require_permission
from app.modules.audit.service import record_audit
from app.modules.auth.service import SessionDep


def record_data(record):
    result = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if isinstance(value, Decimal):
            value = format(value, ".2f")
        elif isinstance(value, datetime):
            value = value.isoformat() + "Z"
        result[column.name] = value
    return result


async def find_record(session, model, record_id):
    record = await session.get(model, record_id)
    if record is None:
        raise HTTPException(404, "档案不存在")
    return record


async def commit_record(session, record, user, changes, action):
    try:
        await session.flush()
        record_audit(session, user.id, action, record.__tablename__, record.id, changes)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "编码、条码或关联关系重复，请检查后重试") from None


async def list_records(session, model, keyword, status, page, page_size, extra_filter=None):
    filters = []
    if keyword:
        filters.append(
            or_(
                model.code.contains(keyword, autoescape=True),
                model.name.contains(keyword, autoescape=True),
            )
        )
    if status:
        filters.append(model.status == status)
    if extra_filter is not None:
        filters.append(extra_filter)
    total = await session.scalar(select(func.count()).select_from(model).where(*filters))
    records = (
        await session.scalars(
            select(model)
            .where(*filters)
            .order_by(model.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [record_data(record) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def archive_router(
    path, model, create_schema, update_schema, validator=None, permission=None, scope=None
):
    router = APIRouter(prefix=path, tags=[path.strip("/")])
    permission = permission or {
        "/stores": "store",
        "/warehouses": "warehouse",
        "/suppliers": "supplier",
    }.get(path, "catalog")
    scope = scope or {"/stores": "store", "/warehouses": "warehouse"}.get(path)

    def read_filter(access):
        require_permission(access, f"{permission}.read")
        ids = getattr(access, f"{scope}_ids")(f"{permission}.read") if scope else None
        return model.id.in_(ids) if ids is not None else None

    def check_detail(access, record_id, write=False):
        require_permission(
            access, f"{permission}.{'write' if write else 'read'}", global_scope=write and not scope
        )
        if scope:
            ids = getattr(access, f"{scope}_ids")(f"{permission}.{'write' if write else 'read'}")
            if ids is not None and record_id not in ids:
                raise HTTPException(404, "档案不存在")

    @router.get("")
    async def listing(
        session: SessionDep,
        user: AccessDep,
        keyword: str = "",
        status: Literal["ACTIVE", "INACTIVE"] | None = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ):
        return payload(
            await list_records(session, model, keyword, status, page, page_size, read_filter(user))
        )

    @router.get("/{record_id}")
    async def detail(record_id: int, session: SessionDep, user: AccessDep):
        check_detail(user, record_id)
        return payload(record_data(await find_record(session, model, record_id)))

    async def create_item(body: dict, session: SessionDep, user: AccessDep):
        require_permission(user, f"{permission}.write", global_scope=True)
        values = body.model_dump()
        if validator:
            await validator(session, values, None)
        record = model(**values)
        session.add(record)
        await commit_record(session, record, user, values, "CREATE")
        return payload(record_data(record), code=201)

    async def update_item(record_id: int, body: dict, session: SessionDep, user: AccessDep):
        check_detail(user, record_id, write=True)
        record = await find_record(session, model, record_id)
        values = body.model_dump(exclude_unset=True)
        for key, value in values.items():
            if value is None and not model.__table__.columns[key].nullable:
                raise HTTPException(422, "必填字段不能为空")
        if validator:
            await validator(session, values, record)
        for key, value in values.items():
            setattr(record, key, value)
        await commit_record(session, record, user, values, "UPDATE")
        return payload(record_data(record))

    create_item.__annotations__["body"] = create_schema
    update_item.__annotations__["body"] = update_schema
    router.add_api_route("", create_item, methods=["POST"], status_code=201)
    router.add_api_route("/{record_id}", update_item, methods=["PATCH"])
    return router
