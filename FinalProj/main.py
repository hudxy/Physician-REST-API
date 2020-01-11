from google.cloud import datastore
from flask import Flask, request, render_template, url_for, redirect, session
import json
import credentials
import doctors
import patients
import rooms
from requests_oauthlib import OAuth2Session
import random
import string
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
import uuid

app = Flask(__name__)
app.register_blueprint(doctors.bp)
app.register_blueprint(patients.bp)
app.register_blueprint(rooms.bp)

client = datastore.Client()

# This disables the requirement to use HTTPS so that you can test locally.
# import os
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

#current_url = "http://localhost:8080"
current_url = "https://hw9-final-deanh.appspot.com"
#OAuth API INFO
client_id = credentials.ClientID
client_secret = credentials.ClientSecret
#test state string
State = credentials.State
#Scope of OAuth REST request
Scope = credentials.Scope
#Redirect_uri
redirect_uri = current_url+"/oauth"
# These let us get basic info to identify a user and not much else
# they are part of the Google People API
scope = ['https://www.googleapis.com/auth/userinfo.email',
             'https://www.googleapis.com/auth/userinfo.profile', 'openid']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                          scope=scope)



# This link will redirect users to begin the OAuth flow with Google
@app.route('/')
def index():
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account")
    context = {}
    context["authorization_url"] = authorization_url
    return render_template('index.html', context=context)

# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@app.route('/oauth')
def oauthroute():
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token(
    token['id_token'], req, client_id)
    context = {}
    context["id"] = str(id_info['sub'])
    context["jwt"] = str(token['id_token'])

    return render_template("jwt.html", context=context)

# This page demonstrates verifying a JWT. id_info['email'] contains
# the user's email address and can be used to identify them
# this is the code that could prefix any API call that needs to be
# tied to a specific user by checking that the email in the verified
# JWT matches the email associated to the resource being accessed.
@app.route('/verify-jwt')
def verify():
    req = requests.Request()
    #begin verification of JWT
    try:
        id_info = id_token.verify_oauth2_token(
        request.args['jwt'], req, client_id)
        #check credentials of issuer
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        return repr(id_info) + "<br><br> the user is: " + id_info['email']
    except ValueError:
        return "Wrong token"
        pass





if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
