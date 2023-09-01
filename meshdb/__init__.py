import json
from typing import Dict, Tuple, Union

from flask import Flask, request
from flask.typing import ResponseReturnValue

from meshdb.auth import authenticate
from meshdb.db import queries

app = Flask(__name__)
app.json.sort_keys = False  # type: ignore


@app.route("/getMembers", methods=["GET"])
def apiGetMembers() -> ResponseReturnValue:
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, "see_members")
    except:
        return "Forbidden", 403
    if permission == True:
        return queries.getMembers()
    else:
        return "Forbidden", 403


@app.route("/getMemberByName", methods=["GET"])
def apiGetMemberByName() -> ResponseReturnValue:
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, "see_members")
    except:
        return "Forbidden", 403
    if permission == True:
        firstName = request.args.get("firstname")
        lastName = request.args.get("lastname")
        if not firstName or not lastName:
            return "firstname and lastname must be provided", 400
        result = queries.getMemberByName(firstName, lastName)
        if result == False:
            return "Member not found", 404
        else:
            return result
    else:
        return "Forbidden", 403


@app.route("/getMemberById/<id>", methods=["GET"])
def apiGetMemberById(id: str) -> ResponseReturnValue:
    try:
        return queries.getMemberByID(id)
    except:
        return "Member not found", 404


@app.route("/getMemberDetailsById/<id>", methods=["GET"])
def apiGetMemberDetailsByID(id: str) -> ResponseReturnValue:
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, "see_members")
    except:
        return "Forbidden", 403
    if permission == True:
        try:
            return queries.getMemberDetailsByID(id)
        except:
            return "Member not found", 404
    else:
        return "Forbidden", 403


@app.route("/addMember", methods=["POST"])
def apiAddMember() -> ResponseReturnValue:
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, "put")
    except:
        return "Forbidden", 403
    if permission == True:
        try:
            queries.createNewMember(request.get_json())
            return "OK", 200
        except:
            return "Error", 500
    else:
        return "Forbidden", 403
