#!/usr/bin/python


import os
import imp
import threading
import argparse

fullsocket = imp.load_source('fullsocket', os.path.join('..', 'common',
                             'fullsocket.py'))


def retr_file(address, sock):
    method = sock.recv().strip()
    print(address, method)
    if method == 'INFO':
        sock.send('OK\n')
    elif method == 'LIST':
        to_send = ['OK']
        for name in os.listdir(os.getcwd()):
            to_send.append(name)
        to_send.append('END')
        sock.send('\n'.join(to_send))
    elif method == 'GET':
        sock.send('OK\n')
        filename = sock.recv()
        if os.path.isfile(filename):
            sock.send('EXISTS ' + str(os.path.getsize(filename)))
            try:
                userResponse = sock.recv()
            except RuntimeError:
                print('Client closed connection.')
                sock.close()
                return
            if userResponse[:2] == 'OK':
                print(address, 'sending \'{}\'...'.format(filename))
                with open(filename, 'rb') as f:
                    while True:
                        bytesToSend = f.read(1024)
                        if bytesToSend == '':
                            break
                        try:
                            sock.send(bytesToSend)
                        except (RuntimeError, fullsocket.socket.ConnectionResetError):
                            print(address, 'closed connection.')
        else:
            try:
                sock.send('ERR')
            except RuntimeError:
                print('Client closed connection.')
        sock.close()
    else:
        sock.send('ERROR\n')


def main(args):
    host = ''
    port = 1234

    s = fullsocket.FullSocket()
    s.setsockopt(fullsocket.socket.SOL_SOCKET, fullsocket.socket.SO_REUSEADDR, 1)
    s.bind((host, port))

    s.listen(5)

    print('Server started.')

    while True:
        conn, addr = s.accept()
        c = fullsocket.FullSocket(conn)
        print('client connected ip:<' + str(addr) + '>')
        t = threading.Thread(target=retr_file, args=(addr,c))
        t.start()
    s.close()

if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('-d DIR', '--directory DIR', help='directory from which to look files.')
    args = args.parse_args()
    main(args)

