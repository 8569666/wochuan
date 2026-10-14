import argparse
import getpass
import re
import secrets
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.core.migrations import upgrade_database
from app.models import register_models
from app.modules.auth.models import User
from app.modules.auth.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="沃川后台管理命令")
    parser.add_argument("command", choices=["migrate", "init-admin", "bootstrap-local", "check-db"])
    args = parser.parse_args()
    settings = get_settings()
    register_models()
    if args.command == "migrate":
        upgrade_database(settings)
        print("项目迁移已完成")
        return
    engine = create_engine(settings.database_url.set(drivername="mysql+pymysql"))
    if args.command == "check-db":
        with engine.connect() as connection:
            print("数据库可用，MySQL", connection.scalar(text("SELECT VERSION()")))
        engine.dispose()
        return
    with Session(engine) as session:
        username = "admin" if args.command == "bootstrap-local" else input("管理员用户名: ").strip().lower()
        if not re.fullmatch(r"[a-z0-9_.-]{3,64}", username):
            raise SystemExit("用户名需为3-64位字母、数字或_.-")
        if session.scalar(select(User).where(User.username == username)):
            print("账号已存在，未覆盖密码")
            return
        if args.command == "bootstrap-local":
            password = secrets.token_urlsafe(24)
        else:
            password = getpass.getpass("管理员密码（至少12位）: ")
            if len(password) < 12 or password != getpass.getpass("再次输入密码: "):
                raise SystemExit("密码长度不足或两次输入不一致")
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()
        if args.command == "bootstrap-local":
            target = PROJECT_ROOT / ".cache" / "initial-admin.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"用户名: {username}\n密码: {password}\n", encoding="utf-8")
            print("本地管理员已创建。凭据保存到 .cache/initial-admin.txt（Git忽略）")
        else:
            print("管理员已创建")
    engine.dispose()


if __name__ == "__main__":
    main()
