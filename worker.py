from socket import *
import selectors
from protocol import *
import sys

from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio

import base64

import torch 
torch.set_num_threads(1)

from pydub import AudioSegment
import io

JOB_ID = -1

_host = 'localhost'
_SERVER_PORT = 5002
_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

_TRACKS_ = {'drums': 0, 'bass': 1, 'other': 2, 'vocals': 3}

def save_file(job_id, file):
  decoded_content = base64.b64decode(file)
  file_name = f'./temp/worker_{job_id}.mp3'

  f = open(file_name, 'wb')
  f.write(decoded_content)
  f.close()

  return file_name

def compose_music(tracks, music_id, job_id):
    audio_segments = []
    for j in range(len(tracks)):
        segments = []
        for i in range(len(tracks[0])):
            decoded = base64.b64decode(tracks[j][i])
            audio_segment = AudioSegment.from_file(io.BytesIO(decoded))
            segments.append(audio_segment)
        audio_segments.append(segments)

    for seg in audio_segments:
        for track in seg:
            print(len(track))

    composed_tracks = []
    for i in range(len(tracks[0])):
        track = audio_segments[0][i]
        for j in range(1, len(audio_segments)):
            track = track.append(audio_segments[j][i], crossfade=0)

        composed_tracks.append(track)

    merged = composed_tracks[0]
    for audio_segment in composed_tracks[1:]:
        merged = merged.overlay(audio_segment)

    output_buffer = io.BytesIO()
    merged.export(output_buffer, format="mp3")
    output_buffer.seek(0)
    merged_contents = output_buffer.read()
    print("[WORKER]: done composing music.")

    merged_encoded = base64.b64encode(merged_contents).decode()

    tracks_to_send = [] 
    for track in composed_tracks:
        buffer = io.BytesIO()
        track.export(buffer, format="mp3")
        buffer.seek(0)
        track_bytes = buffer.read()
        tracks_to_send.append(base64.b64encode(track_bytes).decode())

    PROTO.send_msg(_socket, PROTO.final_file(music_id, merged_encoded, job_id, tracks_to_send))
        
def read_from_manager(conn, mask, sel):
  global JOB_ID

  try:
      msg = PROTO.recv_msg(conn)
      if msg:
          if isinstance(msg, StartWorkMessage):
              JOB_ID = msg.job_id
              music_id = msg.music_id
              file = msg.file

              print(f"[WORKER]: received processing work from manager: id: {JOB_ID}, music_id: {music_id}")
              file_name = save_file(JOB_ID, file)
              tracks = job_process_music(file_name)

              PROTO.send_msg(_socket, PROTO.finished_work(JOB_ID, music_id, json.dumps(tracks)))
          if isinstance(msg, StartComposeMessage):
              print("[WORKER]: received compose work from manager!")
              compose_music(json.loads(msg.tracks), msg.music_id, msg.job_id)
      else:
          pass
  except BadFormat:
      pass

def open_file(filename):
    with open(filename, 'rb') as file:
        file_bytes = file.read()
    return file_bytes

def job_process_music(filename):
    model = get_model(name='htdemucs')
    model.cpu()
    model.eval()

    # load the audio file
    wav = AudioFile(filename).read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    
    # apply the model
    sources = apply_model(model, wav[None], device='cpu', progress=True, num_workers=1)[0]

    sources = sources * ref.std() + ref.mean()

    # store the model
    tracks = {}
    for source, name in zip(sources, model.sources):
        stem = f'./tracks/{JOB_ID}_{name}.wav'
        save_audio(source, str(stem), samplerate=model.samplerate)

        track = open_file(stem) 
        track_b64_encoded = base64.b64encode(track).decode()
        tracks[_TRACKS_[name]] = track_b64_encoded

    return tracks

if __name__ == "__main__":
  _selector = selectors.DefaultSelector()

  _selector.register(_socket, selectors.EVENT_READ, read_from_manager)
  _socket.connect(('localhost', _SERVER_PORT))

  PROTO.send_msg(_socket, PROTO.start_work("-1", "-1", "-1"))

  while True:
      events = _selector.select()
      for key, mask in events:
          callback = key.data
          callback(key.fileobj, mask, _selector)
