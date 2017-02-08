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

"""This module manage action <==> key mapping and can be extended to add new actions"""
from functools import reduce


class ConflictError(Exception):
    pass


class ActionMap(dict):
    """Object which manage mapping betwwen actions and keys"""

    def __init__(self, source_dict=None):
        """ Initialise the map

        @param source_dict: dictionary-like object with actions to import
        """
        self._namespaces_actions = {} # key = namespace, values (set) = actions
        self._close_namespaces = tuple()
        self._alway_check_namespaces = None
        if source_dict is not None:
            self.update(source_dict)

    def __setitem__(self, action, shortcut):
        """set an action avoiding conflicts

        @param action (str,tuple): either an action (str) or a (namespace, action) tuple. action without namespace will not be checked by cbeck_namespaces(). namespace can also be a tuple itself, the action will the be assigned to several namespaces.
        @param shortcut (str): key shortcut for this action
        @raise: ConflictError if the action already exists
        """
        if isinstance(action, tuple):
            namespaces, action = action
            if not isinstance(namespaces, tuple):
                namespaces = (namespaces,)
            for namespace in namespaces:
                namespace_map = self._namespaces_actions.setdefault(namespace.lower(), set())
                namespace_map.add(action)

        if action in self:
            raise ConflictError("The action [{}] already exists".format(action))
        return super(ActionMap, self).__setitem__(action, shortcut.lower())

    def __delitem__(self, action):
        # we don't want to delete actions
        raise NotImplementedError

    def replace_shortcut(self, action, shortcut):
        """Replace an existing action

        @param action: name of an existing action
        @param shortcut: new shortcut to use
        @raise KeyError: action doesn't exists
        """
        assert isinstance(action, str)
        if action not in self:
            raise ValueError("Action [{}] doesn't exist".format(action))
        super(ActionMap, self).__setitem__(action, shortcut)

    def update(self, new_actions):
        """Update actions with an other dictionary

        @param new_actions: dictionary object to update actions
        @raise ValueError: something else than a dictionary is used
        @raise: ConflictError if at least one of the new actions already exists
        """
        if not isinstance(new_actions, dict):
            raise ValueError("only dictionary subclasses are accepted for update")
        conflict = new_actions.keys() & self.keys()
        if conflict:
            raise ConflictError("The actions [{}] already exists".format(','.join(conflict)))
        for action, shortcut in list(new_actions.items()):
            self[action] = shortcut

    def replace(self, action_shortcuts_map):
        """Replace shortcuts with an other dictionary

        @param action_shortcuts_map: dictionary like object to update shortcuts
        @raise ValueError: something else than a dictionary is used
        @raise KeyError: action doesn't exists
        """
        if not isinstance(action_shortcuts_map, dict):
            raise ValueError("only dictionary subclasses are accepted for replacing shortcuts")
        for action, shortcut in action_shortcuts_map.items():
            self.replace_shortcut(action, shortcut)

    def set_close_namespaces(self, close_namespaces, always_check=None):
        """Set namespaces where conflicting shortcut should not happen

        used by check_namespaces to see if the same shortcut is not used in two close namespaces (e.g. 'tab' used in edit_bar and globally)
        @param close_namespaces (tuple of tuples): tuple indicating namespace where shortcut should not conflict. e.g.: (('global', 'edit'), ('confirm', 'popup', 'global')) indicate that shortcut in 'global' and 'edit' should not be the same, nor the ones between 'confirm', 'popup' and 'global'.
        @param always_check (tuple): if not None, these namespaces will be close to every other ones (useful for global namespace)
        """
        assert isinstance(close_namespaces, tuple)
        if always_check is not None:
            assert isinstance(always_check, tuple)
        to_check = reduce(lambda ns1, ns2: ns1.union(ns2), close_namespaces, set(always_check) or set())
        if not to_check.issubset(self._namespaces_actions):
            raise ValueError("Unkown namespaces: {}".format(', '.join(to_check.difference(self._namespaces_actions))))
        self._close_namespaces = close_namespaces
        self._alway_check_namespaces = always_check

    def check_namespaces(self):
        """Check that shortcuts are not conflicting in close namespaces"""
        # we first check each namespace individually
        checked = set()

        def check_namespaces(namespaces):
            # for each namespace which save keys used
            # if 1 key is used several times, we raise
            # a ConflictError
            set_shortcuts = {}

            to_check = set(namespaces + self._alway_check_namespaces)

            for namespace in to_check:
                checked.add(namespace)
                for action in self._namespaces_actions[namespace]:
                    shortcut = self[action]
                    if shortcut in set_shortcuts:
                        set_namespace = set_shortcuts[shortcut]
                        if set_namespace == namespace:
                            msg = 'shortcut [{}] is not unique in namespace "{}"'.format(shortcut, namespace)
                        else:
                            msg = 'shortcut [{}] is used both in namespaces "{}" and "{}"'.format(shortcut, set_namespace, namespace)
                        raise ConflictError(msg)
                    set_shortcuts[shortcut] = namespace

        # we first check close namespaces
        for close_namespaces in self._close_namespaces:
            check_namespaces(close_namespaces)

        # then the remaining ones
        for namespace in set(self._namespaces_actions.keys()).difference(checked):
            check_namespaces((namespace,))


keys = {
        ("edit", "EDIT_HOME"): 'ctrl a',
        ("edit", "EDIT_END"): 'ctrl e',
        ("edit", "EDIT_DELETE_TO_END"): 'ctrl k',
        ("edit", "EDIT_DELETE_LAST_WORD"): 'ctrl w',
        ("edit", "EDIT_ENTER"): 'enter',
        ("edit", "EDIT_COMPLETE"): 'shift tab',
        (("edit", "modal"), "MODAL_ESCAPE"): 'esc',
        ("selectable", "TEXT_SELECT"): ' ',
        ("selectable", "TEXT_SELECT2"): 'enter',
        ("menu_box", "MENU_BOX_UP"): 'up',
        ("menu_box", "MENU_BOX_LEFT"): 'left',
        ("menu_box", "MENU_BOX_RIGHT"): 'right',
        ("menu", "MENU_DOWN"): 'down',
        ("menu", "MENU_UP"): 'up',
        ("menu_roller", "MENU_ROLLER_UP"): 'up',
        ("menu_roller", "MENU_ROLLER_DOWN"): 'down',
        ("menu_roller", "MENU_ROLLER_RIGHT"): 'right',
        ("columns_roller", "COLUMNS_ROLLER_LEFT"): 'left',
        ("columns_roller", "COLUMNS_ROLLER_RIGHT"): 'right',
        ("focus", "FOCUS_SWITCH"): 'tab',
        ('focus', "FOCUS_UP"): 'ctrl up',
        ('focus', "FOCUS_DOWN"): 'ctrl down',
        ('focus', "FOCUS_LEFT"): 'ctrl left',
        ('focus', "FOCUS_RIGHT"): 'ctrl right',
        ('files_management', "FILES_HIDDEN_HIDE"): 'meta h',
        ('files_management', "FILES_JUMP_DIRECTORIES"): 'meta d',
        ('files_management', "FILES_JUMP_FILES"): 'meta f',
       }

action_key_map = ActionMap(keys)

