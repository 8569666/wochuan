from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


def record_audit(session: AsyncSession, actor_id: int, action: str,
                 entity_type: str, entity_id: int, changes: dict) -> None:
    session.add(AuditLog(actor_id=actor_id, action=action, entity_type=entity_type,
                         entity_id=entity_id, changes=jsonable_encoder(changes)))
