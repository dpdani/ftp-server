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
import logging as log
import encodings
utf8decode = lambda s: str(s)

import uuid

import collections

from urwid.util import is_mouse_press #XXX: is_mouse_press is not included in urwid in 1.0.0
from .keys import action_key_map as a_key

FOCUS_KEYS = (a_key['FOCUS_SWITCH'], a_key['FOCUS_UP'], a_key['FOCUS_DOWN'])


def getFocusDirection(key, inversed=False):
    """Return direction and rotate boolean depending on key
    @param key: one of FOCUS_KEYS
    @param inversed: inverse directions if True
    @return (tuple): (direction, rotate) where
        - direction is 1 or -1
        - rotate is False if we should stop at the begin/end of the widgets list
    """
    if not inversed:
        direction = 1 if key in (a_key['FOCUS_SWITCH'], a_key['FOCUS_UP']) else -1
    else:
        direction = -1 if key in (a_key['FOCUS_SWITCH'], a_key['FOCUS_UP']) else 1
    rotate = key == a_key['FOCUS_SWITCH']
    return direction, rotate


class AdvancedEdit(urwid.Edit):
    """Edit box with some custom improvments
    new chars:
              - C-a: like 'home'
              - C-e: like 'end'
              - C-k: remove everything on the right of the cursor
              - C-w: remove the word on the back
    new behaviour: emit a 'click' signal when enter is pressed"""
    signals = urwid.Edit.signals + ['click']

    def getValue(self):
        return self.get_edit_text()

    def setCompletionMethod(self, callback):
        """Define method called when completion is asked

        @callback: method with 2 arguments:
                    - the text to complete (part after cursor position is ignored)
                    - if there was already a completion, a dict with
                        - 'completed':last completion
                        - 'completion_pos': cursor position where the completion starts
                        - 'position': last completion cursor position
                      this dict must be used (and can be filled) to find next completion)
                   and which return the full text completed
        """
        self.completion_cb = callback
        self.completion_data = {}

    def keypress(self, size, key):
        #TODO: insert mode is not managed yet
        if key == a_key['EDIT_HOME']:
            key = 'home'
        elif key == a_key['EDIT_END']:
            key = 'end'
        elif key == a_key['EDIT_DELETE_TO_END']:
            self._delete_highlighted()
            self.set_edit_text(self.edit_text[:self.edit_pos])
        elif key == a_key['EDIT_DELETE_LAST_WORD']:
            before = self.edit_text[:self.edit_pos]
            pos = before.rstrip().rfind(" ")+1
            self.set_edit_text(before[:pos] + self.edit_text[self.edit_pos:])
            self.set_edit_pos(pos)
        elif key == a_key['EDIT_ENTER']:
            self._emit('click')
        elif key == a_key['EDIT_COMPLETE']:
            try:
                before = self.edit_text[:self.edit_pos]
                if self.completion_data:
                    if (not self.completion_data['completed']
                        or self.completion_data['position'] != self.edit_pos
                        or not before.endswith(self.completion_data['completed'])):
                        self.completion_data.clear()
                    else:
                        before = before[:-len(self.completion_data['completed'])]
                complet = self.completion_cb(before, self.completion_data)
                self.completion_data['completed'] = complet[len(before):]
                self.set_edit_text(complet+self.edit_text[self.edit_pos:])
                self.set_edit_pos(len(complet))
                self.completion_data['position'] = self.edit_pos
                return
            except AttributeError:
                #No completion method defined
                pass
        return super(AdvancedEdit, self).keypress(size, key)


class Password(AdvancedEdit):
    """Edit box which doesn't show what is entered (show '*' or other char instead)"""

    def __init__(self, *args, **kwargs):
        """Same args than Edit.__init__ with an additional keyword arg 'hidden_char'
        @param hidden_char: char to show instead of what is actually entered: default '*'
        """
        self.hidden_char=kwargs['hidden_char'] if 'hidden_char' in kwargs else '*'
        self.__real_text=''
        super(Password, self).__init__(*args, **kwargs)

    def set_edit_text(self, text):
        self.__real_text = text
        hidden_txt = len(text)*'*'
        super(Password, self).set_edit_text(hidden_txt)

    def get_edit_text(self):
        return self.__real_text

    def insert_text(self, text):
        self._edit_text = self.__real_text
        super(Password,self).insert_text(text)

    def render(self, size, focus=False):
        return super(Password, self).render(size, focus)


class ModalEdit(AdvancedEdit):
    """AdvancedEdit with vi-like mode management
    - there is a new 'mode' property which can be changed with properties
    specified during init
    - completion callback received a new 'mode' argument
    """

    def __init__(self, modes, *args, **kwargs):
        """ first argument is "modes", others are the same paramaters as AdvancedEdit
        @param modes: dictionnary in the form:
                      'key_to_change_mode': ('Mode', caption)
                      e.g.: 'i': ('INSERTION', '> ')
                      There *MUST* be a None key (for NORMAL mode)"""
        assert(isinstance(modes, dict) and None in modes)
        self._modes = modes
        super(ModalEdit, self).__init__(*args, **kwargs)
        self.mode = self._modes[None][0]

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        mode_key = None
        for key in self._modes:
            if self._modes[key][0] == value:
                mode_key = key
                break

        mode, caption = self._modes[mode_key]
        self._mode = mode
        self.set_caption(caption)
        if not mode_key: #we are in NORMAL mode
            self.set_edit_text('')

    def setCompletionMethod(self, callback):
        """ Same as AdvancedEdit.setCompletionMethod, but with a third argument: current mode"""
        super(ModalEdit, self).setCompletionMethod(lambda text,data: callback(text, data, self._mode))

    def keypress(self, size, key):
        if key == a_key['MODAL_ESCAPE']:
            self.mode = "NORMAL"
            return
        if self._mode == 'NORMAL' and key in self._modes:
            self.mode = self._modes[key][0]
            return
        return super(ModalEdit, self).keypress(size, key)


class SurroundedText(urwid.Widget):
    """Text centered on a repeated character (like a Divider, but with a text in the center)"""
    _sizing = frozenset(['flow'])

    def __init__(self,text,car=utf8decode('─')):
        self.text=text
        self.car=car

    def rows(self,size,focus=False):
        return self.display_widget(size, focus).rows(size, focus)

    def render(self, size, focus=False):
        return self.display_widget(size, focus).render(size, focus)

    def display_widget(self, size, focus):
        (maxcol,) = size
        middle = (maxcol-len(self.text))/2
        render_text = middle * self.car + self.text + (maxcol - len(self.text) - middle) * self.car
        return urwid.Text(render_text)


class AlwaysSelectableText(urwid.WidgetWrap):
    """Text which can be selected with space"""
    signals = ['change']

    def __init__(self, text, align='left', header='', focus_attr='default_focus', selected_text=None, selected=False, data=None):
        """
        @param text: same as urwid.Text's text parameter
        @param align: same as urwid.Text's align parameter
        @select_attr: attrbute to use when selected
        @param selected: is the text selected ?
        """
        self.focus_attr = focus_attr
        self._selected = False
        self._was_focused = False
        self.header = header
        self.text = text
        urwid.WidgetWrap.__init__(self, urwid.Text("",align=align))
        self.setSelectedText(selected_text)
        self.setState(selected)

    def getValue(self):
        if isinstance(self.text,str):
            return self.text
        list_attr = self.text if isinstance(self.text, list) else [self.text]
        txt = ""
        for attr in list_attr:
            if isinstance(attr,tuple):
                txt+=attr[1]
            else:
                txt+=attr
        return txt

    def get_text(self):
        """for compatibility with urwid.Text"""
        return self.getValue()

    def set_text(self, text):
        """/!\ set_text doesn't change self.selected_txt !"""
        self.text = text
        self.setState(self._selected,invisible=True)

    def setSelectedText(self, text=None):
        """Text to display when selected
        @text: text as in urwid.Text or None for default value"""
        if text == None:
            text = ('selected',self.getValue())
        self.selected_txt = text
        if self._selected:
            self.setState(self._selected)

    def _set_txt(self):
        txt_list = [self.header]
        txt = self.selected_txt if self._selected else self.text
        if isinstance(txt,list):
            txt_list.extend(txt)
        else:
            txt_list.append(txt)
        self._w.base_widget.set_text(txt_list)


    def setState(self, selected, invisible=False):
        """Change state

        @param selected: boolean state value
        @param invisible: don't emit change signal if True
        """
        assert type(selected)==bool
        self._selected=selected
        self._set_txt()
        self._was_focused = False
        self._invalidate()
        if not invisible:
            self._emit("change", self._selected)

    def getState(self):
        return self._selected

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in (a_key['TEXT_SELECT'], a_key['TEXT_SELECT2']):
            self.setState(not self._selected)
        else:
            return key

    def mouse_event(self, size, event, button, x, y, focus):
        if is_mouse_press(event) and button == 1:
            self.setState(not self._selected)
            return True

        return False

    def render(self, size, focus=False):
        attr_list = self._w.base_widget._attrib
        if not focus:
            if self._was_focused:
                self._set_txt()
                self._was_focused = False
        else:
            if not self._was_focused:
                if not attr_list:
                    attr_list.append((self.focus_attr,len(self._w.base_widget.text)))
                else:
                    for idx in range(len(attr_list)):
                        attr,attr_len = attr_list[idx]
                        if attr == None:
                            attr = self.focus_attr
                            attr_list[idx] = (attr,attr_len)
                        else:
                            if not attr.endswith('_focus'):
                                attr+="_focus"
                                attr_list[idx] = (attr,attr_len)
                self._w.base_widget._invalidate()
                self._was_focused = True #bloody ugly hack :)
        return self._w.render(size, focus)


class SelectableText(AlwaysSelectableText):
    """Like AlwaysSelectableText but not selectable when text is empty"""

    def selectable(self):
        return bool(self.text)


class ClickableText(SelectableText):
    signals = SelectableText.signals + ['click']

    def setState(self, selected, invisible=False):
        super(ClickableText,self).setState(False,True)
        if not invisible:
            self._emit('click')


class CustomButton(ClickableText):

    def __init__(self, label, on_press=None, user_data=None, left_border="[ ", right_border=" ]", align="left"):
        self.label = label
        self.left_border = left_border
        self.right_border = right_border
        super(CustomButton, self).__init__([left_border, label, right_border], align=align)
        self.size = len(self.get_text())
        if on_press:
            urwid.connect_signal(self, 'click', on_press, user_data)

    def getSize(self):
        """Return representation size of the button"""
        return self.size

    def get_label(self):
        return self.label[1] if isinstance(self.label,tuple) else self.label

    def set_label(self, label):
        self.label = label
        self.set_text([self.left_border, label, self.right_border])


class ListOption(str):
    """Unicode which manage label and value

    This class similar to unicode, but which make the difference between value and label
    label is show when use as unicode, the .value attribute contain the actual value
    Can be initialised with:
        - basestring (label = value = given string)
        - a tuple with (value, label)
    XXX: comparaison is made against value, not the label which is the one displayed
    """

    def __new__(cls, option):
        if (isinstance(option, cls)):
            return option
        elif isinstance(option, str):
            value = label = option
        elif (isinstance(option, tuple) and len(option) == 2):
            value, label = option
        else:
            raise NotImplementedError
        if not label:
            label = value
        instance = super(ListOption, cls).__new__(cls, label)
        instance._value = value
        return instance

    def __eq__(self, other):
        # XXX: try to compare values, if other has no value
        #      (e.g. unicode string) try to compare to other itself
        try:
            return self._value == other._value
        except AttributeError:
            return self._value == other

    def __ne__(self, other):
        # XXX: see __eq__
        try:
            return self._value != other._value
        except AttributeError:
            return self._value != other

    @property
    def value(self):
        """ return option value """
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @staticmethod
    def fromOptions(options):
        """ convert a list of string/tuple options to a list of listOption
        @param options: list of managed option type (basestring, tuple)
        return: list of ListOption
        """
        return [(ListOption(option)) for option in options]


class UnselectableListBox(urwid.ListBox):
    """List box that can be unselectable if all widget are unselectable and visible"""

    def __init__(self, body):
        super(UnselectableListBox, self).__init__(body)
        self.__size_cache = None

    def selectable(self):
        """Selectable that return False if everything is visible and nothing is selectable"""
        if self.__size_cache is None:
            return self._selectable
        middle, top, bottom = self.calculate_visible(self.__size_cache, self.__focus_cache)
        if top is None or bottom is None:
            return True
        if top[0] or bottom[0]:
            # if not everything is visible, we can select
            return True
        for wid in self.body:
            # if any widget is selectable, we can select
            if wid.selectable():
                return True
        return False

    def render(self, size, focus=False):
        """Call ListBox render, but keep size and focus in cache"""
        self.__size_cache = size
        self.__focus_cache = focus
        return super(UnselectableListBox, self).render(size, focus)


class SimpleListWalkerWithCb(urwid.SimpleListWalker):
    """a SimpleListWalker which call callbacks on items changes"""

    def __init__(self, contents, on_new=None, on_delete=None):
        """
        @param contents: list to copy into this object
        @param on_new: callback to call when an item is added
        @param on_delete: callback to call when an item is deleted
        """
        # XXX: we can't use modified signal as it doesn't return the modified item
        super(SimpleListWalkerWithCb, self).__init__(contents)
        for content in contents:
            on_new(content)
        self._on_new = on_new
        self._on_delete = on_delete

    def __cbSingle(self, item, cb):
        try:
            cb(item)
        except TypeError:
            pass

    def __cbMulti(self, items, cb):
        if cb is not None:
            for item in items:
                    cb(item)

    def __add__(self, new_list):
        self.__cbMulti(new_list, self._on_new)
        return super(SimpleListWalkerWithCb, self).__add__(new_list)

    def __delitem__(self, item):
        self.__cbSingle(item, self._on_delete)
        return super(SimpleListWalkerWithCb, self).__delitem__(item)

    def __delslice__(self, i,j):
        items = super(SimpleListWalkerWithCb, self).__getslice__(i,j)
        self.__cbMulti(items, self._on_delete)
        return super(SimpleListWalkerWithCb, self).__delslice(i,j)

    def __iadd__(self, y):
        raise NotImplementedError

    def __imul__(self, y):
        raise NotImplementedError

    def  __mul__(self, n):
        raise NotImplementedError

    def  __rmul__(self, n):
        raise NotImplementedError

    def __setitem__(self, i, y):
        parent = super()
        self.__cbSingle(y, self._on_new)
        to_delete = parent.__getitem__(i)
        self.__cbSingle(to_delete, self._on_delete)
        return parent.__setitem__(i, y)

    def __setslice__(self, i, j, y):
        parent = super(SimpleListWalkerWithCb, self)
        items_to_delete = parent.__getslice__(i,j)
        self.__cbMulti(items_to_delete, self._on_delete)
        if hasattr(y, '__iter__'):
            self.__cbMulti(y, self._on_new)
        else:
            self.__cbSingle(y, self._on_new)
        return parent.__setslice__(i, j, y)

    def append(self, obj):
        self.__cbSingle(obj, self._on_new)
        return super(SimpleListWalkerWithCb, self).append(obj)

    def extend(self, it):
        self.__cbMulti(it, self.__on_new)
        return super(SimpleListWalkerWithCb, self).extend(it)

    def insert(self, idx, obj):
        self.__cbSingle(obj, self.__on_new)
        return super(SimpleListWalkerWithCb, self).insert(idx, obj)

    def pop(self, idx=None):
        if idx is None:
            idx=len(self)-1

        parent = super(SimpleListWalkerWithCb, self)
        to_remove = parent.__getitem__(idx)
        self.__cbSingle(to_remove, self._on_delete)
        return parent.pop(idx)

    def remove(self, val):
        ret = super(SimpleListWalkerWithCb, self).remove(val)
        self.__cbSingle(val, self._on_delete)
        return ret


class GenericList(urwid.ListBox):
    signals = ['click','change']

    def __init__(self, options, style=None, align='left', option_type = SelectableText, on_click=None, on_change=None, user_data=None):
        """Widget managing list of string and their selection

        @param options: list of strings used for options
        @param style: list of string:
            - 'single' if only one must be selected
            - 'no_first_select' nothing selected when list is first displayed
            - 'can_select_none' if we can select nothing
        @param align: alignement of text inside the list
        @param option_type: callable (usually a class) which will be called with:
            - option as first argument
            - align=align as keyword argument
        @param on_click: method called when click signal is emited
        @param on_change: method called when change signal is emited
        @param user_data: data sent to the callback for click signal
        """
        if style is None:
            style = []
        self.single = 'single' in style
        self.no_first_select = 'no_first_select' in style
        self.can_select_none = 'can_select_none' in style
        self.align = align
        self.option_type = option_type
        self.first_display = True

        if on_click:
            urwid.connect_signal(self, 'click', on_click, user_data)

        if on_change:
            urwid.connect_signal(self, 'change', on_change, user_data)

        self.content = SimpleListWalkerWithCb([], self._addSignals, lambda widget: self._emit('change'))
        super(GenericList, self).__init__(self.content)
        self.changeValues(options)

    def _addSignals(self, widget):
        for signal, callback in (('change', self._onStateChange), ('click', self._onClick)):
            try:
                urwid.connect_signal(widget, signal, callback)
            except NameError:
                pass #the widget given doesn't support the signal

    @property
    def contents(self):
        return self.content

    def _onStateChange(self, widget, selected, *args):
        if self.single:
            if not selected and not self.can_select_none:
                #if in single mode, it's forbidden to unselect a value
                widget.setState(True, invisible=True)
                return
            if selected:
                self.unselectAll(invisible=True)
                widget.setState(True, invisible=True)
        self._emit("change", widget, selected, *args)

    def _onClick(self, widget, *args):
        if widget not in self.content:
            urwid.disconnect_signal(widget, "click", self._onClick)
            return
        self._emit("click", widget, *args)

    def unselectAll(self, invisible=False):
        for widget in self.content:
            if widget.getState():
                widget.setState(False, invisible)
                widget._invalidate()

    def deleteValue(self, value):
        """Delete the first value equal to the param given"""
        for widget in self.content:
            if widget.getValue() == value:
                self.content.remove(widget)
                self._emit('change')
                return
        raise ValueError("%s ==> %s" %  (str(value),str(self.content)))

    def getSelectedValue(self):
        """Convenience method to get the value selected as a string in single mode, or None"""
        values = self.getSelectedValues()
        return values[0] if values else None

    def getAllValues(self):
        """Return values of all items"""
        return [widget.getValue() for widget in self.content]

    def getSelectedValues(self):
        """Return values of selected items"""
        result = []
        for widget in self.content:
            if widget.getState():
                result.append(widget.getValue())
        return result

    def changeValues(self, new_values):
        """Change all values in one shot"""
        new_values = ListOption.fromOptions(new_values)
        if not self.first_display:
            old_selected = self.getSelectedValues()
        widgets = []
        for option in new_values:
            widget = self.option_type(option, align=self.align)
            if not self.first_display and option in old_selected:
                widget.setState(True)
            widgets.append(widget)
        self.content[:] = widgets
        if self.first_display and self.single and new_values and not self.no_first_select:
            self.content[0].setState(True)
        self._emit('change')
        self.first_display = False

    def selectValue(self, value, move_focus=True):
        """Select the first item which has the given value.

        @param value
        @param move_focus (bool):
            - True to move the focus on the selected value,
            - False to leave the focus position unchanged.

        """
        self.unselectAll()
        idx = 0
        for widget in self.content:
            if widget.getValue() == value:
                widget.setState(True)
                if move_focus:
                    self.focus_position = idx
                return
            idx+=1

    def selectValues(self, values, move_focus=True):
        """Select all the given values.

        @param values [set, list]
        @param move_focus (boolean): True to move the focus on the last selected value,
                                     False to leave the focus position unchanged.
        """
        if self.single:
            if values:
                self.selectValue(values[-1], move_focus)
            return
        self.unselectAll()
        for value in values:
            idx = 0
            for widget in self.content:
                if widget.getValue() == value:
                    widget.setState(True)
                    if move_focus:
                        self.focus_position = idx
                idx += 1


class List(urwid.Widget):
    """FlowWidget list, same arguments as GenericList, with an additional one 'max_height'"""
    signals = ['click','change']
    _sizing = frozenset(['flow'])

    def __init__(self, options, style=None, max_height=5, align='left', option_type = SelectableText, on_click=None, on_change=None, user_data=None):
        if style is None:
            style = []
        self.genericList = GenericList(options, style, align, option_type, on_click, on_change, user_data)
        urwid.connect_signal(self.genericList, 'change', lambda *args: self._emit('change'))
        self.max_height = max_height

    @property
    def contents(self):
        return self.genericList.content

    def selectable(self):
        return True

    def get_cursor_coords(self, size):
        return self.genericList.get_cursor_coords((size[0], self._getHeight(size, True)))

    def keypress(self, size, key):
        return self.displayWidget(size,True).keypress(size, key)

    def unselectAll(self, invisible=False):
        return self.genericList.unselectAll(invisible)

    def deleteValue(self, value):
        return self.genericList.deleteValue(value)

    def getSelectedValue(self):
        return self.genericList.getSelectedValue()

    def getAllValues(self):
        return self.genericList.getAllValues()

    def getSelectedValues(self):
        return self.genericList.getSelectedValues()

    def changeValues(self, new_values):
        return self.genericList.changeValues(new_values)

    def selectValue(self, value, move_focus=True):
        return self.genericList.selectValue(value, move_focus)

    def selectValues(self, values, move_focus=True):
        return self.genericList.selectValues(values, move_focus)

    def render(self, size, focus=False):
        return self.displayWidget(size, focus).render(size, focus)

    def rows(self, size, focus=False):
        return self.displayWidget(size, focus).rows(size, focus)

    def _getHeight(self, size, focus):
        list_size = sum([wid.rows(size, focus) for wid in self.genericList.content])
        height = min(list_size,self.max_height) or 1
        return height

    def displayWidget(self, size, focus):
        return urwid.BoxAdapter(self.genericList, self._getHeight(size, focus))


## MISC ##

class NotificationBar(urwid.WidgetWrap):
    """Bar used to show misc information to user"""
    signals = ['change']

    def __init__(self):
        self.waitNotifs = urwid.Text('')
        self.message = ClickableText('')
        urwid.connect_signal(self.message, 'click', lambda wid: self.showNext())
        self.progress = ClickableText('')
        self.columns = urwid.Columns([('fixed',6,self.waitNotifs),self.message,('fixed',4,self.progress)])
        urwid.WidgetWrap.__init__(self, urwid.AttrMap(self.columns,'notifs'))
        self.notifs = []

    def _modQueue(self):
        """must be called each time the notifications queue is changed"""
        self.waitNotifs.set_text(('notifs',"(%i)" % len(self.notifs) if self.notifs else ''))
        self._emit('change')

    def setProgress(self,percentage):
        """Define the progression to show on the right side of the bar"""
        if percentage == None:
            self.progress.set_text('')
        else:
            self.progress.set_text(('notifs','%02i%%' % percentage))
            if self.columns.focus != self.progress:
                self.columns.focus_position = len(self.columns.contents)-1
        self._emit('change')

    def addPopUp(self, pop_up_widget):
        """Add a popup to the waiting queue"""
        self.notifs.append(('popup',pop_up_widget))
        self._modQueue()

    def removePopUp(self, pop_up_widget):
        """Remove a popup from the waiting queue"""
        for idx, (wid_type, widget) in enumerate(self.notifs):
            if widget == pop_up_widget:
                del self.notifs[idx]
                self._modQueue()
                return

        raise ValueError("trying to remove an unknown pop_up_widget")

    def addMessage(self, message):
        "Add a message to the notificatio bar"
        if not self.message.get_text():
            self.message.set_text(('notifs',message))
            self._invalidate()
            self._emit('change')
        else:
            self.notifs.append(('message',message))
            self._modQueue()

    def showNext(self):
        """Show next message if any, else delete current message"""
        found = None
        for notif in self.notifs:
            if notif[0] == "message":
                found = notif
                break
        if found:
            self.notifs.remove(found)
            self.message.set_text(('notifs',found[1]))
            self._modQueue()
            self.focus_possition = 1
        else:
            self.message.set_text('')
            self._emit('change')

    def getNextPopup(self):
        """Return next pop-up and remove it from the queue
        @return: pop-up or None if there is no more in the queue"""
        ret = None
        for notif in self.notifs:
            if notif[0] == 'popup':
                ret = notif[1]
                break
        if ret:
            self.notifs.remove(notif)
            self._modQueue()
        return ret

    def isQueueEmpty(self):
        return not bool(self.notifs)

    def canHide(self):
        """Return True if there is no important information to show"""
        return self.isQueueEmpty() and not self.message.get_text() and not self.progress.get_text()


class MenuBox(urwid.WidgetWrap):
    """Show menu items of a category in a box"""
    signals = ['click']

    def __init__(self,parent,items):
        self.parent = parent
        self.selected = None
        content = urwid.SimpleListWalker([ClickableText(('menuitem',text)) for text in items])
        for wid in content:
            urwid.connect_signal(wid, 'click', self.onClick)

        self.listBox = urwid.ListBox(content)
        menubox = urwid.LineBox(urwid.BoxAdapter(self.listBox,len(items)))
        urwid.WidgetWrap.__init__(self,menubox)

    def getValue(self):
        return self.selected

    def keypress(self, size, key):
        if key==a_key['MENU_BOX_UP']:
            if self.listBox.get_focus()[1] == 0:
                self.parent.keypress(size, key)
        elif key in (a_key['MENU_BOX_LEFT'], a_key['MENU_BOX_RIGHT']):
            self.parent.keypress(size,'up')
            self.parent.keypress(size,key)
        return super(MenuBox,self).keypress(size,key)

    def mouse_event(self, size, event, button, x, y, focus):
        if button == 3:
            self.parent.keypress(size,'up')
            return True
        return super(MenuBox,self).mouse_event(size, event, button, x, y, focus)

    def onClick(self, wid):
        self.selected = wid.getValue()
        self._emit('click')


class Menu(urwid.WidgetWrap):

    def __init__(self,loop, x_orig=0):
        """Menu widget
        @param loop: main loop of urwid
        @param x_orig: absolute start of the abscissa
        """
        self.loop = loop
        self.menu_keys = []
        self.menu = {}
        self.x_orig = x_orig
        self.shortcuts = {} #keyboard shortcuts
        self.save_bottom = None
        col_rol = ColumnsRoller()
        urwid.WidgetWrap.__init__(self, urwid.AttrMap(col_rol,'menubar'))

    def selectable(self):
        return True

    def getMenuSize(self):
        """return the current number of categories in this menu"""
        return len(self.menu_keys)

    def setOrigX(self, orig_x):
        self.x_orig = orig_x

    def __buildOverlay(self, menu_key, columns):
        """Build the overlay menu which show menuitems
        @param menu_key: name of the category
        @param columns: column number where the menubox must be displayed"""
        max_len = 0
        for item in self.menu[menu_key]:
            if len(item[0]) > max_len:
                max_len = len(item[0])

        self.save_bottom = self.loop.widget
        menu_box = MenuBox(self,[item[0] for item in self.menu[menu_key]])
        urwid.connect_signal(menu_box, 'click', self.onItemClick)

        self.loop.widget = urwid.Overlay(urwid.AttrMap(menu_box,'menubar'),self.save_bottom,('fixed left', columns),max_len+2,('fixed top',1),None)

    def keypress(self, size, key):
        if key == a_key['MENU_DOWN']:
            key = 'enter'
        elif key == a_key['MENU_UP']:
            if  self.save_bottom:
                self.loop.widget = self.save_bottom
                self.save_bottom = None

        return self._w.base_widget.keypress(size, key)

    def checkShortcuts(self, key):
        for shortcut in list(self.shortcuts.keys()):
            if key == shortcut:
                category, item, callback = self.shortcuts[shortcut]
                callback((category, item))
        return key

    def addMenu(self, category, item=None, callback=None, shortcut=None):
        """Create the category if new and add a menu item (if item is not None).

        @param category: category of the menu (e.g. File/Edit)
        @param item: menu item (e.g. new/close/about)
        @callback: method to call when item is selected"""
        if not category in list(self.menu.keys()):
            self.menu_keys.append(category)
            self.menu[category] = []
            button = CustomButton(('menubar',category), self.onCategoryClick,
                                   left_border = ('menubar',"[ "),
                                   right_border = ('menubar'," ]"))
            self._w.base_widget.addWidget(button,button.getSize())
        if not item:
            return
        self.menu[category].append((item, callback))
        if shortcut:
            assert(shortcut not in list(self.shortcuts.keys()))
            self.shortcuts[shortcut] = (category, item, callback)

    def onItemClick(self, widget):
        category = self._w.base_widget.getSelected().get_label()
        item = widget.getValue()
        callback = None
        for menu_item in self.menu[category]:
            if item == menu_item[0]:
                callback = menu_item[1]
                break
        if callback:
            self.keypress(None, a_key['MENU_UP'])
            callback((category, item))

    def onCategoryClick(self, button):
        self.__buildOverlay(button.get_label(),
                            self.x_orig + self._w.base_widget.getStartCol(button))

MenuItem = collections.namedtuple('MenuItem', ('name', 'widget'))

class MenuRoller(urwid.WidgetWrap):

    def __init__(self, menus_list):
        """Create a MenuRoller

        @param menus_list: list of tuples which can be either:
            - (name, Menu instance)
            - (name, Menu instance, id)
        """
        assert menus_list
        self.selected = None
        self.menu_items = collections.OrderedDict()

        self.columns = urwid.Columns([urwid.Text(''),urwid.Text('')])
        urwid.WidgetWrap.__init__(self, self.columns)

        for menu_tuple in menus_list:
            try:
                name, menu, id_ = menu_tuple
            except ValueError:
                name, menu = menu_tuple
                id_ = None
            self.addMenu(name, menu, id_)

    def _showSelected(self):
        """show menu selected"""
        if self.selected is None:
            self.columns.contents[0] = (urwid.Text(''), ('given', 0, False))
            self.columns.contents[1] = (urwid.Text(''), ('weight', 1, False))
        else:
            menu_item = self.menu_items[self.selected]
            name_txt = '\u21c9 ' + menu_item.name + ' \u21c7 '
            current_name = ClickableText(name_txt)
            name_len = len(name_txt)
            current_menu = menu_item.widget
            current_menu.setOrigX(name_len)
            self.columns.contents[0] = (current_name, ('given', name_len, False))
            self.columns.contents[1] = (current_menu, ('weight', 1, False))

    def keypress(self, size, key):
        menu_ids = list(self.menu_items.keys())
        try:
            idx = menu_ids.index(self.selected)
        except ValueError:
            return super(MenuRoller, self).keypress(size, key)

        if key==a_key['MENU_ROLLER_UP']:
            if self.columns.get_focus_column()==0:
                if idx > 0:
                    self.selected = menu_ids[idx-1]
                    self._showSelected()
                return
        elif key==a_key['MENU_ROLLER_DOWN']:
            if self.columns.get_focus_column()==0:
                if idx < len(menu_ids)-1:
                    self.selected = menu_ids[idx+1]
                    self._showSelected()
                return
        elif key==a_key['MENU_ROLLER_RIGHT']:
            if self.columns.get_focus_column()==0 and \
                (isinstance(self.columns.contents[1][0], urwid.Text) or \
                self.menu_items[self.selected].widget.getMenuSize()==0):
                return #if we have no menu or the menu is empty, we don't go the right column

        return super(MenuRoller, self).keypress(size, key)

    def addMenu(self, name, widget, menu_id=None):
        """Add a menu

        @param name: name of the menu to add, it name already exists, menu is not added
        @param widget: instance of Menu
        @param menu_id: id to use of this menu, or None to generate
        @return: menu_id
        """
        names = {menu_item.name: id_ for id_, menu_item in self.menu_items.items()}

        if name not in names:
            id_ = menu_id or str(uuid.uuid4())
            if id_ in self.menu_items:
                raise ValueError('Conflict: the id [{}] is already used'.format(id_))
            self.menu_items[id_] = MenuItem(name, widget)
        else:
            id_ = names[name]
            menu_item = self.menu_items[id_]
            if menu_item.widget is not widget:
                raise ValueError("The menu with id [{}] exists and doesn't contain the given instance. Use replaceMenu if you want to change the menu.".format(id_))
        if self.selected is None:
            self.selected = id_
            self._showSelected()
        return id_

    def replaceMenu(self, name, widget, menu_id):
        """Add a menu or replace it if the id already exists

        @param name: name of the menu to add, it name already exists, menu is not added
        @param widget: instance of Menu
        @param menu_id: id or the menu
        """
        assert menu_id is not None
        if menu_id in self.menu_items:
            del self.menu_items[menu_id]
        self.addMenu(name, widget, menu_id)
        if self.selected == menu_id:
            self._showSelected() #if we are on the menu, we update it

    def removeMenu(self, menu_id):
        del self.menu_items[menu_id]
        if self.selected == menu_id:
            try:
                self.selected = next(iter(self.menu_items.keys()))
            except StopIteration:
                self.selected = None
            self._showSelected()

    def checkShortcuts(self, key):
        for menu_item in list(self.menu_items.values()):
            key = menu_item.widget.checkShortcuts(key)
        return key


## DIALOGS ##

class GenericDialog(urwid.WidgetWrap):

    def __init__(self, widgets_lst, title, style=None, **kwargs):
        if style is None:
            style = []
        frame_header = urwid.AttrMap(urwid.Text(title,'center'),'title')

        self.buttons = collections.OrderedDict()

        if "OK/CANCEL" in style:
            self.buttons['cancel'] = urwid.Button(_("Cancel"), kwargs.get('cancel_cb'), kwargs.get('cancel_value'))
            self.buttons['ok'] = urwid.Button(_("Ok"), kwargs.get('ok_cb'), kwargs.get('ok_value'))
        elif "YES/NO" in style:
            self.buttons['yes'] = urwid.Button(_("Yes"), kwargs.get('yes_cb'), kwargs.get('yes_value'))
            self.buttons['no'] = urwid.Button(_("No"), kwargs.get('no_cb'), kwargs.get('no_value'))
        if "OK" in style:
            self.buttons['ok'] = urwid.Button(_("Ok"), kwargs.get('ok_cb'), kwargs.get('ok_value'))
        if self.buttons:
            buttons_flow = urwid.GridFlow(list(self.buttons.values()), max([len(button.get_label()) for button in self.buttons.values()])+4, 1, 1, 'center')
        body_content = urwid.SimpleListWalker(widgets_lst)
        frame_body = UnselectableListBox(body_content)
        frame = FocusFrame(frame_body, frame_header, buttons_flow if self.buttons else None, 'footer' if self.buttons else 'body')
        decorated_frame = urwid.LineBox(frame)
        urwid.WidgetWrap.__init__(self, decorated_frame)

    def setCallback(self, name, callback, data=None):
        """Set the callback associated with a button press

        @param name: one of "ok", "cancel", "yest", "no"
        @aram callback(callable): method to call on requested action
        @param data: argument to send to the callback (first one will be the button widget)
        @raise KeyError if name is invalid
        """
        button = self.buttons[name]
        urwid.connect_signal(button, 'click', callback, data)


class InputDialog(GenericDialog):
    """Dialog with an edit box"""

    def __init__(self, title, instrucions, style=None, default_txt = '', **kwargs):
        if style is None:
            style = ['OK/CANCEL']
        instr_wid = urwid.Text(instrucions+':')
        edit_box = AdvancedEdit(edit_text=default_txt)
        GenericDialog.__init__(self, [instr_wid,edit_box], title, style, ok_value=edit_box, **kwargs)
        self._w.base_widget.focusposition = 'body'


class ConfirmDialog(GenericDialog):
    """Dialog with buttons for confirm or cancel an action"""

    def __init__(self, title, message=None, style=None, **kwargs):
        if style is None:
            style = ['YES/NO']
        GenericDialog.__init__(self,
                               [urwid.Text(message, 'center')] if message is not None else [],
                               title,
                               style,
                               **kwargs)


class Alert(GenericDialog):
    """Dialog with just a message and a OK button"""

    def __init__(self, title, message, style=None, **kwargs):
        if style is None:
            style= ['OK']
        GenericDialog.__init__(self, [urwid.Text(message, 'center')], title, style, ok_value=None, **kwargs)

## CONTAINERS ##

class ColumnsRoller(urwid.Widget):
    _sizing = frozenset(['flow'])

    def __init__(self, widget_list = None, focus_column=0):
        self.widget_list = widget_list or []
        self.focus_column = focus_column
        self.__start = 0
        self.__next = False

    def addWidget(self, widget, width):
        self.widget_list.append((width,widget))
        if len(self.widget_list) == 1:
            self.focus_position = 0

    def getStartCol(self, widget):
        """Return the column of the left corner of the widget"""
        start_col = 0
        for wid in self.widget_list[self.__start:]:
            if wid[1] == widget:
                return start_col
            start_col+=wid[0]
        return None

    def selectable(self):
        try:
            return self.widget_list[self.focus_column][1].selectable()
        except IndexError:
            return False

    def keypress(self, size, key):
        if key==a_key['COLUMNS_ROLLER_LEFT']:
            if self.focus_column>0:
                self.focus_column-=1
                self._invalidate()
                return
        if key==a_key['COLUMNS_ROLLER_RIGHT']:
            if self.focus_column<len(self.widget_list)-1:
                self.focus_column+=1
                self._invalidate()
                return
        if self.focus_column<len(self.widget_list):
            return self.widget_list[self.focus_column][1].keypress(size,key)
        return key

    def getSelected(self):
        """Return selected widget"""
        return self.widget_list[self.focus_column][1]

    @property
    def focus_position(self):
        return self.focus_column

    @focus_position.setter
    def focus_position(self, idx):
        if idx>len(self.widget_list)-1:
            idx = len(self.widget_list)-1
        self.focus_column = idx

    def rows(self,size,focus=False):
        return 1

    def __calculate_limits(self, size):
        (maxcol,) = size
        _prev = _next = False
        start_wid = 0
        end_wid = len(self.widget_list)-1

        total_wid = sum([w[0] for w in self.widget_list])
        while total_wid > maxcol:
            if self.focus_column == end_wid:
                if not _prev:
                    total_wid+=1
                    _prev = True
                total_wid-=self.widget_list[start_wid][0]
                start_wid+=1
            else:
                if not _next:
                    total_wid+=1
                    _next = True
                total_wid-=self.widget_list[end_wid][0]
                end_wid-=1

        cols_left = maxcol - total_wid
        self.__start = start_wid #we need to keep it for getStartCol
        return _prev,_next,start_wid,end_wid,cols_left


    def mouse_event(self, size, event, button, x, y, focus):
        (maxcol,)=size

        if is_mouse_press(event) and button == 1:
            _prev,_next,start_wid,end_wid,cols_left = self.__calculate_limits(size)
            if x==0 and _prev:
                self.keypress(size, a_key['COLUMNS_ROLLER_LEFT'])
                return True
            if x==maxcol-1 and _next:
                self.keypress(size, a_key['COLUMNS_ROLLER_RIGHT'])
                return True

            current_pos = 1 if _prev else 0
            idx = 0
            while current_pos<x and idx<len(self.widget_list):
                width,widget = self.widget_list[idx]
                if x<=current_pos+width:
                    self.focus_column = idx
                    self._invalidate()
                    if not hasattr(widget,'mouse_event'):
                        return False
                    return widget.mouse_event((width,0), event, button,
                        x-current_pos, 0, focus)

                current_pos+=self.widget_list[idx][0]
                idx+=1

        return False

    def render(self, size, focus=False):
        if not self.widget_list:
            return urwid.SolidCanvas(" ", size[0], 1)

        _prev,_next,start_wid,end_wid,cols_left = self.__calculate_limits(size)

        idx=start_wid
        render = []

        for width,widget in self.widget_list[start_wid:end_wid+1]:
            _focus = idx == self.focus_column and focus
            render.append((widget.render((width,),_focus),False,_focus,width))
            idx+=1
        if _prev:
            render.insert(0,(urwid.Text(["◀"]).render((1,),False),False,False,1))
        if _next:
            render.append((urwid.Text(["▶"],align='right').render((1+cols_left,),False),False,False,1+cols_left))
        else:
            render.append((urwid.SolidCanvas(" "*cols_left, size[0], 1),False,False,cols_left))

        return urwid.CanvasJoin(render)


class FocusPile(urwid.Pile):
    """A Pile Widget which manage SàT Focus keys"""
    _focus_inversed = False

    def keypress(self, size, key):
        ret = super(FocusPile, self).keypress(size, key)
        if not ret:
            return

        if key in FOCUS_KEYS:
            direction, rotate = getFocusDirection(key, inversed = self._focus_inversed)
            max_pos = len(self.contents) - 1
            new_pos = self.focus_position + direction
            if rotate:
                if new_pos > max_pos:
                    new_pos = 0
                elif new_pos < 0:
                    new_pos = max_pos
            try:
                self.focus_position = new_pos
            except IndexError:
                pass

        return key


class FocusFrame(urwid.Frame):
    """Frame-like which manage SàT Focus Keys"""
    ordered_positions = ('footer', 'body', 'header')

    def keypress(self, size, key):
        ret = super(FocusFrame, self).keypress(size, key)
        if not ret:
            return

        if key in FOCUS_KEYS:
            direction, rotate = getFocusDirection(key)

            positions = [pos for pos in self.ordered_positions if pos in self]
            selectables = [pos for pos in positions if self.contents[pos][0].selectable()] # keep positions which exists and have a selectable widget
            if not selectables:
                # no widget is selectable, we just return
                return
            idx = selectables.index(self.focus_position) + direction
            if not rotate and (idx < 0 or idx >= len(selectables)):
                # if we don't rotate, we stay where we are on the first and last position
                return
            try:
                self.focus_position = selectables[idx]
            except IndexError:
                # happen if idx > len(selectables)
                self.focus_position = selectables[0]
            return

        return ret

    def get_cursor_coords(self, size):
        """Return the cursor coordinates of the focus widget."""
        if not self.selectable():
            return None
        if not hasattr(self.focus, 'get_cursor_coords'):
            return None
        maxcol, maxrow = size
        try:
            if self.focus_position != 'body':
                # only body is a box widget
                size = (maxcol,)
            col, row = self.focus.get_cursor_coords(size)
        except TypeError:
            return None
        if self.focus_position == 'header':
            return (col, row)
        if self.focus_position == 'body':
            header_rows = self.header.rows((maxcol,))
            return (col, row + header_rows)
        if self.focus_position == 'footer':
            footer_rows = self.footer.rows((maxcol,))
            return (col, row + (maxrow - footer_rows))
        raise Exception('This line should not be reached')


class TabsContainer(urwid.WidgetWrap):
    """ Container which can contain multiple box widgets associated to named tabs """
    signals = ['click']

    def __init__(self):
        self._current_tab = None
        self._buttons_cont = ColumnsRoller()
        self.tabs = []
        self._frame = FocusFrame(urwid.Filler(urwid.Text('')),urwid.Pile([self._buttons_cont,urwid.Divider("─")]))
        urwid.WidgetWrap.__init__(self, self._frame)

    def keypress(self, size, key):
        return self._w.keypress(size,key)

    def _buttonClicked(self, button, invisible=False):
        """Called when a button on the tab is changed,
        change the page
        @param button: button clicked
        @param invisible: emit signal only if False"""
        tab_name = button.get_label()
        for tab in self.tabs:
            if tab[0] == tab_name:
                break
        if tab[0] != tab_name:
            log.error(_("INTERNAL ERROR: Tab not found"))
            assert(False)
        self._frame.body = tab[1]
        button.set_label(('title',button.get_label()))
        if self._current_tab:
            self._current_tab.set_label(self._current_tab.get_label())
        self._current_tab = button
        if not invisible:
            self._emit('click')

    def _appendButton(self, name, selected=False):
        """Append a button to the frame header, and link it to the page change method.

        @param name (unicode): button name
        @param selected (bool): set to True to select this tab
        """
        button = CustomButton(name, self._buttonClicked, left_border = '', right_border=' | ')
        self._buttons_cont.addWidget(button, button.getSize())
        count = len(self._buttons_cont.widget_list)
        if selected or count == 1:
            # first/selected button: we set the focus and the body
            self.selectTab(count - 1)

    def addTab(self, name, content=None, selected=False):
        """Add a page to the container

        @param name: name of the page (what appear on the tab)
        @param content: content of the page:
            - if None create and empty Listbox
            - if it is a list instance, create a ListBox with the list in a body
            - else it must be a box widget which will be used instead of the ListBox
        @param selected (bool): set to True to select this tab
        @return: ListBox (content of the page)"""
        if content is None or isinstance(content, list):
            tab = urwid.ListBox(urwid.SimpleListWalker(content or []))
        else:
            tab = content

        self.tabs.append([name, tab])
        self._appendButton(name, selected)
        return tab

    def addFooter(self, widget):
        """Add a widget on the bottom of the tab (will be displayed on all pages)
        @param widget: FlowWidget"""
        self._w.footer = widget

    def selectTab(self, index):
        """Select a tab.

        @param index (int): index of the tab to select
        """
        self._buttons_cont.focus_position = index
        self._buttonClicked(self._buttons_cont.widget_list[index][1], True)


class HighlightColumns(urwid.AttrMap):
    """ Decorated columns which highlight all or some columns """

    def __init__(self, highlight_cols, highlight_attr, *args, **kwargs):
        """ Create the HighlightColumns
        @param highlight_cols: tuple of columns to highlight, () to highlight to whole row
        @param highlight_attr: name of the attribute to use when focused
        other parameter are passed to urwid Columns

        """
        columns = urwid.Columns(*args, **kwargs)
        self.highlight_cols = highlight_cols
        self.highlight_attr = highlight_attr
        self.has_focus = False
        if highlight_cols == ():
            super(HighlightColumns, self).__init__(columns, None, highlight_attr)
            self.highlight_cols = None
        else:
            super(HighlightColumns, self).__init__(columns, None)

    @property
    def options(self):
        return self.base_widget.options

    @property
    def contents(self):
        return self.base_widget.contents

    @property
    def focus_position(self):
        return self.base_widget.focus_position

    @focus_position.setter
    def focus_position(self, value):
        self.base_widget.focus_position = value

    def addWidget(self, wid, options):
        """ Add a widget to the columns
        Widget is wrapped with AttrMap, that's why Columns.contents should not be used directly for appending new widgets
        @param wid: widget to add
        @param options: result of Columns.options(...)

        """
        wrapper = urwid.AttrMap(wid, None)
        self.base_widget.contents.append((wrapper, options))


    def render(self, size, focus=False):
        if self.highlight_cols and focus != self.has_focus:
            self.has_focus = focus
            for idx in self.highlight_cols:
                wid = self.base_widget.contents[idx][0]
                wid.set_attr_map({None: self.highlight_attr if focus else None})

        return super(HighlightColumns, self).render(size, focus)


class TableContainer(urwid.WidgetWrap):
    """ Widgets are disposed in row and columns """
    signals = ['click']

    def __init__(self, items=None, columns=None, dividechars=1, row_selectable=False, select_key='enter', options=None):
        """ Create a TableContainer
        @param items: iterable of widgets to add to this container
        @param columns: nb of columns of this table
        @param dividechars: same as dividechars param for urwid.Columns
        @param row_selectable: if True, row are always selectable, even if they don't contain any selectable widget
        @param options: dictionnary with the following keys:
            - ADAPT: tuple of columns for which the size must be adapted to its contents,
                     empty tuple for all columns
            - HIGHLIGHT: tuple of columns which must be higlighted on focus,
                         empty tuple for the whole row
            - FOCUS_ATTR: Attribute name to use when focused (see HIGHLIGHT). Default is "table_selected"

        """
        pile = urwid.Pile([])
        super(TableContainer, self).__init__(pile)
        if items is None:
            items = []
        if columns is None: # if columns is None, we suppose only one row is given in items
            columns = len(items)
        assert columns
        self._columns = columns
        self._row_selectable = row_selectable
        self.select_key = select_key
        if options is None:
            options = {}
        for opt in ['ADAPT', 'HIGHLIGHT']:
            if opt in options:
                try:
                    options[opt] = tuple(options[opt])
                except TypeError:
                    log.warning('[%s] option is not a tuple' % opt)
                    options[opt] = ()
        self._options = options
        self._dividechars = dividechars
        self._idx = 0
        self._longuest = self._columns * [0]
        self._next_row_idx = None
        for item in items:
            self.addWidget(item)

    def _getIdealSize(self, widget):
        """ return preferred size for widget, or 0 if we can't find it """
        try:
            return len(widget.text)
        except AttributeError:
            return 0

    def keypress(self, size, key):
        if key == self.select_key and self._row_selectable:
            self._emit('click')
        else:
            return super(TableContainer, self).keypress(size, key)


    def addWidget(self, widget):
        # TODO: use a contents property ?
        pile = self._w
        col_idx = self._idx % self._columns

        options = None

        if col_idx == 0:
            # we have a new row
            columns = HighlightColumns(self._options.get('HIGHLIGHT'), self._options.get('FOCUS_ATTR', 'table_selected'), [], dividechars=self._dividechars)
            columns.row_idx = self._next_row_idx
            pile.contents.append((columns, pile.options()))
        else:
            columns = pile.contents[-1][0]

        if 'ADAPT' in self._options and (col_idx in self._options['ADAPT']
            or self._options['ADAPT'] == ()):
            current_len = self._getIdealSize(widget)
            longuest = self._longuest[col_idx]
            max_len = max(longuest, current_len)
            if max_len > longuest:
                self._longuest[col_idx] = max_len
                for wid,_ in pile.contents[:-1]:
                    col = wid.base_widget
                    col.contents[col_idx] = (col.contents[col_idx][0], col.options('given', max_len))
            options = columns.options('given', max_len) if max_len else columns.options()

        columns.addWidget(widget, options or columns.options())

        if self._row_selectable and col_idx == self._columns - 1:
            columns.addWidget(urwid.SelectableIcon(''), columns.options('given', 0))

        if not columns.selectable() and columns.contents[-1][0].base_widget.selectable():
            columns.focus_position = len(columns.contents)-1
        if not self.selectable() and columns.selectable():
            pile.focus_position = len(pile.contents) - 1
        self._idx += 1

    def setRowIndex(self, idx):
        self._next_row_idx = idx

    def getSelectedWidgets(self):
        columns = self._w.focus
        return (wid for wid, _ in columns.contents)

    def getSelectedIndex(self):
        columns = self._w.focus
        return columns.row_idx

## DECORATORS ##
class LabelLine(urwid.LineBox):
    """Like LineBox, but with a Label centered in the top line"""

    def __init__(self, original_widget, label_widget):
        urwid.LineBox.__init__(self, original_widget)
        top_columns = self._w.widget_list[0]
        top_columns.widget_list[1] = label_widget


class VerticalSeparator(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, original_widget, left_char = "│", right_char = ''):
        """Draw a separator on left and/or right of original_widget."""

        widgets = [original_widget]
        if left_char:
            widgets.insert(0, ('fixed', 1, urwid.SolidFill(left_char)))
        if right_char:
            widgets.append(('fixed', 1, urwid.SolidFill(right_char)))
        columns = urwid.Columns(widgets, box_columns = [0,2], focus_column = 1)
        urwid.WidgetDecoration.__init__(self, original_widget)
        urwid.WidgetWrap.__init__(self, columns)


