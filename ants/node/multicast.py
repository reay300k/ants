# encodung=utf8
from ants.utils import manager

__author__ = 'wcong'
import socket
import threading
import time
import logging

'''
this multicast file where all multicast tools

'''


def get_host_name():
    return socket.gethostbyname(socket.gethostname())


def make_receive_socket(ip, port):
    receive_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    receive_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    receive_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    receive_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    logging.info('start multicast server')
    receive_sock.bind((ip, port))
    host = get_host_name()
    receive_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
    receive_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
                            socket.inet_aton(ip) + socket.inet_aton(host))
    return receive_sock


def make_cast_socket(ip, post):
    cast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    cast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
    return cast_sock


class MulticastManager(manager.Manager):
    '''
    what we do
    start a cast
    accept a cast
    send message
    '''
    ip = '224.1.1.1'
    port = 8900
    receive_length = 22

    def __init__(self, node_manager, receive_callback=None):
        self.settings = node_manager.settings
        self.is_multicast = self.settings.get('MULTICAST_ENABLED')
        if not self.is_multicast:
            return
        self.node_manager = node_manager
        self.message = self.settings.get('CLUSTER_NAME') + ':' + str(self.settings.get('TRANSPORT_PORT'))
        self.cast_sock = make_cast_socket(self.ip, self.port)
        self.receive_sock = make_receive_socket(self.ip, self.port)
        self.start_time = time.time()
        self.multicast_status = MulticastStatus()
        self.receive_callback = receive_callback


    def stop(self):
        self.stop_cast()

    def start(self):
        if self.is_multicast:
            self.find_node()

    def cast(self):
        logging.info("going to send request,hopping to find node")
        multicast_thread = MulticastThread(self)
        multicast_thread.start()

    def stop_cast(self):
        self.multicast_status.stop()

    def send_message(self):
        self.cast_sock.sendto(self.message, (self.ip, self.port))

    def find_node(self):
        logging.info('start multicast receive thread')
        receive_thread = ReceiveThread(self)
        receive_thread.start()

    def get_message(self):
        data, addr = self.receive_sock.recvfrom(self.receive_length)
        return data, addr


class MulticastStatus:
    status_start = 'start'
    status_run = 'run'
    status_stop = 'stop'

    def __init__(self):
        self.status = self.status_start

    def run(self):
        self.status = self.status_run

    def stop(self):
        self.status = self.status_stop

    def is_run(self):
        return self.status == self.status_run


class ReceiveThread(threading.Thread):
    sleep_time = 1

    def __init__(self, multicast_manager):
        super(ReceiveThread, self).__init__()
        self.multicast_manager = multicast_manager

    def run(self):
        self.multicast_manager.multicast_status.run()
        self.multicast_manager.cast()
        while self.multicast_manager.multicast_status.is_run():
            data, addr = self.multicast_manager.get_message()
            if data == self.multicast_manager.message:
                if self.multicast_manager.receive_callback:
                    self.multicast_manager.receive_callback(addr, data)
            time.sleep(self.sleep_time)


class MulticastThread(threading.Thread):
    def __init__(self, multicast):
        super(MulticastThread, self).__init__()
        self.multicast = multicast

    def run(self):
        self.multicast.send_message()