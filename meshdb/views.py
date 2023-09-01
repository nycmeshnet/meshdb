from flask import current_app as app
from flask import request
from flask_security import auth_required

from .db import queries


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
