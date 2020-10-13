from flask import Flask, render_template, make_response, redirect, url_for, request, session, jsonify

import random
import requests
from pymongo import MongoClient
from urllib.parse import urlencode
from config import DefaultConfig
from datetime import datetime, timedelta

CONFIG = DefaultConfig()

client = MongoClient(host=CONFIG.DB_URL, port=CONFIG.DB_PORT, username=CONFIG.DB_USERNAME, password=CONFIG.DB_PASSWORD, authSource=CONFIG.DB_COL)
col_playlist = client.bot['playlist']
col_token = client.bot['token']

app = Flask(__name__)

app.secret_key = b'2aa45112fa0e4d38befc0cbde25006e1'
client_id = 'ca83153c363a4fbc8fc683647b84831d'
client_secret = '2aa45112fa0e4d38befc0cbde25006e1'
redirect_uri = 'https://1a59d5ef6cbe.ngrok.io/callback'

letters = 'abcdefghijklmnopqrstuvwxyz0123456789'
stateKey = 'spotify_auth_state'
import base64

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    # state = ''.join(random.choice(letters) for i in range(16))
    scope = 'user-read-private user-read-email playlist-read-collaborative playlist-modify-public'

    # print('st',state)
    query_str = {
        'response_type':'code',
        'client_id':client_id,
        'scope':scope,
        'redirect_uri':redirect_uri,
        # 'state':state
    }
    query_str = urlencode(query_str)

    response = make_response(redirect('https://accounts.spotify.com/authorize?'+query_str))
    # response.set_cookie(stateKey, state)
    # session[stateKey] = state

    return response


@app.route('/callback')
def callback():
    code = request.args.get('code', default=None)
    # state = request.args.get('state', default=None)
    # storedState = session[stateKey]
    # print(storedState)
    # if state == None or state != storedState:
    #     response = make_response(redirect(url_for('#', error='state_mismatch')))
    #     return response
    # else:
    # session.pop(stateKey, None)
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
        # print(r.json())
        headers = {
            'Authorization': 'Bearer ' + r.json()['access_token']
        }
        rme = requests.get('https://api.spotify.com/v1/me', headers=headers)
        user = rme.json()

        r2 = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)
        playlists = r2.json()['items']
        for playlist in playlists:
            track_list = get_tracks(playlist["id"], headers)
            track_list = get_track_features(track_list, headers)

            playlist_item = {
                '_id': playlist["id"],
                'name': playlist["name"],
                'owner': {
                    'id': user['id'],
                    'display_name': user['display_name'],
                    'email': user['email'],
                    'images': user['images']
                },
                'images': playlist['images'],
                'tracks': list(track_list.values())
            }

            if col_playlist.find_one({ "_id": playlist["id"] }):
                col_playlist.update_one({ "_id": playlist["id"] }, {'$set':playlist_item})
            else:   
                col_playlist.insert_one(playlist_item)

        return jsonify(r2.json())


@app.route('/add_playlist')
def add_playlist():
    playlist_id = request.args.get('playlist_id', default=None)
    now = datetime.now()
    token = col_token.find_one({"_id": "service"})
    if token and token['expire_time'] <= now:
        access_token = token['access_token']
    else:
        form = {
            'grant_type': 'client_credentials'
        }
        auth_str = f'{client_id}:{client_secret}'
        headers = {
            'Authorization': 'Basic '+str(base64.b64encode(bytes(auth_str,'utf-8')), "utf-8")
        }
        r = requests.post('https://accounts.spotify.com/api/token', data=form, headers=headers)
        if r.status_code == 200:
            access_token = r.json()['access_token']
            col_token.update_one({'_id': 'service'}, {'$set': {'access_token': access_token, 'expire_time': now + timedelta(hours=1)}})

    rplaylist = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)
    playlist = rplaylist.json()
    track_list = get_tracks(playlist["id"], headers)
    track_list = get_track_features(track_list, headers)

    playlist_item = {
        '_id': playlist["id"],
        'name': playlist["name"],
        'owner': "service",
        'images': playlist['images'],
        'tracks': list(track_list.values()),
        'for_train': True
    }

    if col_playlist.find_one({ "_id": playlist["id"] }):
        del playlist_item['owner']
        col_playlist.update_one({ "_id": playlist["id"] }, {'$set':playlist_item})
    else:   
        col_playlist.insert_one(playlist_item)

def get_tracks(playlist_id, headers, next_url=None, track_list={}):
    print('get_track',next_url)
    if next_url:
        rtracks = requests.get(next_url, headers=headers)
    else:
        rtracks = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers)
        
    tracks = rtracks.json()
    for track in tracks['items']:
        track_list[track['track']['id']] = {
            'id': track['track']['id'],
            'name': track['track']['name'],
            'duration_ms': track['track']['duration_ms'],
            'popularity': track['track']['popularity'],
            'explicit': track['track']['explicit'],
            'artist': track['track']['artists'][0]['name']
        }

    if tracks['next']:
        return get_tracks(playlist_id, headers, next_url=tracks['next'], track_list=track_list)
    else:
        return track_list


def get_track_features(track_list, headers, iter_index=0):
    print('get track feature',iter_index)
    id_list = list(track_list.keys())
    start_index = iter_index*100
    end_index = (iter_index+1)*100 if (iter_index+1)*100 < len(id_list) else len(id_list)
    req_id_list = id_list[start_index:end_index]

    rfeatures = requests.get(f'https://api.spotify.com/v1/audio-features/?ids={",".join(req_id_list)}', headers=headers)
    features = rfeatures.json()

    for feature in features['audio_features']:
        track_list[feature['id']]['danceability'] = feature['danceability']
        track_list[feature['id']]['energy'] = feature['energy']
        track_list[feature['id']]['key'] = feature['key']
        track_list[feature['id']]['loudness'] = feature['loudness']
        track_list[feature['id']]['mode'] = feature['mode']
        track_list[feature['id']]['speechiness'] = feature['speechiness']
        track_list[feature['id']]['acousticness'] = feature['acousticness']
        track_list[feature['id']]['instrumentalness'] = feature['instrumentalness']
        track_list[feature['id']]['liveness'] = feature['liveness']
        track_list[feature['id']]['valence'] = feature['valence']
        track_list[feature['id']]['tempo'] = feature['tempo']
        track_list[feature['id']]['time_signature'] = feature['time_signature']

    if end_index != len(id_list):
        iter_index += 1
        return get_track_features(track_list, headers, iter_index=iter_index)
    else:
        return track_list


if __name__ == '__main__':
   app.run(host='127.0.0.1', port=8888)