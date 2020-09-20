from flask import Flask, render_template, make_response, redirect, url_for, request, session
import random
import requests
from urllib.parse import urlencode

app = Flask(__name__)

app.secret_key = b'2aa45112fa0e4d38befc0cbde25006e1'
client_id = 'ca83153c363a4fbc8fc683647b84831d'
client_secret = '2aa45112fa0e4d38befc0cbde25006e1'
redirect_uri = 'https://a8eda52b4f24.ngrok.io/callback'

letters = 'abcdefghijklmnopqrstuvwxyz0123456789'
stateKey = 'spotify_auth_state'
import base64

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    state = ''.join(random.choice(letters) for i in range(16))
    scope = 'user-read-private user-read-email playlist-read-collaborative playlist-modify-public'

    print('st',state)
    query_str = {
        'response_type':'code',
        'client_id':client_id,
        'scope':scope,
        'redirect_uri':redirect_uri,
        'state':state
    }
    query_str = urlencode(query_str)

    response = make_response(redirect('https://accounts.spotify.com/authorize?'+query_str))
    # response.set_cookie(stateKey, state)
    session[stateKey] = state

    return response


@app.route('/callback')
def callback():
    code = request.args.get('code', default=None)
    state = request.args.get('state', default=None)
    storedState = session[stateKey]
    if state == None or state != storedState:
        response = make_response(redirect(url_for('#', error='state_mismatch')))
        return response
    else:
        session.pop(stateKey, None)
        form = {
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        auth_str = f'{client_id}:{client_secret}'
        headers = {
            'Authorization': 'Basic '+str(base64.b64encode(bytes(auth_str,'utf-8')), "utf-8")
        }
        r = requests.post('https://accounts.spotify.com/api/token', data=form, headers=headers)
        
        if r.status_code == 200:
            print(r.json())
            headers = {
                'Authorization': 'Bearer ' + r.json()['access_token']
            }
            r2 = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)
            print(r2.json())



if __name__ == '__main__':
   app.run(host='127.0.0.1', port=8888)