from flask import Flask, render_template, make_response, redirect, url_for, request, session, jsonify

import random
import requests
import time
from pymongo import MongoClient
from urllib.parse import urlencode
from config import DefaultConfig
from datetime import datetime, timedelta
from flask_cors import CORS

CONFIG = DefaultConfig()

# client = MongoClient(host=CONFIG.DB_URL, port=CONFIG.DB_PORT, username=CONFIG.DB_USERNAME, password=CONFIG.DB_PASSWORD, authSource=CONFIG.DB_COL)
client = MongoClient("mongodb+srv://teehim-usr:mongoDB@cluster0.driro.mongodb.net/teehim?retryWrites=true&w=majority")
col_playlist = client.playlist['playlist']
col_token = client.playlist['token']
col_track = client.playlist['track']

app = Flask(__name__)
CORS(app)

app.secret_key = b'2aa45112fa0e4d38befc0cbde25006e1'
client_id = 'ca83153c363a4fbc8fc683647b84831d'
client_secret = '2aa45112fa0e4d38befc0cbde25006e1'
redirect_uri = 'https://3afea1c4ecb8.ngrok.io/callback'

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
    print(query_str)

    response = make_response(redirect('https://accounts.spotify.com/authorize?'+query_str))
    # response.set_cookie(stateKey, state)
    # session[stateKey] = state

    return response


@app.route('/create_playlist')
def create_playlist():
    # access_token = get_service_token()
    headers = {
        'Authorization': 'Bearer ' + 'BQC5jji4F0NmGb109bmhfAXZ8O7qR0u5BVz3_huawvti_Y4wQ1p_PQ5Q4zG0jtXuF0oN3tPkfrA8DGz4lL1hH-56Ih7SvvLa7F1FGGhrfefg7FeCnUBv22ScYe60lINu7GKnHV-M8JdUvV-i6Rrd_qR9bnLtFDUEMBIHiugi31RTSYjah4D4hDrPCnHt1GZCnLZ2Ms97ijs4I-j4EDWVYA'
    }
    track_ids = ['spotify:track:2LeLsYwDTlfvWfqgIbxvgG',
       'spotify:track:0PACdf6vCQee3ICq02EWlf',
       'spotify:track:5qcwzdhDQjHjmu12gOLjY0',
       'spotify:track:3p7byaSR5J1he8vvDkxirp',
       'spotify:track:0AqMAXSzkIRMV0alAddJK8',
       'spotify:track:3TmMHzw7592o4bwtrSHeYv',
       'spotify:track:4J3eFXXi2nQqF6MWLprnbR',
       'spotify:track:2Fxmhks0bxGSBdJ92vM42m',
       'spotify:track:6IRdLKIyS4p7XNiP8r6rsx',
       'spotify:track:3Tc57t9l2O8FwQZtQOvPXK',
       'spotify:track:218AUAkMEZWsVwjPxs80OI',
       'spotify:track:2mosyIQjuejKlqSsdoI6q4',
       'spotify:track:2ylVfK4pVfeSV4zxieyT2B',
       'spotify:track:1ZI0AGxSFv2bW3STGNDhB7',
       'spotify:track:19QNA6AoLPJvKcf4Oosg2z',
       'spotify:track:2gmdr7WU3kSGRsDxv4tOqA',
       'spotify:track:7vA7BaPdYpdJtt8zVJaqy8',
       'spotify:track:58mtgcQVZ56NgWHKsN94nD']

    track_uris = ','.join(track_ids)
    playlist_data = {
        "name": "Bot Gen"
    }
    res_pl = requests.post(f'https://api.spotify.com/v1/users/21nrpmngofpue4bu35v3b7moq/playlists', json=playlist_data, headers=headers)
    pl_id = res_pl.json()['id']
    print(pl_id)
    print(track_uris)
    track_data = {
        "uris": track_ids
    }
    res_tr = requests.post(f'https://api.spotify.com/v1/playlists/{pl_id}/tracks', json=track_data, headers=headers)
    print(res_tr.json())
    return jsonify(res_tr.json())


@app.route('/add_playlist')
def add_playlist():
    playlist_id = request.args.get('playlist_id', default=None)
    access_token = get_service_token()
    headers = {
        'Authorization': 'Bearer ' + access_token
    }
    rplaylist = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)
    playlist = rplaylist.json()
    track_list = get_tracks(playlist["id"], headers, track_list={})
    track_list = get_track_data(track_list, headers)
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

    return 'success'


@app.route('/add_playlist_w_cat', methods=['POST'])
def add_playlist_w_cat():
    playlist_id = request.json['playlist_id']
    
    update_data = {}
    if 'season' in request.json.keys():
        update_data['season'] = request.json['season']

    if 'emotion' in request.json.keys():
        update_data['emotion'] = request.json['emotion']

    access_token = get_service_token()
    headers = {
        'Authorization': 'Bearer ' + access_token
    }
    rplaylist = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)
    playlist = rplaylist.json()
    track_list = get_tracks(playlist["id"], headers, track_list={})
    track_list = get_track_data(track_list, headers)
    track_list = get_track_features(track_list, headers)

    # playlist_item = {
    #     '_id': playlist["id"],
    #     'name': playlist["name"],
    #     'owner': "service",
    #     'images': playlist['images'],
    #     'tracks': list(track_list.values()),
    #     'for_train': True
    # }
    track_ids = list(track_list.keys())
    existing_track_ids = col_track.find({ '_id': {'$in': track_ids} }).distinct('_id')
    insert_tracks = []

    for track in list(track_list.values()):
        if track['_id'] not in existing_track_ids:
            insert_tracks.append(track)

    if insert_tracks:
        col_track.insert_many(insert_tracks)
    
    col_track.update_many({ '_id': {'$in': track_ids} }, { '$set': update_data })

    return 'success'


@app.route('/get_audio_feature')
def get_audio_feature():
    access_token = get_service_token()
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    tracks = list(col_track.find({'timbre': None}))
    for track in tracks:
        rfeature = requests.get(f'https://api.spotify.com/v1/audio-analysis/{track["_id"]}', headers=headers)
        feature = rfeature.json()
        if 'track' in feature:
            afeature = feature['track']
            segments = feature['segments']

            duration = afeature['duration']
            pitch_values = {'C': 0, 'C#':0, 'D':0, 'D#':0, 'E':0 , 'F':0, 'F#':0, 'G':0, 'G#':0, 'A':0, 'A#':0, 'B':0}
            timbre_values = {'B1': 0, 'B2':0, 'B3':0, 'B4':0, 'B5':0 , 'B6':0, 'B7':0, 'B8':0, 'B9':0, 'B10':0, 'B11':0, 'B12':0}

            for segment in segments:
                seg_duration = segment['duration']
                pitches = segment['pitches']
                pitch_values['C'] += pitches[0] * seg_duration
                pitch_values['C#'] += pitches[1] * seg_duration
                pitch_values['D'] += pitches[2] * seg_duration
                pitch_values['D#'] += pitches[3] * seg_duration
                pitch_values['E'] += pitches[4] * seg_duration
                pitch_values['F'] += pitches[5] * seg_duration
                pitch_values['F#'] += pitches[6] * seg_duration
                pitch_values['G'] += pitches[7] * seg_duration
                pitch_values['G#'] += pitches[8] * seg_duration
                pitch_values['A'] += pitches[9] * seg_duration
                pitch_values['A#'] += pitches[10] * seg_duration
                pitch_values['B'] += pitches[11] * seg_duration

                timbres = segment['timbre']
                timbre_values['B1'] += timbres[0] * seg_duration
                timbre_values['B2'] += timbres[1] * seg_duration
                timbre_values['B3'] += timbres[2] * seg_duration
                timbre_values['B4'] += timbres[3] * seg_duration
                timbre_values['B5'] += timbres[4] * seg_duration
                timbre_values['B6'] += timbres[5] * seg_duration
                timbre_values['B7'] += timbres[6] * seg_duration
                timbre_values['B8'] += timbres[7] * seg_duration
                timbre_values['B9'] += timbres[8] * seg_duration
                timbre_values['B10'] += timbres[9] * seg_duration
                timbre_values['B11'] += timbres[10] * seg_duration
                timbre_values['B12'] += timbres[11] * seg_duration
                

            for note in pitch_values:
                pitch_values[note] = pitch_values[note] / duration

            for basis in timbre_values:
                timbre_values[basis] = timbre_values[basis] / duration

            update_data = {
                'timbre': timbre_values,
                'pitches': pitch_values
            }
            col_track.update({'_id': track['_id']}, { '$set': update_data })
            print(track['name'] + ' done.')
        # time.sleep(1)

    return 'success'



def get_tracks(playlist_id, headers, next_url=None, track_list={}):
    if next_url:
        rtracks = requests.get(next_url, headers=headers)
    else:
        rtracks = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers)
        
    tracks = rtracks.json()
    for track in tracks['items']:
        if track['track']['id']:
            track_list[track['track']['id']] = {
                '_id': track['track']['id'],
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


def get_track_data(track_list, headers, iter_index=0):
    id_list = list(track_list.keys())
    start_index = iter_index*50
    end_index = (iter_index+1)*50 if (iter_index+1)*50 < len(id_list) else len(id_list)
    req_id_list = id_list[start_index:end_index]

    rdata = requests.get(f'https://api.spotify.com/v1/tracks/?ids={",".join(req_id_list)}', headers=headers)
    data = rdata.json()
    for track in data['tracks']:
        track_list[track['id']]['release_date'] = track['album']['release_date']

    if end_index != len(id_list):
        iter_index += 1
        return get_track_data(track_list, headers, iter_index=iter_index)
    else:
        return track_list


def get_track_features(track_list, headers, iter_index=0):
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


def get_service_token():
    now = datetime.now()
    access_token = None
    token = col_token.find_one({"_id": "service"})
    if token and token['expire_time'] > now:
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
            if token:
                col_token.update_one({'_id': 'service'}, {'$set': {'access_token': access_token, 'expire_time': now + timedelta(hours=1)}})
            else:
                col_token.insert_one({'_id': 'service', 'access_token': access_token, 'expire_time': now + timedelta(hours=1)})
    return access_token


def get_user_token(user_id):
    now = datetime.now()
    access_token = None
    token = col_token.find_one({"_id": user_id})
    if token and token['expire_time'] > now:
        access_token = token['access_token']
    # else:



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8887)