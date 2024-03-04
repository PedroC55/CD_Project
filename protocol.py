# Protocol for messages between broker (manager server/ backend?) and web app
# Messages Spec:
# - StartFileMessage (message that gets sent to broker when app receives a new music_file) 
# - FinalFileMessage (message that gets sent to webapp by broker when processing is done) 

import json
from datetime import datetime
import socket
import time

class Message:
    """ Message type. """

class StartFileMessage(Message):
    def __init__(self, file):
        self.file = file

    def __str__(self):
        data = {'command': 'start_file', 'file': self.file}
        return json.dumps(data)

class FinalFileMessage(Message):
    # TODO
    def __init__(self, music_id, file, job_id, tracks):
        self.file = file
        self.job_id = job_id
        self.music_id = music_id
        self.tracks = tracks

    def __str__(self):
        data = {'command': 'final_file', 'music_id': self.music_id, 'file': self.file, 'job_id': self.job_id, 'tracks': self.tracks}
        return json.dumps(data)

class ResetMessage(Message):
    def __init__(self):
      pass

    def __str__(self):
        data = {'command': 'reset'}
        return json.dumps(data)

class GetFinalFileMessage(Message):
    def __init__(self, filename, file):
        self.filename = filename
        self.file = file

    def __str__(self):
        data = {'command': 'get_final_file', 'filename': self.filename, 'file': self.file}
        return json.dumps(data)

class ProcessMusicMessage(Message):
    def __init__(self, music_id, tracks):
        self.music_id = music_id
        self.tracks = tracks

    def __str__(self):
        data = {'command': 'process_music', 'music_id': self.music_id, 'tracks': self.tracks}
        return json.dumps(data)

class StartWorkMessage(Message):
    def __init__(self, job_id, music_id, file):
        self.job_id = job_id 
        self.music_id = music_id
        self.file = file

    def __str__(self):
        data = {'command': 'start_work', 'job_id': self.job_id, 'music_id': self.music_id, 'file': self.file}
        return json.dumps(data)

class FinishedWorkMessage(Message):
    def __init__(self, job_id, music_id, tracks):
        self.job_id = job_id 
        self.music_id = music_id
        self.tracks = tracks # List of tracks

    def __str__(self):
        data = {'command': 'finished_work', 'job_id': self.job_id, 'music_id': self.music_id, 'tracks': self.tracks}
        return json.dumps(data)

class StartComposeMessage(Message):
    def __init__(self, job_id, music_id, tracks):
        self.job_id = job_id 
        self.music_id = music_id
        self.tracks = tracks

    def __str__(self):
        data = {'command': 'start_compose', 'job_id': self.job_id, 'music_id': self.music_id, 'tracks': self.tracks}
        return json.dumps(data)
    
class GetJobsMessage(Message):
    def __init__(self, jobs_list):
        self.jobs_list = jobs_list

    def __str__(self):
        data = {'command': 'get_jobs', 'jobs_list': self.jobs_list}
        return json.dumps(data)
    
class GetStatusMessage(Message):
    def __init__(self, music_id, final, instruments):
        self.music_id = music_id
        self.final = final 
        self.instruments = instruments

    def __str__(self):
        data = {'command': 'get_process_status', 'music_id': self.music_id, 'final': self.final, 'instruments': self.instruments}
        return json.dumps(data)

class PROTO:
    @classmethod
    def start_file(cls, file: str) -> StartFileMessage:
        return StartFileMessage(file)

    @classmethod
    def final_file(cls, music_id: str, file: str, job_id: str, tracks: str) -> FinalFileMessage:
        return FinalFileMessage(music_id, file, job_id, tracks)

    @classmethod
    def get_final_file(cls, filename: str, file: str) -> GetFinalFileMessage:
        return GetFinalFileMessage(filename, file)

    @classmethod
    def process_music(cls, music_id: str, tracks: str) -> ProcessMusicMessage:
        return ProcessMusicMessage(music_id, tracks)

    @classmethod
    def start_work(cls, job_id: str, music_id: str, file: str) -> StartWorkMessage:
        return StartWorkMessage(job_id, music_id, file)

    @classmethod
    def finished_work(cls, job_id: str, music_id: str, tracks: str) -> FinishedWorkMessage:
        return FinishedWorkMessage(job_id, music_id, tracks)

    @classmethod
    def start_compose(cls, job_id: str, music_id: str, tracks: str) -> StartComposeMessage:
        return StartComposeMessage(job_id, music_id, tracks)
    
    @classmethod
    def get_jobs(cls, jobs_list: str) -> GetJobsMessage:
        return GetJobsMessage(jobs_list)
    
    @classmethod
    def get_process_status(cls, music_id: str, final: str, instruments: str) -> GetStatusMessage:
        return GetStatusMessage(music_id, final, instruments)

    @classmethod
    def reset(cls) -> ResetMessage:
        return ResetMessage()

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        size_msg = len(str(msg).encode('utf-8')).to_bytes(4, byteorder='big')
        new_msg = size_msg + str(msg).encode('utf-8')

        try:
            connection.setblocking(False) 
            total_sent = 0
            while total_sent < len(new_msg):
                try:
                    sent = connection.send(new_msg[total_sent:])
                    if sent == 0:
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
                except BlockingIOError as e:
                    #if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    #    raise  # Re-raise exception if it's not the expected error
                    continue
        finally:
            connection.setblocking(True)

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        size_bytes = connection.recv(4) 
        size = int.from_bytes(size_bytes, byteorder='big')

        data = b''
        total_received = 0
        while total_received < size:
            chunk = connection.recv(max(size - total_received, 4096))
            if len(chunk) == 0:
                raise RuntimeError("Socket connection broken")
            data += chunk
            total_received += len(chunk)

        try:
            data_json = json.loads(data.decode('utf-8'))
            cmd = data_json['command']

            if cmd == 'start_file':
                file = data_json['file']
                return PROTO.start_file(file)
            elif cmd == 'final_file':
                file = data_json['file']
                music_id = data_json['music_id']
                job_id = data_json['job_id']
                tracks = data_json['tracks']
                return PROTO.final_file(music_id, file, job_id, tracks)
            elif cmd == 'process_music':
                music_id = data_json['music_id']
                tracks = data_json['tracks']
                return PROTO.process_music(music_id, tracks)
            elif cmd == 'start_work':
                job_id = data_json['job_id']
                music_id = data_json['music_id']
                file = data_json['file']
                return PROTO.start_work(job_id, music_id, file)
            elif cmd == 'finished_work':
                job_id = data_json['job_id']
                music_id = data_json['music_id']
                tracks = data_json['tracks']
                return PROTO.finished_work(job_id, music_id, tracks)
            elif cmd == 'start_compose':
                job_id = data_json['job_id']
                music_id = data_json['music_id']
                tracks = data_json['tracks']
                return PROTO.start_compose(job_id, music_id, tracks)
            elif cmd == 'get_jobs':
                jobs_list = data_json['jobs_list']
                return PROTO.get_jobs(jobs_list)
            elif cmd == 'get_process_status':
                music_id = data_json['music_id']
                final = data_json['final']
                instruments = data_json['instruments']
                return PROTO.get_process_status(music_id, final, instruments)
            elif cmd == 'get_final_file':
                filename = data_json['filename']
                file = data_json['file']
                return PROTO.get_final_file(filename, file)
            elif cmd == 'reset':
                return PROTO.reset()
            
        except Exception as e:
            print(e)
            raise BadFormat

class BadFormat(Exception):
    def __init__(self, original_msg: bytes = None):
        self.original = original_msg 

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")
