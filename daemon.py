import socket
import threading
import logging
import pickle
from tkinter import image_names
from utils import dht_hash, contains


class Daemon(threading.Thread):
    """ DHT Node Agent. """

    #1º daemon apenas 2 parametros
    #3 parametros de entrada
    #caminho para as imagens
    #porto para si proprio
    #Porto que ele se vai ligar para ligar a rede - 5000


    def __init__(self, address, port, nextport):
        """Constructor
        """
        threading.Thread.__init__(self)
        self.port = port
        self.host = 'localhost'
        self.daemon = []
        self.n_daeomns = 0

        if nextport is None:
            self.nextport = None
        else:
            self.nextport = nextport
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect((self.host, self.port))
        print("Conected to " + self.host + ":" + self.port)

    def send(self, address, msg):
        """ Send msg to address. """
        payload = pickle.dumps(msg)
        self.socket.sendto(payload, address)

    def recv(self):
        """ Retrieve msg payload and from address."""
        try:
            payload, addr = self.socket.recvfrom(1024)
        except socket.timeout:
            return None, None

        if len(payload) == 0:
            return None, addr
        return payload, addr