from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants
import patients
from requests_oauthlib import OAuth2Session
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

client = datastore.Client()

bp = Blueprint('doctors', __name__, url_prefix='/doctors')

#<id> is the doctor associated id
@bp.route('/<id>/patients', methods=['GET'])
def user_get_patients(id):
    if request.method == 'GET':
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)
        if int(id_info["sub"]) != int(id):
            return constants.makeResponse({"Error": "You do not have access to this collection"}, 403)
        query = client.query(kind=constants.patients)
        query.add_filter('physician_id', '=', str(id))
        results = list(query.fetch())
        for e in results:
            constants.getLoadsSelf(e, 'room', request)
            e["self"] = str(request.url_root) + "patients/" + e["id"]
        return constants.makeResponse(results, 200)

    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['GET']
        return res
