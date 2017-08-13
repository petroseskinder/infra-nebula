import os
from flask import Flask, jsonify, request, session
from flask_session import Session

from fabric.api import execute
from redis import Redis

import memoize.redis

from fabfile import read_remote_file

import firebase_admin
from firebase_admin import credentials, auth
from flask_wtf.csrf import CSRFProtect

import requests
from github import Github

gh = Github(os.getenv('GITHUB_ACCESS_TOKEN'))

cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), '.firebase-admin.json'))
firebase_app = firebase_admin.initialize_app(cred)

app = Flask(__name__)
# csrf = CSRFProtect(app)
SESSION_TYPE = 'redis'
app.config.from_object(__name__)
Session(app)

db = Redis()
store = memoize.redis.wrap(db)

memo = memoize.Memoizer(store)


# @app.after_request
# def set_x_csrf_cookie(response):
#     response.set_cookie('X-CSRF', csrf.generate_csrf())
#     print(csrf.generate_csrf())
#     return response

@memo
def get_gh_username_by_id(gh_id: str) -> str:
    return requests.get(f"https://api.github.com/user/{gh_id}").json()['login']


@memo(max_age=3600 * 30)
def is_token_authorized(gh_uid: str) -> bool:
    gh_login = get_gh_username_by_id(gh_uid)
    gh_user = gh.get_user(gh_login)
    return gh.get_organization('scc-gatech').has_in_members(gh_user)


@app.route('/auth', methods=['POST'])
def firebase_auth():
    id_token = request.json['auth_data']
    decoded_token = auth.verify_id_token(id_token)
    gh_uid = decoded_token['firebase']['identities']['github.com'][0]

    return jsonify({
        "authorized": is_token_authorized(gh_uid)
    })


@app.route('/')
def hello_world():
    host = 'ubuntu@ec2-52-91-74-197.compute-1.amazonaws.com'
    jsonify()
    return jsonify({
        "file_content": execute(read_remote_file, "/etc/hosts", host=host)
    })
