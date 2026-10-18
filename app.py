import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, redirect, request, url_for
from sqlalchemy import inspect
from werkzeug.middleware.proxy_fix import ProxyFix

from tracker.extensions import csrf, db, login_manager
from tracker.models import User
from tracker.views import tracker

BASE_DIR = Path(__file__).resolve().parent


def create_app(test_config=None):
    app = Flask(__name__)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://", "postgresql+psycopg://", 1
            )
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
    else:
        database_url = f"sqlite:///{(BASE_DIR / 'db.sqlite3').as_posix()}"

    debug = os.getenv("DEBUG", "false").lower() == "true"
    allowed_hosts = [
        host.strip()
        for host in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
        if host.strip()
    ]
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        DEBUG=debug,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        WTF_CSRF_TIME_LIMIT=3600,
        ADMIN_MOBILE=os.getenv("ADMIN_MOBILE", "7338884040"),
        TRUSTED_HOSTS=[
            f"*{host}" if host.startswith(".") else host for host in allowed_hosts
        ]
        or None,
    )
    if not debug:
        app.config.update(SESSION_COOKIE_SECURE=True, WTF_CSRF_SSL_STRICT=True)
    if test_config:
        app.config.update(test_config)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "tracker.login"

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Please sign in to continue."}), 401
        return redirect(url_for(login_manager.login_view))

    app.register_blueprint(tracker)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except ValueError:
            return None

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        if db.engine.dialect.name == "postgresql":
            columns = inspect(db.engine).get_columns("tracker_user")
            password_column = next(
                (column for column in columns if column["name"] == "password"),
                None,
            )
            if password_column is None:
                raise RuntimeError("The tracker_user.password column is missing.")
            if password_column["type"].length is not None:
                with db.engine.begin() as connection:
                    connection.exec_driver_sql(
                        "ALTER TABLE tracker_user "
                        "ALTER COLUMN password TYPE TEXT"
                    )
        print("Database tables are ready.")

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin():
        mobile = app.config["ADMIN_MOBILE"]
        user = db.session.scalar(db.select(User).where(User.mobile == mobile))
        created = user is None
        if created:
            user = User(username="Admin", mobile=mobile)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
        user.username = "Admin"
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        initial_password = os.getenv("ADMIN_INITIAL_PASSWORD")
        if initial_password:
            user.set_password(initial_password)
        db.session.commit()
        print(f"{'Created' if created else 'Updated'} admin account {mobile}")

    return app


app = create_app()
