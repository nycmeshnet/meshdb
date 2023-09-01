import json
from flask import *
from meshdb.db import queries
from flask_security import (
    Security,
    SQLAlchemyUserDatastore,
    auth_required,
    hash_password,
)
from flask_security.models import fsqla_v3 as fsqla
import os
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey
from sqlalchemy.ext.mutable import MutableList
from flask_security import UserMixin, RoleMixin, AsaList
from sqlalchemy.orm import relationship, backref

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

# csrf breaks token auth auth, need to investigate further
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["WTF_CSRF_ENABLED"] = False

db = SQLAlchemy(app)

# import authmodels after db has been declared
import meshdb.auth.authmodels as authmodels

user_datastore = SQLAlchemyUserDatastore(db, authmodels.User, authmodels.Role)
app.security = Security(app, user_datastore)

# test code to create user
with app.app_context():
    db.create_all()
    db.metadata.create_all
    if not app.security.datastore.find_user(email="example@nycmesh.net"):
        app.security.datastore.create_user(email="example@nycmesh.net", password=hash_password("abcd1234"))
    db.session.commit()


@app.route("/getMembers", methods=["GET"])
@auth_required("token", "session")
def apiGetMembers():
    return queries.getMembers()


@app.route("/getMemberByName", methods=["GET"])
def apiGetMemberByName():
    firstName = request.args.get("firstname")
    lastName = request.args.get("lastname")
    result = queries.getMemberByName(firstName, lastName)
    return result


@app.route("/getMemberById/<id>", methods=["GET"])
def apiGetMemberById(id):
    try:
        return queries.getMemberByID(id)
    except:
        return "Member not found", 404


@app.route("/getMemberDetailsById/<id>", methods=["GET"])
def apiGetMemberDetailsByID(id):
    try:
        return queries.getMemberDetailsByID(id)
    except:
        return "Member not found", 404


@app.route("/addMember", methods=["POST"])
def apiAddMember():
    try:
        queries.createNewMember(request.get_json())
        return "OK", 200
    except:
        return "Error", 500
