from socket import *
import selectors
from protocol import *
import subprocess
import shortuuid

import base64
from demucs.audio import AudioFile
from pydub import AudioSegment
import time

import os

_host = "localhost" 
_port =  5002
_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_selector = selectors.DefaultSelector()

_start_files = {} # MUSIC 
JOBS = {}
_START_FILE_ID = 0
_JOB_ID = 0

IDLE_WORKERS = []
ACTIVE_WORKERS = []

# TEST: in-memory files
FILES = {}

MUSIC = {}

'''
Tracks: 
- 0 drums
- 1 bass 
- 2 other
- 3 vocals 
'''
_TRACKS_ = {'0': 'drums', '1': 'bass', '2': 'other', '3': 'vocals'}

def remove_files_in_folder(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
                        
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"[DEBUG]: Removed file: {file_name}")

def reset_system():
  global _start_files
  global JOBS
  global _START_FILE_ID
  global _JOB_ID
  global IDLE_WORKERS 
  global ACTIVE_WORKERS
  global FILES 
  global MUSIC 

  remove_files_in_folder('./temp')
  remove_files_in_folder('./tracks')

  _start_files = {} # MUSIC 
  JOBS = {}
  _START_FILE_ID = 0
  _JOB_ID = 0
  IDLE_WORKERS = []
  ACTIVE_WORKERS = []
  FILES = {}
  MUSIC = {}

def accept(sock, mask):
    conn, addr = _socket.accept()
    conn.setblocking(False)
    _selector.register(conn, selectors.EVENT_READ, read)
    print("[MANAGER]: accepted ", conn)

def get_start_file_id():
    global _START_FILE_ID

    _id = _START_FILE_ID
    _START_FILE_ID += 1
    return _id

def get_job_id():
    global _JOB_ID

    _id = _JOB_ID
    _JOB_ID += 1
    return _id

def save_file(music_id, file):
  decoded_content = base64.b64decode(file)
  file_name = f'./temp/{music_id}.mp3'

  f = open(file_name, 'wb')
  f.write(decoded_content)
  f.close()

  return file_name

def save_start_file(file: str):
    _music_id = get_start_file_id()
    _start_files[_music_id] = file
    save_file(_music_id, file)

    print("[MANAGER]: file with id [", _music_id, "] saved!")
    return _music_id


def split_audio_into_chunks(filename, music_id, n):
    audio = AudioSegment.from_mp3(filename)
    total_duration = len(audio)
    chunk_duration = total_duration // n

    chunks = []
    for i in range(n):
      start = i * chunk_duration
      end = (i + 1) * chunk_duration

      if i == n - 1:
          end = total_duration

      chunk = audio[start:end]

      chunk_filename = f"./temp/{music_id}_chunk_{i}.mp3"
      FILES[chunk_filename] = chunk.export(format="mp3").read()
      chunks.append(chunk_filename)
      print(f'[DEBUG]: saved chunk with filename: {chunk_filename}')

    return chunks

def start_to_process_music(music_id, tracks):
    if not music_id in _start_files:
        return

    if len(IDLE_WORKERS) == 0:
        #TODO(@cobileacd): handle this.
        print("[MANAGER]: there are no workers available.")
        return

    file_name = f'./temp/{music_id}.mp3'
    chunks = split_audio_into_chunks(file_name, music_id, len(IDLE_WORKERS))
    print(len(chunks))

    for chunk_filename in chunks:
        job_id = get_job_id()
        JOBS[job_id] = { 'job_id': job_id, 'music_id': music_id, 'chunk_filename': chunk_filename, 'is_working': False, 'start_time': 0, 'end_time': 0, 'time': 0, 'type': 'process', 'size': len(FILES[chunk_filename]), 'tracks': tracks, 'composed': False }

    return len(chunks)

# TODO: find better name for this
def get_work():
    for job_id in JOBS:
        if JOBS[job_id]['is_working'] == False:
            JOBS[job_id]['is_working'] = True
            return job_id

    return None

def get_worker():
    if IDLE_WORKERS != []:
        worker = IDLE_WORKERS.pop(0)
        ACTIVE_WORKERS.append(worker)
        return worker
    else:
        return None

def open_file(filename):
    with open(filename, 'rb') as file:
        file_bytes = file.read()
    return file_bytes

def process_music():
    for job_id in JOBS:
        if JOBS[job_id]['is_working'] == False:
            JOBS[job_id]['is_working'] = True
            JOBS[job_id]['start_time'] = time.time()

            music_id = JOBS[job_id]['music_id']
            #chunk = open_file(JOBS[job_id]['chunk_filename'])
            chunk = FILES[JOBS[job_id]['chunk_filename']]

            chunk_b64 = base64.b64encode(chunk).decode()

            worker = get_worker()
            if worker != None: 
                print("[MANAGER]: sent StartWorkMessage! to", worker)
                PROTO.send_msg(worker, PROTO.start_work(job_id, music_id, chunk_b64))
            else:
                # TODO: waits for worker?
                pass

def save_tracks(job_id, music_id, tracks):
    for tracks_id in tracks:
        decoded_content = base64.b64decode(tracks[tracks_id])

        filename = f'./tracks/{job_id}_manager_track_{tracks_id}.wav'
        with open(filename, 'wb') as f:
            f.write(decoded_content)

def check_music_processing(music_id):
    ids = []
    for job_id in JOBS:
        if JOBS[job_id]['music_id'] != music_id:
            continue
        if JOBS[job_id]['time'] == 0: # There's still chunks being processed, return 
            return
        if JOBS[job_id]['composed'] == True:
            continue 

        ids.append(job_id)

    user_tracks = JOBS[job_id]['tracks']
    tracks_to_send = []
    for job_id in ids:
        tracks = []
        for track_id in _TRACKS_:
            if track_id in user_tracks: 
                continue
            # TODO: check which tracks user wants
            # if not track_id in user_tracks: continue
            track_filename = f'./tracks/{job_id}_manager_track_{track_id}.wav'

            track_contents = open_file(track_filename)
            track_b64encoded = base64.b64encode(track_contents).decode() 

            tracks.append(track_b64encoded)

        tracks_to_send.append(tracks)

    tracks_to_send_json = json.dumps(tracks_to_send) 

    # Send to worker
    job_id = get_job_id()
    JOBS[job_id] = { 
                       'job_id': job_id, 
                       'music_id': music_id, 
                       'chunk_filename': None, 
                       'size': 0,  
                       'is_working': True, 
                       'start_time': time.time(), 
                       'end_time': 0, 
                       'time': 0, 
                       'type': 'compose', 
                       'composed': True, 
                       'tracks': user_tracks 
                   }

    worker = get_worker()
    if worker != None:
        print("[MANAGER]: sent compose work to ", worker)
        PROTO.send_msg(worker, PROTO.start_compose(job_id, music_id, tracks_to_send_json))

        for job_id in ids:
            JOBS[job_id]['composed'] = True
    else:
        # TODO: HANDLE
        pass

def getJOBS_for_api():
    apiJOBS = []
    for job_id in JOBS:
        size = JOBS[job_id]['size']
        time = JOBS[job_id]['time']
        music_id = JOBS[job_id]['music_id']
        tracks = JOBS[job_id]['tracks']
        #tracks = [0, 1, 2, 3] # TEMP:

        apiJOBS.append({'job_id': job_id, 'size': size, 'time': time, 'music_id': music_id, 'track_id': tracks})

    return apiJOBS

def read(conn, mask):
    try:
        msg = PROTO.recv_msg(conn)

        if msg:
            if isinstance(msg, StartFileMessage):
                print("[MANAGER]: received StartFileMessage! from ", conn)
                music_id = save_start_file(msg.file)
                PROTO.send_msg(conn, PROTO.start_file(music_id))
            elif isinstance(msg, FinalFileMessage):
                print("[MANAGER]: received FinalFileMessage! from ", conn)
                file = msg.file
                music_id = msg.music_id
                job_id = msg.job_id
                file_id = shortuuid.uuid()

                instruments = []
                tracks = msg.tracks

                i = 0
                for track_id in _TRACKS_:
                    if track_id in JOBS[job_id]['tracks']: 
                        continue

                    file_id = shortuuid.uuid()
                    decoded = base64.b64decode(tracks[i])

                    instruments.append(
                        {"name": _TRACKS_[track_id], "track": f"/file/{file_id}", "file": decoded}
                    )
                    i += 1
                #decode 


                MUSIC[music_id] = {'final': f'/file/{file_id}', 'file': file, 'instruments': instruments}

                IDLE_WORKERS.append(conn)
                # get job with id [time] = time.time - start_time

                # TODO: function this.
                JOBS[msg.job_id]['end_time'] = time.time()
                elapsed = JOBS[msg.job_id]['end_time'] - JOBS[msg.job_id]['start_time']
                JOBS[msg.job_id]['time'] = elapsed
                JOBS[msg.job_id]['size'] = len(file)

            elif isinstance(msg, ProcessMusicMessage):
                print("[MANAGER]: received ProcessMusicMessage! from ", conn)
                start_to_process_music(msg.music_id, msg.tracks)
                process_music()
            elif isinstance(msg, GetStatusMessage):
                print("[MANAGER]: received GetStatusMessage! from ", conn)

                final = ""
                instruments_api = []
                if msg.music_id in MUSIC:
                    final = MUSIC[msg.music_id]['final'] 
                    instruments = MUSIC[msg.music_id]['instruments'] 

                    for track in instruments:
                        instruments_api.append({"name": track['name'], "track": track['track']})

                PROTO.send_msg(conn, PROTO.get_process_status(msg.music_id, final, instruments_api))
            elif isinstance(msg, GetFinalFileMessage):
                print("[MANAGER]: received GetFinalFileMessage! from ", conn)
                for music_id in MUSIC:
                    if MUSIC[music_id]['final'] == msg.filename:
                        file = MUSIC[music_id]['file']
                        break

                    instruments = MUSIC[music_id]['instruments']
                    for track in instruments:
                        if track['track'] == msg.filename:
                            file = base64.b64encode(track['file']).decode()
                            break

                PROTO.send_msg(conn, PROTO.get_final_file(msg.filename, file))
            elif isinstance(msg, StartWorkMessage):
                print("[MANAGER]: received StartWorkMessage! from ", conn)
                IDLE_WORKERS.append(conn)
            elif isinstance(msg, GetJobsMessage):
                print("[MANAGER]: received GetJobsMessage! from ", conn)
                apiJOBS = getJOBS_for_api() 
                PROTO.send_msg(conn, PROTO.get_jobs(json.dumps(apiJOBS)))
            elif isinstance(msg, ResetMessage):
                print("[MANAGER]: received ResetMessage! from ", conn)
                reset_system()
            elif isinstance(msg, FinishedWorkMessage):
                print("[MANAGER]: received FinishedWorkMessage! from ", conn)
                tracks = json.loads(msg.tracks)
                JOBS[msg.job_id]['end_time'] = time.time()

                elapsed = JOBS[msg.job_id]['end_time'] - JOBS[msg.job_id]['start_time']
                JOBS[msg.job_id]['time'] = elapsed
                print(f"[MANAGER]: job: {msg.job_id} was processed in {elapsed} ms.")

                save_tracks(msg.job_id, msg.music_id, tracks)

                IDLE_WORKERS.append(conn) 

                # TODO: checks wheter all chunks were processed and
                check_music_processing(msg.music_id) 
                # TODO: Active workers remove
        else:
            pass
    except Exception as e:
        print(e)
        print("[MANAGER]: EXCEPTION")
        #_selector.unregister(conn)
        #conn.close()

if __name__ == "__main__":
    _socket.bind(("localhost", _port))
    _socket.listen()
    _selector.register(_socket, selectors.EVENT_READ, accept)

    # Loop
    print("[MANAGER]: Server started!")
    while 1:
        events = _selector.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)
