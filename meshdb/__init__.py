"""App factrory file"""
import os

from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore, hash_password

from .data.database import db

from dotenv import load_dotenv


def create_app():
    """App factory"""
    load_dotenv()
    app = Flask(__name__)
    app.json.sort_keys = False

    # Network I sure hope it does
    app.config["IP"] = os.getenv("IP")
    app.config["PORT"] = os.getenv("PORT")

    # set settings for flask-security, authentication DB
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["SECURITY_PASSWORD_SALT"] = os.environ.get("SECURITY_PASSWORD_SALT")
    app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
    app.config["SESSION_COOKIE_SAMESITE"] = "strict"
    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

    # csrf breaks token auth, need to investigate further
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    # Configure Database
    from meshdb.data.setup import initialize_db

    initialize_db()

    db.init_app(app)

    import meshdb.auth.authmodels as authmodels

    user_datastore = SQLAlchemyUserDatastore(db, authmodels.User, authmodels.Role)
    app.security = Security(app, user_datastore)

    # test code to create user
    with app.app_context():
        db.create_all()
        if not app.security.datastore.find_user(email="example@nycmesh.net"):
            app.security.datastore.create_user(email="example@nycmesh.net", password=hash_password("abcd1234"))
        db.session.commit()

    # Register API routes
    from .routes import route_blueprint

    app.register_blueprint(route_blueprint)

    return app
