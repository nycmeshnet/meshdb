"""App factrory file"""
import os

from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore, hash_password

from .db.database import db


def create_app():
    """App factory"""
    app = Flask(__name__)
    app.json.sort_keys = False

    # set settings for flask-security, authentication DB
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["SECURITY_PASSWORD_SALT"] = os.environ.get("SECURITY_PASSWORD_SALT")
    app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
    app.config["SESSION_COOKIE_SAMESITE"] = "strict"
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://{}:{}@{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_AUTH_NAME"),
    )

    # csrf breaks token auth, need to investigate further
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
    app.config["WTF_CSRF_ENABLED"] = False

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

    db.init_app(app)

    return app
