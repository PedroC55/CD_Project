import socket
import pickle
import logging

def __init__(self, address):
        """ Initialize client."""
        self.dht_addr = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.logger = logging.getLogger("DHTClient")