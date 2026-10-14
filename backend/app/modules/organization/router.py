from fastapi import APIRouter

from app.common.archives import archive_router
from app.modules.organization.models import Store, Warehouse
from app.modules.organization.schemas import (
    StoreCreate,
    StoreUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)
from app.modules.organization.service import validate_warehouse

router = APIRouter()
router.include_router(archive_router("/stores", Store, StoreCreate, StoreUpdate))
router.include_router(
    archive_router("/warehouses", Warehouse, WarehouseCreate, WarehouseUpdate, validate_warehouse)
)
