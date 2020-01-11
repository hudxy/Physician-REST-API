from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import patients
from requests_oauthlib import OAuth2Session
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

boats = "boats"
slips = "slips"
loads = "loads"
patients = "patients"
doctors = "doctors"
rooms = "rooms"


client = datastore.Client()

def getLoadsSelf(carrier, entityStr, req):
    if entityStr in carrier:
        if carrier[entityStr] is not None:
            carrier[entityStr]['self'] = str(req.url_root) + entityStr + "s/" + str(carrier[entityStr]['id'])
            #print(x)
    return

def removeOneEntityFromCarrier(carrier, entityStr, entityID):
    if entityStr in carrier.keys():
        if int(carrier[entityStr]['id']) == int(entityID):
            carrier[entityStr] = None
            return carrier
    return False

def pagination(kind, limit, offset):
    query = client.query(kind=kind)
    total_count = len(list(query.fetch()))
    q_limit = int(limit)
    q_offset = int(offset)
    l_iterator = query.fetch(limit=q_limit, offset=q_offset)
    pages = l_iterator.pages
    results = list(next(pages))
    if l_iterator.next_page_token:
        next_offset = q_offset + q_limit
        next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
    else:
        next_url = None
    for e in results:
        e["self"] = str(request.base_url) + "/" +  e["id"]
        if kind == patients:
            getLoadsSelf(e, 'room', request)
        elif kind == rooms:
            getLoadsSelf(e, 'patient', request)
        e["id"] = e.key.id
    output = {str(kind): results}
    output["total"] = total_count
    if next_url:
        output["next"] = next_url
    return json.dumps(output)

#making response function
def makeResponse(output, statusCode):
    res = make_response(json.dumps(output))
    res.mimetype = 'application/json'
    res.status_code = statusCode
    return res

def validJWT(headers):
    req = requests.Request()
    #begin verification of JWT
    if 'authorization' not in headers:
        return False
    else:
        #slice string to remove "Bearer " from authorization header field
        jwtToken = headers['Authorization'][7:]


    try:
        id_info = id_token.verify_oauth2_token(jwtToken, req, ClientID)
        #check credentials of issuer
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
    except ValueError:
        return False
    return id_info
