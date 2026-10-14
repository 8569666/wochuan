from app.common.archives import archive_router
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierUpdate

router = archive_router("/suppliers", Supplier, SupplierCreate, SupplierUpdate)
