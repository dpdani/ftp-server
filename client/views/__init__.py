import urwid
import threading
import datetime
import time
from .welcome import WelcomeView
from .main import MainView
from . import common


stop_evt = threading.Event()


def set_ui(ui):
    common.ui = ui


class MainFrame(urwid.Frame):
    def __init__(self):
        self.header_txt = urwid.Text("FTP-CLI client", 'center')
        self.header_txt = urwid.AttrWrap(self.header_txt, 'header')
        self.header_date = urwid.Text("{}", 'left')
        self.header_date = urwid.AttrWrap(self.header_date, 'header')
        self.header_time = urwid.Text("{}", 'right')
        self.header_time = urwid.AttrWrap(self.header_time, 'header')
        self.commands = urwid.Columns([
            urwid.AttrWrap(urwid.Text("[esc|q: Exit]", 'left'), 'header buttons'),
            urwid.AttrWrap(urwid.Text("[w: Back]", 'center'), 'header buttons'),
            urwid.AttrWrap(urwid.Text("[e: Next]", 'center'), 'header buttons'),
            urwid.AttrWrap(urwid.Text("[F5|r: Refresh]", 'right'), 'header buttons'),
        ])
        self.header = urwid.Pile([
            urwid.Columns([
                self.header_date,
                ('weight', 2, self.header_txt),
                self.header_time,
            ]),
            self.commands,
            urwid.AttrWrap(urwid.Divider(div_char='━'), 'header'),
        ])
        self.placeholder = urwid.Text("Placeholder")
        self.body_history = {}
        self.current_view = 0
        self.status = urwid.AttrWrap(urwid.Text(""), 'footer')  # footer
        self.reset_status()
        self.footer = urwid.Pile(
            [urwid.AttrWrap(urwid.Divider(div_char='━'), 'header'), self.status])
        super().__init__(
            body=urwid.Filler(self.placeholder),
            header=self.header,
            footer=self.footer,
        )
        threading.Thread(target=self.keep_time_updated).start()

    def keep_time_updated(self):
        while not stop_evt.is_set():
            try:
                self.header_date.set_text(datetime.datetime.now().strftime("%d/%m/%Y"))
                self.header_time.set_text(datetime.datetime.now().strftime("%H:%M"))
                time.sleep(.1)
            except:
                break

    def set_status(self, text, color='waiting'):
        self.status.set_text(text)
        self.status.set_attr(color)

    def reset_status(self):
        self.set_status("Ready.", 'body')

    def set_body(self, body):
        if hasattr(self, 'app_quit'):
            body.app_quit = self.app_quit
        self.reset_status()
        for view_index in list(self.body_history.keys()):
            if view_index > self.current_view:
                del self.body_history[view_index]
        self.current_view += 1
        self.body_history[self.current_view] = body
        return self._set_body(body)

    def _set_body(self, body):
        views = list(self.body_history.values())[0:self.current_view]
        # self.nav_position.set_text(" →  ".join([entry.title for entry in views]))
        self.reset_status()
        return super().set_body(body)

    def refresh(self):
        self.body_history[self.current_view].refresh()
        self.body._invalidate()

