from flask import Flask, request, jsonify, render_template, send_file

import subprocess
import threading

import base64
import io

from  socket import * 
import selectors

from .protocol import *

from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio

import torch 
torch.set_num_threads(1)

app = Flask(__name__)

musics = []
_host = 'localhost'
_SERVER_PORT = 5002
_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_selector = selectors.DefaultSelector()

def read_from_manager(conn, mask, sel):
    try:
        msg = PROTO.recv_msg(conn)
        if msg:
            return msg
        else:
            pass
    except BadFormat:
        pass

    return None

def wait_and_get_response_from_server():
    while True:
        events = _selector.select()
        for key, mask in events:
            callback = key.data
            return callback(key.fileobj, mask, _selector)

_selector.register(_socket, selectors.EVENT_READ, read_from_manager)
_socket.connect(('localhost', _SERVER_PORT))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/music', methods=['POST', 'GET'])
def add_music():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'Empty file provided'}), 400

        file.save('uploads/' + file.filename)

        name = file.filename 
        band = request.form.get('band')

        #tracks = get_tracks_from_music(file.filename)
        #tracks = [{'name': 'Drums', 'track_id': '1'}]
        _TRACKS_ = {0: 'drums', 1: 'bass', 2: 'other', 3: 'vocals'}

        file.seek(0)
        file_contents = file.read()

        contents_b64 = base64.b64encode(file_contents).decode()

        PROTO.send_msg(_socket, PROTO.start_file(contents_b64))

        start_file_message = wait_and_get_response_from_server()

        musics.append({'music_id': start_file_message.file, 'name': name, 'band': band, 'tracks': _TRACKS_})

        return jsonify({'music_id': start_file_message.file, 'name': name, 'band': band, 'tracks': _TRACKS_}), 200

    elif request.method == 'GET':

        return jsonify(musics), 200

# Processing a music
@app.route('/music/<int:music_id>', methods=['POST'])
def process_music(music_id):
    tracks = request.json.get('tracks')

    PROTO.send_msg(_socket, PROTO.process_music(music_id, json.dumps(tracks)))
    return jsonify(None), 200

# NOTE: Getting the processing status of a music
@app.route('/music/<int:music_id>', methods=['GET'])
def get_processing_status(music_id):
    PROTO.send_msg(_socket, PROTO.get_process_status(music_id, '', ''))
    status_msg = wait_and_get_response_from_server()
    instruments = status_msg.instruments

    progress = 100
    if status_msg.final == '': 
        progress = 0

    return jsonify({'progress': progress, 'instruments': instruments, 'final': status_msg.final}), 200

# Listing all submitted jobs
@app.route('/job', methods=['GET'])
def list_all_jobs():
    PROTO.send_msg(_socket, PROTO.get_jobs([]))
    job_message = wait_and_get_response_from_server()

    return jsonify(json.loads(job_message.jobs_list)), 200

# Getting information about a specific job
@app.route('/job/<int:job_id>', methods=['GET'])
def get_job_info(job_id):
    '''
    job = next((j for j in jobs if j['job_id'] == job_id), None)
    if not job:
        return jsonify({'message': 'Job not found'}), 404
    
    job_info = get_additional_job_info(job_id)
    '''
    
    return jsonify(job_info), 200

# Resetting the system
@app.route('/reset', methods=['POST'])
def reset_system():
    PROTO.send_msg(_socket, PROTO.reset())
    return jsonify({'message': 'System reset successful'}), 200

@app.route('/file/<string:filename>', methods=['GET'])
def download_file(filename):
    PROTO.send_msg(_socket, PROTO.get_final_file(f'/file/{filename}', ''))
    get_final_file_msg = wait_and_get_response_from_server()
    file = get_final_file_msg.file

    decoded = base64.b64decode(file)
    file_stream = io.BytesIO()
    file_stream.write(decoded)
    file_stream.seek(0)

    return send_file(
        file_stream, 
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=f'{filename}.mp3'
    )

if __name__ == '__main__':
    app.run()
