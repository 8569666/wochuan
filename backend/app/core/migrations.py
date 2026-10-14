from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import Settings
from app.models import register_models


def upgrade_database(settings: Settings) -> None:
    register_models()
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "alembic"))
    config.attributes["settings"] = settings
    command.upgrade(config, "head")
