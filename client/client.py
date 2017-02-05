#!/usr/bin/python

import os
import importlib.machinery as imp
import urwid
import argparse


fullsocket = imp.SourceFileLoader('fullsocket', os.path.join('..', 'common',
                                  'fullsocket.py')).load_module()


class GUI:
    palette = [
        # ...
    ]

    top = None

    def __init__(self, args):
        pass

    def main(self):
        self.loop = urwid.MainLoop(self.top, palette=self.palette,
                                   unhandled_input=self.unhandled_input)

    def unhandled_input(self, key):
        if key in ('q', 'Q', 'esc'):
            raise urwid.ExitMainLoop()


def simple_main():
    host = '127.0.0.1'      # The remote host
    port = 1234             # The same port as used by the server
    sock = fullsocket.FullSocket()
    sock.connect((host, port))
    filename = input('Filename? -> ')
    if filename != 'q':
        sock.send(filename)
        data = sock.recv()
        if data[:6] == 'EXISTS':
            file_size = int(data[6:])
            message = input('File Exists, ' + str(file_size) + 'Bytes, download? (Y/N)? -> ').lower()
            if message == 'y':
                if os.path.exists(os.path.join(os.getcwd(), filename)):
                    if input('File \'{}\' already exists. Replace it? y/n  ').lower() != 'y':
                        sock.close()
                        return
                sock.send('OK')
                f = open(filename, 'wb')
                total_recv = 0
                while total_recv < file_size:
                    data = sock.recv()
                    total_recv += len(data)
                    f.write(data)
                    print('{0:.3f}'.format((total_recv/float(file_size))*100) + '% Done')
                print('Download Complete!')
        else:
            print('File does not Exist!')
    sock.close()


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('-s', '--simple', help='run this client in simple mode (without'
                                             ' a nice interface; also ignores '
                                             'command-line arguments).',
                      action='store_true')
    args = args.parse_args()
    if args.simple:
        simple_main()
    else:
        GUI(args).main()

