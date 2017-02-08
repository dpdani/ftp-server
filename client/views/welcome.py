"""

Welcome screen.

"""

import os
import importlib.machinery as imp
import urwid
from .main import MainView
from . import common

fullsocket = imp.SourceFileLoader('fullsocket', os.path.join('..', 'common',
                                  'fullsocket.py')).load_module()


class WelcomeView(urwid.WidgetWrap):
    def __init__(self, frame):
        self.frame = frame
        self.title = "FTP-CLI"
        self.location = common.StyledEdit("FTP server:", edit_style=('edit', None), text_width=11, left_padding=5)
        self.port = common.StyledEdit("Port:", edit_style=('edit', None), text_width=11, left_padding=5)
        urwid.connect_signal(self.location.edit, 'change', self.clear_error)
        urwid.connect_signal(self.port.edit, 'change', self.clear_error)
        blank = urwid.AttrWrap(urwid.Divider(), 'body')
        content = [
            blank,
            blank,
            urwid.Padding(self.location, align='center'),
            urwid.Padding(self.port, align='center'),
            blank,
            blank,
            blank,
            blank,
            urwid.GridFlow([
                urwid.Button("Ok", self.on_ok),
                urwid.Button("Quit", self.on_quit)],
                8,3,1, 'center'
            ),
        ]
        self.listbox = urwid.ListBox(urwid.SimpleFocusListWalker(content))
        self.listbox = urwid.AttrWrap(self.listbox, 'body')
        super().__init__(self.listbox)

    def refresh(self):
        pass

    def clear_error(self, *args):
        self.frame.reset_status()

    def on_ok(self, *args):
        self.clear_error()
        host, port = self.location.edit.get_edit_text(), self.port.edit.get_edit_text()
        try:
            port = int(port)
        except ValueError:
            self.frame.set_status('Please provide a valid port number.', 'error')
            return
        sock = fullsocket.FullSocket()
        try:
            sock.connect((host,port))
        except:
            self.frame.set_status('No server found at specified location.', 'error')
            return
        else:
            sock.send('INFO')
            status = sock.recv()
            if status.strip() != 'OK':
                self.frame.set_status("Server is an unsupported FTP server. Received: {}...".format(status), 'error')
                return
            self.frame.set_body(
                MainView(sock=sock, frame=self.frame, address=(host, port))
            )

    def on_quit(self, *args):
        if hasattr(self, 'app_quit'):
            self.app_quit()