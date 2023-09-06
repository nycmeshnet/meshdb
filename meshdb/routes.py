from flask import current_app as app
from flask import request, Blueprint
from flask_security import auth_required

from .data import queries


def construct_blueprint(engine):
    route_blueprint = Blueprint("route_blueprint", __name__)

    @route_blueprint.route("/getMembers", methods=["GET"])
    @auth_required("token", "session")
    def apiGetMembers():
        return queries.getMembers(engine)

    @route_blueprint.route("/getMemberByName", methods=["GET"])
    def apiGetMemberByName():
        firstName = request.args.get("firstname")
        lastName = request.args.get("lastname")
        result = queries.getMemberByName(engine, firstName, lastName)
        return result

    @route_blueprint.route("/getMemberById/<id>", methods=["GET"])
    def apiGetMemberById(id):
        try:
            return queries.getMemberByID(engine, id)
        except:
            return "Member not found", 404

    @route_blueprint.route("/getMemberDetailsById/<id>", methods=["GET"])
    def apiGetMemberDetailsByID(id):
        try:
            return queries.getMemberDetailsByID(engine, id)
        except:
            return "Member not found", 404

    @route_blueprint.route("/addMember", methods=["POST"])
    def apiAddMember():
        try:
            queries.createNewMember(engine, request.get_json())
            return "OK", 200
        except:
            return "Error", 500

    return route_blueprint
