#!/usr/bin/python
# -*- coding: utf-8 -*-

# Urwid SàT extensions
# Copyright (C) 2009-2016 Jérôme Poisson (goffi@goffi.org)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urwid
from . import sat_widgets
import os, os.path
from xml.dom import minidom
import logging as log
from time import time
from .keys import action_key_map as a_key

import gettext
gettext.install('urwid_satext', str=True)

class PathEdit(sat_widgets.AdvancedEdit):
    """AdvancedEdit with manage file paths"""

    def keypress(self, size, key):
        if key == '~' and self.edit_pos==0:
            expanded = os.path.expanduser('~')
            self.set_edit_text(os.path.normpath(expanded+'/'+self.edit_text))
            self.set_edit_pos(len(expanded)+1)
        elif key == a_key['EDIT_DELETE_LAST_WORD']:
            if self.edit_pos<2:
                return
            before = self.edit_text[:self.edit_pos]
            pos = (before[:-1] if before.endswith('/') else before).rfind("/")+1
            self.set_edit_text(before[:pos] + self.edit_text[self.edit_pos:])
            self.set_edit_pos(pos)
            return
        else:
            return super(PathEdit, self).keypress(size, key)

class FilesViewer(urwid.WidgetWrap):
    """List specialised for files"""

    def __init__(self, onPreviousDir, onDirClick, onFileClick = None):
        self.path=''
        self.key_cache = ''
        self.key_time = time()
        self.onPreviousDir = onPreviousDir
        self.onDirClick = onDirClick
        self.onFileClick = onFileClick
        self.files_list = urwid.SimpleListWalker([])
        self.show_hidden = True
        listbox = urwid.ListBox(self.files_list)
        urwid.WidgetWrap.__init__(self, listbox)

    def keypress(self, size, key):
        if key==a_key['FILES_HIDDEN_HIDE']:
            #(un)hide hidden files
            self.show_hidden = not self.show_hidden
            self.showDirectory(self.path)
        elif key==a_key['FILES_JUMP_DIRECTORIES']:
            #jump to directories
            if self.files_list:
                self._w.set_focus(0)
        elif key==a_key['FILES_JUMP_FILES']:
            for idx in range(len(self.files_list)):
                if isinstance(self.files_list[idx].base_widget,urwid.Divider):
                    if idx<len(self.files_list)-1:
                        self._w.set_focus(idx+1)
                    break
        elif len(key) == 1:
            if time() - self.key_time > 2:
                self.key_cache=key
            else:
                self.key_cache+=key
            self.key_time = time()
            for idx in range(len(self.files_list)):
                if isinstance(self.files_list[idx],sat_widgets.ClickableText) and self.files_list[idx].get_text().lower().startswith(self.key_cache.lower()):
                    self._w.set_focus(idx)
                    break
        else:
            return self._w.keypress(size, key)

    def showDirectory(self, path):
        self.path = path
        del self.files_list[:]
        directories = []
        files = []
        try:
            for filename in os.listdir(path):
                if not isinstance(filename, str):
                    log.warning("file [{}] has a badly encode filename, ignoring it".format(filename.decode('utf-8', 'replace')))
                    continue
                fullpath = os.path.join(path,filename)
                if os.path.isdir(fullpath):
                    directories.append(filename)
                else:
                    files.append(filename)
        except OSError:
           self.files_list.append(urwid.Text(("warning",_("Impossible to list directory")),'center'))
        directories.sort()
        files.sort()
        if os.path.abspath(path)!='/' and os.path.abspath(path) != '//':
            previous_wid = sat_widgets.ClickableText(('directory','..'))
            urwid.connect_signal(previous_wid,'click',self.onPreviousDir)
            self.files_list.append(previous_wid)
        for directory in directories:
            if directory.startswith('.') and not self.show_hidden:
                continue
            dir_wid = sat_widgets.ClickableText(('directory',directory))
            urwid.connect_signal(dir_wid,'click',self.onDirClick)
            self.files_list.append(dir_wid)
        self.files_list.append(urwid.AttrMap(urwid.Divider('-'),'separator'))
        for filename in files:
            if filename.startswith('.') and not self.show_hidden:
                continue
            file_wid = sat_widgets.ClickableText(filename)
            if self.onFileClick:
                urwid.connect_signal(file_wid,'click',self.onFileClick)
            self.files_list.append(file_wid)


class FileDialog(urwid.WidgetWrap):

    def __init__(self, ok_cb, cancel_cb, message=None, title=_("Please select a file"), style=[]):
        """Create file dialog

        @param title: title of the window/popup
        @param message: message to display, or None to only show title and file dialog
            message will be passed to a Text widget, so markup can be used
        @param style: list of string:
            - 'dir' if a dir path must be selected
        """
        self.ok_cb = ok_cb
        self._type = 'dir' if 'dir' in style else 'normal'
        self.__home_path = os.path.expanduser('~')
        widgets = []
        if message:
            widgets.append(urwid.Text(message))
            widgets.append(urwid.Divider('─'))
        self.path_wid = PathEdit(_('Path: '))
        self.path_wid.setCompletionMethod(self._directory_completion)
        urwid.connect_signal(self.path_wid, 'change', self.onPathChange)
        widgets.append(self.path_wid)
        widgets.append(urwid.Divider('─'))
        header = urwid.Pile(widgets)
        bookm_list = urwid.SimpleListWalker([])
        self.bookmarks = list(self.getBookmarks())
        self.bookmarks.sort()
        for bookmark in self.bookmarks:
            if bookmark.startswith(self.__home_path):
                bookmark="~"+bookmark[len(self.__home_path):]
            book_wid = sat_widgets.ClickableText(bookmark)
            urwid.connect_signal(book_wid, 'click', self.onBookmarkSelected)
            bookm_list.append(book_wid)
        bookm_wid = urwid.Frame(urwid.ListBox(bookm_list), urwid.AttrMap(urwid.Text(_('Bookmarks'),'center'),'title'))
        self.files_wid = FilesViewer(self.onPreviousDir, self.onDirClick, self.onFileClick if self._type == 'normal' else None)
        center_row = urwid.Columns([('weight',2,bookm_wid),
                     ('weight',8,sat_widgets.VerticalSeparator(self.files_wid))])

        buttons = []
        if self._type == 'dir':
            buttons.append(sat_widgets.CustomButton(_('Ok'), self._validateDir))
        buttons.append(sat_widgets.CustomButton(_('Cancel'),cancel_cb))
        max_len = max([button.getSize() for button in buttons])
        buttons_wid = urwid.GridFlow(buttons,max_len,1,0,'center')
        main_frame = sat_widgets.FocusFrame(center_row, header, buttons_wid)
        decorated = sat_widgets.LabelLine(main_frame, sat_widgets.SurroundedText(title))
        urwid.WidgetWrap.__init__(self, decorated)
        self.path_wid.set_edit_text(os.getcwd())

    def _validateDir(self, wid):
        """ call ok callback if current path is a dir """
        path = os.path.abspath(self.path_wid.get_edit_text())
        if os.path.isdir(path):
            self.ok_cb(path)

    def _directory_completion(self, path, completion_data):
        assert isinstance(path, str)
        path=os.path.abspath(path)
        if not os.path.isdir(path):
            head,dir_start = os.path.split(path)
        else:
            head=path
            dir_start=''
        try:
            filenames = os.listdir(head)
            to_remove = []

            # we remove badly encoded files
            for filename in filenames:
                if not isinstance(filename, str):
                    log.warning("file [{}] has a badly encode filename, ignoring it".format(filename.decode('utf-8', 'replace')))
                    to_remove.append(filename)
            for filename in to_remove:
                filenames.remove(filename)

            filenames.sort()
            try:
                start_idx=filenames.index(completion_data['last_dir'])+1
                if start_idx == len(filenames):
                    start_idx = 0
            except (KeyError,ValueError):
                start_idx = 0
            for idx in list(range(start_idx,len(filenames))) + list(range(0,start_idx)):
                full_path = os.path.join(head,filenames[idx])
                if filenames[idx].lower().startswith(dir_start.lower()) and os.path.isdir(full_path):
                    completion_data['last_dir'] = filenames[idx]
                    return full_path
        except OSError:
            pass
        return path

    def getBookmarks(self):
        gtk_bookm = os.path.expanduser("~/.gtk-bookmarks")
        kde_bookm = os.path.expanduser("~/.kde/share/apps/kfileplaces/bookmarks.xml")
        bookmarks = set()
        try:
            with open(gtk_bookm) as gtk_fd:
                for bm in gtk_fd.readlines():
                    if bm.startswith("file:///"):
                        bookmarks.add(bm[7:].replace('\n','').decode('utf-8', 'replace'))
        except IOError:
            log.info(_('No GTK bookmarks file found'))
            pass

        try:
            dom = minidom.parse(kde_bookm)
            for elem in dom.getElementsByTagName('bookmark'):
                bm = elem.getAttribute("href")
                if bm.startswith("file:///"):
                    bookmarks.add(bm[7:].decode('utf-8', 'replace'))
        except IOError:
            log.info(_('No KDE bookmarks file found'))
            pass

        return bookmarks

    def onBookmarkSelected(self, button):
        self.path_wid.set_edit_text(os.path.expanduser(button.get_text()))

    def onPathChange(self, edit, path):
        if os.path.isdir(path):
            self.files_wid.showDirectory(path)

    def onPreviousDir(self, wid):
        path = os.path.abspath(self.path_wid.get_edit_text())
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        self.path_wid.set_edit_text(os.path.split(path)[0])

    def onDirClick(self, wid):
        path = os.path.abspath(self.path_wid.get_edit_text())
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        self.path_wid.set_edit_text(os.path.join(path,wid.get_text()))

    def onFileClick(self, wid):
        self.ok_cb(os.path.abspath(os.path.join(self.files_wid.path,wid.get_text())))
