"""

Entering screen.

"""
import datetime
import os
import importlib.machinery as imp
import urwid
import threading
from . import common


fullsocket = imp.SourceFileLoader('fullsocket', os.path.join('..', 'common',
                                  'fullsocket.py')).load_module()


class MainView(urwid.WidgetWrap):
    def __init__(self, sock, frame, address):
        self.sock = sock
        self.frame = frame
        self.address = address
        self.title = "Home"
        self.refresh()

    def refresh(self):
        self.files_list = common.EntriesList(lesser_height=15, options=[], max_height=100)
        left_contents = [
            urwid.AttrWrap(urwid.Text("Home", 'center'), 'header'),
            urwid.AttrWrap(urwid.Text("FTP server at {}:{}.".format(
                self.address[0] if self.address[0] else 'localhost', self.address[1]
            )), 'mainview_title'),
            urwid.Divider(),
            urwid.Divider(),
            urwid.AttrWrap(urwid.Text("Files:"), 'mainview_title'),
            self.files_list,
        ]
        self.cols = urwid.Columns([
            ('weight', 3, urwid.ListBox(urwid.SimpleFocusListWalker(left_contents))),
            # common.ExpandedVerticalSeparator(
            #     urwid.ListBox(urwid.SimpleFocusListWalker([
            #         urwid.Button("Settings", on_press=self.on_settings),
            #         urwid.Button("Up Hosts", on_press=self.on_up_hosts),
            #         urwid.Button("Ignored Hosts", on_press=self.on_ignored_hosts),
            #         urwid.Button("About IP...", on_press=self.on_ip),
            #         urwid.Button("About MAC...", on_press=self.on_mac),
            #         urwid.Button("About Name...", on_press=self.on_name),
            #     ]))
            # ),
        ])
        super().__init__(self.cols)
        threading.Thread(target=self.fill_stats()).start()

    def fill_stats(self):
        self.frame.set_status("Waiting for response...")
        print('sas')
        self.sock.close()
        self.sock = fullsocket.FullSocket()
        self.sock.connect(self.address)
        self.sock.send('LIST')
        print('sas')
        files = self.sock.recv()
        self.sock.close()
        print('sas')
        files = files[3:-4].split('\n')  # removes header and footer
        if len(files) == 0:
            files.append('  - NO FILES -')
        files_ = []
        for file in files:
            txt = common.SelectableText(' - ' + file)
            txt.callback = self.download_file
            files_.append(urwid.AttrWrap(txt, None, 'reveal focus'))
        self.files_list.genericList.content[:] = files_
        self.files_list.genericList.content.set_focus(0)

    def download_file(self, label):
        filename = label[3:]
        self.sock = fullsocket.FullSocket()
        self.sock.connect(self.address)
        self.sock.send('GET')
        self.sock.recv()  # OK
        self.sock.send(filename)
        status = self.sock.recv()
        if status == 'ERR':
            # file not found (??)
            return
        else:
            length = int(status.split(' ')[1])
        sure = common.YesNoDialog('File is {} bytes. Do you want to proceed?',
            attr='default', width=40, height=10, body=self.frame)
        if sure.listen():
            self.sock.send('OK')
        f = open(filename, 'wb')
        total_recv = 0
        while total_recv < length:
            data = self.sock.recv()
            total_recv += len(data)
            f.write(data)
