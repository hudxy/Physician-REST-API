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

bp = Blueprint('rooms', __name__, url_prefix='/rooms')

roomCheck = {"number": "", "check_in": "", "wing": ""}
@bp.route('', methods=['POST', 'GET'])
def rooms_get_post():
    if request.method == 'POST':
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        content = request.get_json()
        if set(("number", "check_in", "wing")) != set(content):
            err = {"Error": "The request object is missing at least one of the required attributes"}
            return  constants.makeResponse(err, 400)

        new_room = datastore.entity.Entity(key=client.key(constants.rooms))


        new_room.update({"number": content["number"], "check_in": content["check_in"], "wing": content["wing"], "patient": None})
        client.put(new_room)
        room_key =  client.key(constants.rooms, new_room.key.id)
        room = client.get(key=room_key)
        room.update({"id": str(new_room.key.id)})
        client.put(room)
        room["self"] = str(request.base_url) + "/" +  str(new_room.key.id)
        return constants.makeResponse(room, 201)
    #Retrieve all rooms in DB
    elif request.method == 'GET':
        if 'application/json' in request.accept_mimetypes:
            return constants.pagination(constants.rooms, int(request.args.get('limit', '5')), int(request.args.get('offset', '0')))
        else:
            err = {"Error": "Accept mimetype must be 'application/json'."}
            return constants.makeResponse(err, 406)
    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['POST', 'GET']
        return res

@bp.route('/<id>', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def rooms_get_put_delete(id):
    if request.method == 'PATCH':
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        content = request.get_json()


        room_key =  client.key(constants.rooms, int(id))
        room = client.get(key=room_key)
        if not room:
            err = {"Error": "No room with this room_id exists"}
            return constants.makeResponse(err, 404)
        update = {}
        for attr in content:
            if attr not in roomCheck:
                err = {"Error": "The request object contains unrecognized attributes"}
                return  constants.makeResponse(err, 400)
            update[attr] = content[attr]
        room.update(update)
        client.put(room)
        room["self"] = str(request.base_url)
        constants.getLoadsSelf(room, 'patient', request)

        return constants.makeResponse(room, 200)
    elif request.method == 'PUT':
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        content = request.get_json()
        if set(("number", "check_in", "wing")) != set(content):
            err = {"Error": "The request object is missing at least one of the required attributes"}
            return  constants.makeResponse(err, 400)

        room_key =  client.key(constants.rooms, int(id))
        room = client.get(key=room_key)
        if not room:
            err = {"Error": "No room with this room_id exists"}
            return constants.makeResponse(err, 404)

        room.update({"number": content["number"], "check_in": content["check_in"], "wing": content["wing"]})
        client.put(room)
        room["self"] = str(request.base_url)
        constants.getLoadsSelf(room, 'patient', request)
        return constants.makeResponse(room, 200)

    elif request.method == 'DELETE':
        room_key = client.key(constants.rooms, int(id))
        room = client.get(key=room_key)
        if not room:
            err = {"Error": "No room with this room_id exists"}
            return constants.makeResponse(err, 404)
        #Remove rooms from patients when deleting room
        query = client.query(kind=constants.patients)
        results = list(query.fetch())
        for e in results:
            if e["room"] is not None:
                if int(e["room"]["id"]) == int(room["id"]):
                    patient_key = client.key(constants.patients, int(e["id"]))
                    patient = client.get(key=patient_key)
                    patient.update({"room": None})
                    client.put(patient)
        client.delete(room_key)
        return constants.makeResponse('', 204)
    elif request.method == 'GET':
        if 'application/json' not in request.accept_mimetypes and 'text/html' not in request.accept_mimetypes:
            err = {"Error": "The accept-header Content-Type must be application/json or text/html"}
            return constants.makeResponse(err, 406)
        room_key = client.key(constants.rooms, int(id))
        room = client.get(key=room_key)
        if not room:
            err = {"Error": "No room with this room_id exists"}
            return constants.makeResponse(err, 404)
        room["self"] = str(request.base_url)
        constants.getLoadsSelf(room, 'patient', request)
        if 'application/json' in request.accept_mimetypes:
            return constants.makeResponse(room, 200)

    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['GET', 'DELETE', 'PATCH', 'PUT']
        return res
