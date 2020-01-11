from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants
import doctors
import rooms
from requests_oauthlib import OAuth2Session
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

client = datastore.Client()

bp = Blueprint('patients', __name__, url_prefix='/patients')

def populatePatient(content):
    #template to handle empty fields
    data = {"first_name": "", "last_name": "", "gender": "", "phone": "",
     "email_address": "", "address": "", "visit_date": "", "diagnosis": ""}

    #populate entries from request
    for fields in content:
        if fields not in data:
            return False
        data[fields] = content[fields]
    data['room'] = None
    return data

def patientInputVal(content):
    if "first_name" not in content or "last_name" not in content:
        err = {"Error": "The request object is missing one of the required attributes"}
        return err
    return content

#Route to handle retrieve all patients and to add a patient
@bp.route('', methods=['POST', 'GET', 'PUT', 'PATCH', 'DELETE'])
def patient_get_post():
    #check if user is adding a patient
    if request.method == 'POST':
        #check if JWT is valid
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)
        #ensure request is json format
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        content = request.get_json()
        #error checks of input
        content = patientInputVal(content)
        if "Error" in content:
            return constants.makeResponse(content, 400)

        #retrive request data
        content = populatePatient(content)
        if not content:
            err = {"Error": "The request object has unacceptable attributes"}
            return constants.makeResponse(err, 400)
        #set patients physician to current doctors(user) sub number
        content["physician_id"] = id_info["sub"]
        new_patient = datastore.entity.Entity(key=client.key(constants.patients))
        new_patient.update(content)
        client.put(new_patient)
        patient_key =  client.key(constants.patients, new_patient.key.id)
        patient = client.get(key=patient_key)
        patient.update({"id": str(new_patient.key.id)})
        client.put(patient)
        patient["self"] = str(request.base_url) + "/" +  str(new_patient.key.id)
        return constants.makeResponse(patient, 201)
    #Retrieve all patients in DB
    elif request.method == 'GET':
        if 'application/json' in request.accept_mimetypes:
            return constants.pagination(constants.patients, int(request.args.get('limit', '5')), int(request.args.get('offset', '0')))
        else:
            err = {"Error": "Accept mimetype must be 'application/json'."}
            return constants.makeResponse(err, 406)

    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['GET', 'POST']
        return res

#Route to handle retrieve, update, or delete a specific patient
@bp.route('/<id>', methods=['PATCH', 'PUT', 'GET', 'DELETE'])
def patient_get_update_delete(id):
    #retrieve specific patient
    if request.method == 'GET':
        #check if JWT is valid
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)

        patient_key = client.key(constants.patients, int(id))
        patient = client.get(key=patient_key)
        if not patient:
            err = {"Error": "No patient with this patient_id exists"}
            return constants.makeResponse(err, 404)

        if patient["physician_id"] != id_info["sub"]:
            return constants.makeResponse({"Error": "You do not have access to this patient"}, 403)
        patient["self"] = str(request.base_url)
        constants.getLoadsSelf(patient, 'room', request)
        if 'application/json' in request.accept_mimetypes:
            return constants.makeResponse(patient, 200)
        else:
            err = {"Error": "Accept mimetype must be 'application/json'."}
            return constants.makeResponse(err, 406)

    elif request.method == 'PUT':
        #ensure request is json format
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        #check if JWT is valid
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)

        #retrive request data
        content = request.get_json()
        content = patientInputVal(content)
        if "Error" in content:
            return constants.makeResponse(content, 400)

        content = populatePatient(request.get_json())
        if not content:
            err = {"Error": "The request object has unacceptable attributes"}
            return constants.makeResponse(err, 400)
        patient_key = client.key(constants.patients, int(id))
        patient = client.get(key=patient_key)
        if not patient:
            err = {"Error": "No patient with this patient_id exists"}
            return constants.makeResponse(err, 404)
        if patient["physician_id"] != id_info["sub"]:
            return constants.makeResponse({"Error": "You do not have access to this patient"}, 403)

        patient.update(content)
        client.put(patient)
        patient["self"] = str(request.base_url)
        constants.getLoadsSelf(patient, 'room', request)
        if 'application/json' in request.accept_mimetypes:
            return constants.makeResponse(patient, 200)
        else:
            err = {"Error": "Accept mimetype must be 'application/json'."}
            return constants.makeResponse(err, 406)

    elif request.method == 'PATCH':
        #ensure request is json format
        if not request.is_json:
            err = {"Error": "The request Content-Type must be JSON"}
            return constants.makeResponse(err, 415)
        #check if JWT is valid
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)

        #retrive request data
        content = request.get_json()
        #check body of request

        #Update patient info (Keeps old patient info if fields aren't specified in request)
        patient_key = client.key(constants.patients, int(id))
        patient = client.get(key=patient_key)
        if not patient:
            err = {"Error": "No patient with this patient_id exists"}
            return constants.makeResponse(err, 404)
        if patient["physician_id"] != id_info["sub"]:
            return constants.makeResponse({"Error": "You do not have access to this patient"}, 403)

        for fields in content:
            if fields not in patient:
                err = {"Error": "The request object has unacceptable attributes"}
                return constants.makeResponse(err, 400)
            patient[fields] = content[fields]

        patient.update(content)
        client.put(patient)
        patient["self"] = str(request.base_url)
        constants.getLoadsSelf(patient, 'room', request)
        if 'application/json' in request.accept_mimetypes:
            return constants.makeResponse(patient, 200)
        else:
            err = {"Error": "Accept mimetype must be 'application/json'."}
            return constants.makeResponse(err, 406)

    elif request.method == 'DELETE':
        #check if JWT is valid
        id_info = constants.validJWT(request.headers)
        if id_info == False:
            return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)

        patient_key = client.key(constants.patients, int(id))
        patient = client.get(key=patient_key)
        if not patient:
            err = {"Error": "No patient with this patient_id exists"}
            return constants.makeResponse(err, 404)
        if patient["physician_id"] != id_info["sub"]:
            return constants.makeResponse({"Error": "You do not have access to this patient"}, 403)
        #Remove rooms when deleting patients
        query = client.query(kind=constants.rooms)
        results = list(query.fetch())
        for e in results:
            if e['patient'] is not None:
                if int(e['patient']['id']) == int(patient["id"]):
                    room_key = client.key(constants.rooms, int(e["id"]))
                    room = client.get(key=room_key)
                    room.update({"patient": None})
                    client.put(room)
        client.delete(patient_key)
        return constants.makeResponse('', 204)

    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['GET', 'PATCH', 'PUT', 'DELETE']
        return res

@bp.route('/<pid>/rooms/<rid>', methods=['PUT', 'DELETE'])
def patients_rooms(pid, rid):
    #check if JWT is valid
    id_info = constants.validJWT(request.headers)
    if id_info == False:
        return constants.makeResponse({"Error": "Invalid or Missing JWT"}, 401)

    patient_key = client.key(constants.patients, int(pid))
    patient = client.get(key=patient_key)
    room_key = client.key(constants.rooms, int(rid))
    room = client.get(key=room_key)
    if not patient or not room:
         err = {"Error": "No patient with this patient_id exists or No room with this room_id exists"}
         return constants.makeResponse(err, 404)

    if patient["physician_id"] != id_info["sub"]:
        return constants.makeResponse({"Error": "You do not have access to this patient"}, 403)

    if request.method == 'PUT':
        if room['patient'] is not None:
            err = {"Error": "The room already has a patient"}
            return constants.makeResponse(err, 403)
        elif patient['room'] is not None:
            err = {"Error": "The patient is already assigned a room"}
            return constants.makeResponse(err, 403)
        #Add room_id to patient["room"]
        patient['room'] = {"id": room.id}

        #Add patient_id to room["patient"]
        if 'patient' in room.keys():
            room.update({"patient": {"id": patient.id, "last_name": patient['last_name']} })
        client.put(patient)
        client.put(room)
        return('', 204)
    elif request.method == 'DELETE':
        if room['patient'] is None:
            err = {"Not Modified": "The room does not currently have a patient"}
            return constants.makeResponse(err, 304)
        elif patient['room'] is None:
            err = {"Not Modified": "The patient is not currently assigned a room"}
            return constants.makeResponse(err, 304)
        constants.removeOneEntityFromCarrier(patient, 'room', room.id)
        constants.removeOneEntityFromCarrier(room, 'patient', patient.id)

        client.put(patient)
        client.put(room)
        return('', 204)
    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['PUT', 'DELETE']
        return res

@bp.route('/<pid>/rooms', methods=['GET'])
def patient_room_get(pid):
    if request.method == 'GET':
        patient_key = client.key(constants.patients, int(pid))
        patient = client.get(key=patient_key)
        if not patient:
             err = {"Error": "No patient with this patient_id exists"}
             return constants.makeResponse(err, 404)
        query = client.query(kind=constants.rooms)
        results = list(query.fetch())
        roomList = []
        for e in results:
            if e['patient'] is not None:
                if e['patient']['id'] == int(patient.id):
                    constants.getLoadsSelf(e, 'patient', request)
                    e['self'] = str(request.url_root) + 'rooms/' + str(e['id'])
                    roomList.append(e)
        return constants.makeResponse(roomList, 200)
    else:
        err = {"Error": "The request method is not recognized"}
        res = constants.makeResponse(err, 405)
        res.headers['Allows'] = ['GET']
        return res
