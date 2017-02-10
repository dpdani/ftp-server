__authors__ = ('paolo', 'Daniele Parmeggiani <dani.parmeggiani@gmail.com>')
# 12/2015
# Daniele Parmeggiani (compatibility with Python 3): 05/02/2017

import socket
import struct
import sys
import chardet

assert sys.version_info >= (2,5)  # needed for bytes objects
PY3 = sys.version_info >= (3,0)


class FullSocket:
    def __init__(self, sock=None):
        self.MSGLEN = 4
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def __getattr__(self, attr):
        return getattr(self.sock, attr)

    def recv(self):
        chunks = []
        bytes_recd = 0
        while bytes_recd < self.MSGLEN:
            chunk = self.sock.recv(min(self.MSGLEN - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            if PY3:
                chunks.append(chunk.decode(chardet.detect(chunk)['encoding']))
            else:
                chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        nstr  = ''.join(chunks)
        with open('asdf', 'w') as f:
            f.write(str(type(nstr.encode())))
            f.write('\n')
            f.write(str(len(nstr.encode())))
        if PY3:
            nsize = struct.unpack('I', nstr.encode()[:4])
        else:
            nsize = struct.unpack('I', nstr)
        size  = socket.ntohl(nsize[0])
        chunks = []
        bytes_recd = 0
        while bytes_recd < size:
            chunk = self.sock.recv(min(size - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            if PY3:
                chunks.append(chunk.decode())
            else:
                chunks.append(chunk)
            bytes_recd = bytes_recd + len(chunk)
        return ''.join(chunks)

    def send(self, msg):
        if PY3 and type(msg) != bytes:
            msg = msg.encode()
        size = len(msg)               # send msg length as unsigned integer
        nsize = socket.htonl(size)    #
        nstr = struct.pack('I',nsize)
        sizelen = len(nstr)
        totalsent = 0
        while totalsent < sizelen:
            sent = self.sock.send(nstr[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
