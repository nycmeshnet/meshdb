from flask import *
from api import queries
import json
from auth import authenticate



app = Flask(__name__)
app.json.sort_keys = False



@app.route('/getMembers', methods=['GET'])
def apiGetMembers():
    return (queries.getMembers())

@app.route('/getMemberById/<id>', methods=['GET'])
def apiGetMemberById(id):
    try:
        return queries.getMemberByID(id)
    except:
        return "Member does not exist", 404
