import socket
import pickle
import logging

def __init__(self, address):
        """ Initialize client."""
        self.dht_addr = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.logger = logging.getLogger("DHTClient")

def get(self, key):
        """ Retrieve key from DHT."""
        msg = {"method": "GET", "args": {"key": key}}
        pickled_msg = pickle.dumps(msg)
        self.socket.sendto(pickled_msg, self.dht_addr)
        pickled_msg, addr = self.socket.recvfrom(1024)
        out = pickle.loads(pickled_msg)
        if out["method"] != "ACK":
            self.logger.error("Invalid msg: %s", out)
            return None
        return out["args"]