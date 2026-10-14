from fastapi import HTTPException

from app.modules.organization.models import Store


async def validate_warehouse(session, values, existing):
    kind = values.get("type", existing.type if existing else "CENTRAL")
    store_id = values.get("store_id", existing.store_id if existing else None)
    if (kind == "STORE") != (store_id is not None):
        raise HTTPException(422, "店仓必须绑定门店，其他仓库不能绑定门店")
    if store_id:
        store = await session.get(Store, store_id)
        changed = not existing or store_id != existing.store_id
        if not store or (changed and store.status != "ACTIVE"):
            raise HTTPException(422, "请选择有效门店")
