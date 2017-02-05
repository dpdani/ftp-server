#!/usr/bin/python


import os
import importlib.machinery as imp
import threading
import argparse

fullsocket = imp.SourceFileLoader('fullsocket', os.path.join('..', 'common',
                                  'fullsocket.py')).load_module()


def retr_file(name, sock):
    filename = sock.recv()
    if os.path.isfile(filename):
        sock.send('EXISTS ' + str(os.path.getsize(filename)))
        try:
            userResponse = sock.recv()
        except RuntimeError:
            print('Client closed connection.')
            sock.close()
            return
        if userResponse[:2] =='OK':
            with open(filename, 'rb') as f:
                while True:
                    bytesToSend = f.read(1024)
                    if bytesToSend == '':
                        break
                    try:
                        sock.send(bytesToSend)
                    except RuntimeError:
                        print('Client closed connection.')
    else:
        try:
            sock.send('ERR')
        except RuntimeError:
            print('Client closed connection.')
    sock.close()


def main(args):
    host = ''
    port = 1234

    s = fullsocket.FullSocket()
    s.bind((host, port))

    s.listen(5)

    print('Server started.')

    while True:
        conn, addr = s.accept()
        c = fullsocket.FullSocket(conn)
        print('client connected ip:<' + str(addr) + '>')
        t = threading.Thread(target=retr_file, args=('retrThread',c))
        t.start()
    s.close()

if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('-d DIR', '--directory DIR', help='directory from which to look files.')
    args = args.parse_args()
    main(args)

