#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (C) 2017 David Toro <davsamirtor@gmail.com>

# compatibility with python 2 and 3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import object
from six import with_metaclass
from past.builtins import basestring

# import build-in modules
import sys
from abc import ABCMeta
from functools import wraps
from ordered_set import OrderedSet
from collections import MutableMapping, MutableSet

# import third party modules

# special variables
# __all__ = []
__author__ = "David Toro"
# __copyright__ = "Copyright 2017, The <name> Project"
# __credits__ = [""]
__license__ = "GPL"
# __version__ = "1.0.0"
__maintainer__ = "David Toro"
__email__ = "davsamirtor@gmail.com"
# __status__ = "Pre-release"


class MetaSpace(ABCMeta):
    """
    Meta class for the Space which gives the "physics" behaviour of the Space
    """
    def __new__(meta, name, bases, dct):
        init = dct.get('__init__', None)
        if init is not None:
            @wraps(init)
            def __init__(self, *args, **kwargs):
                name = kwargs.pop("name", None)
                parent = kwargs.pop("_space_parent", None)
                # initialization
                init(self, *args, **kwargs)
                # after initialization
                if name is not None:
                    self.name = name
                if parent is not None:
                    self._space_parent = parent
            dct['__init__'] = __init__
        return super(MetaSpace, meta).__new__(meta, name, bases, dct)

    def __init__(cls, name, bases, dct):
        super(MetaSpace, cls).__init__(name, bases, dct)


class Space(with_metaclass(MetaSpace, object)):
    """
    Anything that is created must have a name attribute and be in the Space
    """
    _space_entities = {}

    def __new__(cls, *args, **kwargs):
        self = super(Space, cls).__new__(cls)
        self._space_entities[str(id(self))] = self
        self._space_children = []
        return self

    def _correct_hierarchy(self, old_hierarchy):
        # register new name
        new_hierarchy = self._space_hierarchy()
        # change old name
        self._space_entities[new_hierarchy] = self._space_entities.pop(old_hierarchy)
        # change children's old names
        for i in self._space_children:
            old = new_hierarchy + "." + i.name
            new = old_hierarchy + "." + i.name
            self._space_entities[old] = self._space_entities.pop(new)

    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            return str(id(self))

    @name.setter
    def name(self, value):
        if value and value != self.name:
            if not isinstance(value, basestring):
                raise TypeError("name must be a string not {}".format(type(value)))
            if self._space_hierarchy(value) in self._space_entities:
                raise ValueError("name '{}' already exists".format(value))
            # get old hierarchy
            old_hierarchy = self._space_hierarchy()
            # assign new name
            self._name = value
            # correct all names
            self._correct_hierarchy(old_hierarchy)
            self._name_event()

    def _space_hierarchy(self, key=None):
        parent = self._space_parent
        train = []
        if parent is not None:
            train.append(parent._space_hierarchy())
        train.append(self.name)
        if key is not None:
            train.append(key)
        return ".".join(train)
        
    def _space_get_item(self, key=None):
        return self._space_entities[self._space_hierarchy(key)]

    @property
    def _space_parent(self):
        try:
            return self._space_parent_
        except AttributeError:
            return None

    @_space_parent.setter
    def _space_parent(self, value):
        if value != self._space_parent:
            # get old hierarchy
            old_hierarchy = self._space_hierarchy()
            old_parent = self._space_parent
            # assign new parent
            self._space_parent_ = value
            # correct all names
            self._correct_hierarchy(old_hierarchy)
            # register child in parent
            if value is None:
                value._space_children.remove(self)
            else:
                value._space_children.append(self)
            # unregister child in old parent
            if old_parent is not None:
                old_parent._space_children.remove(self)
            # call event
            self._parent_event()

    def _name_event(self):
        return

    def _parent_event(self):
        return


def deco_name(func, ismethod=True):
    """
    wrap function to give always 'name' variable
    
    :param func: 
    :param ismethod: 
    :return: 
    """
    if ismethod:
        @wraps(func)
        def _func(self, *args, **kwargs):
            name = kwargs.pop("name", None)
            return func(self, name, *args, **kwargs)
    else:
        @wraps(func)
        def _func(*args, **kwargs):
            name = kwargs.pop("name", None)
            return func(name, *args, **kwargs)
    return _func
    

class Group(Space, MutableSet):
    """
    Create group of objects withing the Space
    """
    # https://stackoverflow.com/a/3387975/5288758
    # https://github.com/LuminosoInsight/ordered-set/blob/master/ordered_set.py
    # TODO: this must only save references
    # TODO: create callbacks to delete references in groups if they are deleted from the space
    # TODO: create callbacks to change names in groups if the object name is changed
    # perhaps creating views from the Space is how a group can be made?
    # perhaps saving a class object as Name
    # consider https://stackoverflow.com/a/11560258/5288758

    def __init__(self, iterable=None):
        self.items = []
        self.map = {}
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.items)

    def __getitem__name(self, name):
        item = self._space_get_item(name)
        if item in self:
            return item
        raise KeyError("name {} is not in {}".format(name, self))

    def __getitem__(self, index):
        """
        Get the item at a given index.

        If `index` is a slice, you will get back that slice of items. If it's
        the slice [:], exactly the same object is returned. (If you want an
        independent copy of an OrderedSet, use `OrderedSet.copy()`.)

        If `index` is an iterable, you'll get the OrderedSet of items
        corresponding to those indices. This is similar to NumPy's
        "fancy indexing".
        """
        if isinstance(index, basestring):
            return self.__getitem__name(index)
        elif index == slice(None):
            return self
        elif hasattr(index, '__index__') or isinstance(index, slice):
            result = self.items[index]
            if isinstance(result, list):
                return type(self)(result)
            else:
                return result
        elif hasattr(index, '__iter__') and not isinstance(index, str) and not isinstance(index, tuple):
            return type(self)([self.items[i] for i in index])
        else:
            raise TypeError("don't know how to index by %r" % index)

    def copy(self):
        return type(self)(self)

    def __getstate__(self):
        if len(self) == 0:
            # The state can't be an empty list.
            # We need to return a truthy value, or else __setstate__ won't be run.
            #
            # This could have been done more gracefully by always putting the state
            # in a tuple, but this way is backwards- and forwards- compatible with
            # previous versions of OrderedSet.
            return (None,)
        else:
            return list(self)

    def __setstate__(self, state):
        if state == (None,):
            self.__init__([])
        else:
            self.__init__(state)

    def __contains__(self, key):
        if isinstance(key, basestring):
            try:
                return self._space_get_item(key) in self.map
            except KeyError:
                return False
        return key in self.map

    def add(self, key):
        """
        Add `key` as an item to this OrderedSet, then return its index.

        If `key` is already in the OrderedSet, return the index it already
        had.
        """
        if isinstance(key, basestring):
            key = self._space_get_item(key)
        if key not in self.map:
            key._space_parent = self
            self.map[key] = len(self.items)
            self.items.append(key)
        return self.map[key]
    append = add

    def update(self, sequence):
        """
        Update the set with the given iterable sequence, then return the index
        of the last element inserted.
        """
        item_index = None
        try:
            for item in sequence:
                item_index = self.add(item)
        except TypeError:
            raise ValueError('Argument needs to be an iterable, got %s' % type(sequence))
        return item_index

    def index(self, key):
        """
        Get the index of a given entry, raising an IndexError if it's not
        present.

        `key` can be an iterable of entries that is not a string, in which case
        this returns a list of indices.
        """
        if hasattr(key, '__iter__') and not isinstance(key, str) and not isinstance(key, tuple):
            return [self.index(subkey) for subkey in key]
        return self.map[key]

    def pop(self):
        """
        Remove and return the last element from the set.

        Raises KeyError if the set is empty.
        """
        if not self.items:
            raise KeyError('Set is empty')

        elem = self.items[-1]
        del self.items[-1]
        del self.map[elem]
        return elem

    def discard(self, key):
        """
        Remove an element.  Do not raise an exception if absent.

        The MutableSet mixin uses this to implement the .remove() method, which
        *does* raise an error when asked to remove a non-existent item.
        """
        if isinstance(key, basestring):
            key = self._space_get_item(key)
        if key in self:
            i = self.map[key]
            del self.items[i]
            del self.map[key]
            for k, v in self.map.items():
                if v >= i:
                    self.map[k] = v - 1

    def clear(self):
        """
        Remove all items from this OrderedSet.
        """
        del self.items[:]
        self.map.clear()

    def __iter__(self):
        return iter(self.items)

    def __reversed__(self):
        return reversed(self.items)

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __str__(self):
        name = getattr(self, "_name", "")
        if name:
            name = "<{}>".format(name)
        if not self:
            return '%s%s()' % (self.__class__.__name__, name)
        return '%s%s(%r)' % (self.__class__.__name__, name, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and self.items == other.items
        try:
            other_as_set = set(other)
        except TypeError:
            # If `other` can't be converted into a set, it's not equal.
            return False
        else:
            return set(self) == other_as_set