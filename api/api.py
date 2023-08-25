from flask import *
from api import queries
import json
from auth import authenticate


app = Flask(__name__)
app.json.sort_keys = False


@app.route("/getMembers", methods=["GET"])
def apiGetMembers():
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
def apiGetMemberByName():
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, "see_members")
    except:
        return "Forbidden", 403
    if permission == True:
        firstName = request.args.get("firstname")
        lastName = request.args.get("lastname")
        result = queries.getMemberByName(firstName, lastName)
        if result == False:
            return "Member not found", 404
        else:
            return result
    else:
        return "Forbidden", 403


@app.route("/getMemberById/<id>", methods=["GET"])
def apiGetMemberById(id):
    try:
        return queries.getMemberByID(id)
    except:
        return "Member not found", 404


@app.route("/getMemberDetailsById/<id>", methods=["GET"])
def apiGetMemberDetailsByID(id):
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
def apiAddMember():
    token = request.headers["token"]
    try:
        permission = authenticate.getRolePermission(token, 'put')
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