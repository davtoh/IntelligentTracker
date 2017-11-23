#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (C) 2017 David Toro <davsamirtor@gmail.com>

# compatibility with python 2 and 3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import object

# import build-in modules
import sys
from past.builtins import basestring
from numbers import Number
from time import time

# import third party modules
from ordered_set import OrderedSet
from collections import MutableMapping, MutableSet
from .periferials import UnifiedCamera, SyncCameras, PiCamera
import numpy as np
from threading import Thread, RLock
from .forms import EventFigure
import cv2
(cv_major_ver, cv_minor_ver, cv_subminor_ver) = cv2.__version__.split('.')

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


class Space(object):
    """
    Anything that is created must have a name attribute and be in the Space
    """
    entities = {}

    def __new__(cls, *args, **kwargs):
        self = super(Space, cls).__new__(cls)
        self.name = str(id(self))
        self.entities[self.name] = self
        return self        

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
            if value in self.entities:
                raise ValueError("name '{}' already exists".format(value))
            old_name = self.name
            # register new name
            self.entities[value] = self
            # delete old name
            del self.entities[old_name]
            # assign new name
            self._name = value
            self._name_event()

    def _name_event(self):
        return
    

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

    def __init__(self, iterable=None):
        self.items = []
        self.map = {}
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.items)

    def __getitem__(self, name):
        item = self.entities[name]
        if item in self:
            return item
        raise KeyError("name {} is not in Group".format(name))

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
        if index == slice(None):
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
            raise TypeError("Don't know how to index an OrderedSet by %r" %
                    index)

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
        return key in self.map

    def add(self, key):
        """
        Add `key` as an item to this OrderedSet, then return its index.

        If `key` is already in the OrderedSet, return the index it already
        had.
        """
        if key not in self.map:
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
        if is_iterable(key):
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


class World(Space):
    """
    This is the world, here everything must be contained.
    """
    def __init__(self):
        self.scenes = Group()
        self.trackers = Group()

    def show(self, name=None, *args, **kwargs):
        if name is None:
            for i in self.scenes:
                i.show(*args, **kwargs)
        else:
            self.scenes[name].show(*args, **kwargs)

    def close(self, name=None, *args, **kwargs):
        if name is None:
            for i in self.scenes:
                i.close(*args, **kwargs)
        else:
            self.scenes[name].close(*args, **kwargs)

    def compute(self, name=None, *args, **kwargs):
        if name is None:
            for i in self.scenes:
                i.compute(*args, **kwargs)
        else:
            self.scenes[name].compute(*args, **kwargs)

    def create_scene(self, name=None, *args, **kwargs):
        scene = Scene(*args, **kwargs)
        if name is not None:
            scene.name = name
        self.scenes.add(scene)
        return scene

    def create_tracker(self, name=None, *args, **kwargs):
        tracker = Scene(*args, **kwargs)
        if name is not None:
            tracker.name = name
        self.trackers.add(tracker)
        return tracker

    def assign_tracker_to_scene(self, tracker_name, scene_name):
        self.scenes[scene_name].add_tracker(self.trackers[tracker_name])

    def objects(self, name=None):
        if name is None:
            for tracker in self.trackers:
                for obj in tracker.objects:
                    yield obj
        else:
            for obj in self.trackers[name].objects:
                yield obj

    def __json_enco__(self):
        pass


class Agent(Space):
    """
    Anything in the World, from here anything is derived and populated
    in the world.
    """
    def __init__(self):
        self._to_compute = False
        self.active = False
        self.visible = False
        self.drawing = None
        self.cnt = []
        self.rotated_box = None

    def compute(self):
        pass

    def computed_vis(self):
        pass

    def raw_vis(self):
        pass

    @staticmethod
    def get_bounding_box_from_rotated_box(rotated_box, _type=None):
        (tx, ty), (sz_x, sz_y), angle = rotated_box
        # get half distance to center
        x, y = sz_x / 2., sz_y / 2.
        if _type is None:
            return tx - x, ty - y, sz_x, sz_y
        else:
            return _type(tx - x), _type(ty - y), _type(sz_x), _type(sz_y)

    @staticmethod
    def get_rotated_box_from_bounding_box(bounding_box, _type=None):
        x, y, sz_x, sz_y = bounding_box
        # get half distance to center
        tx, ty = sz_x / 2., sz_y / 2.
        if _type is None:
            return (x + tx, y + ty), (sz_x, sz_y), 0
        else:
            return ((_type(x + tx), _type(y + ty)),
                    (_type(sz_x), _type(sz_y)), _type(0))

    @staticmethod
    def get_rotated_box_from_cnt(cnt, _type=None):
        """
        get a rotated box format (center, size, angle)
        from a contour of N points.
        """
        if _type is None:
            return cv2.minAreaRect(cnt)
        else:
            (cx, cy), (x, y), a = cv2.minAreaRect(cnt)
            return (_type(cx), _type(cy)), (_type(x), _type(y)), _type(a)

    @staticmethod
    def get_cnt_from_rotated_box(rotated_box, _type=None):
        """
        get a contour of 4 points with format [left-top, right-top,
        right-bottom, left-bottom] from a rotated box with format
        (center, size, angle)
        """
        # format (x,y),(width,height),theta e.g. ((122, 239), (4, 4), 0)
        (tx, ty), (sz_x, sz_y), angle = rotated_box
        # get half distance to center
        x, y = sz_x/2., sz_y/2.
        # construct contour in origin
        cnt_rect = np.array([((-x, -y),), ((x, -y),),
                             ((x, y),), ((-x, y),)], np.float)#.reshape(-1, 1, 2)

        # create transformation matrix to rotate and translate
        # https://en.wikipedia.org/wiki/Transformation_matrix
        a = angle * np.pi / 180.  # convert from degrees to radians
        c = np.cos(a)
        s = np.sin(a)
        H = np.array([(c, -s, tx),
                      (s, c, ty),
                      (0, 0, 1)], np.float)

        # apply transformation with desired type
        # https://docs.opencv.org/2.4/modules/core/doc/operations_on_arrays.html#perspectivetransform
        if _type is None:
            return cv2.perspectiveTransform(cnt_rect, H)
        else:
            return _type(cv2.perspectiveTransform(cnt_rect, H))

    def __json_enco__(self):
        pass


class Scene(Space):
    """
    This is a scene, specifically made to name places in the world
    and configure how the place is seen through the perspectives it can
    see in the place (cameras)
    
    .. example::
        
        # create a scene with two available cameras
        scene = Scene([None, None])
        # show the scene
        scene.show()
        # change resolution in shown scene
        scene.resolution = (300,200)
        # change frame rate in show scene and processing
        scene.framerate = 5
        # close and stop scene processing
        scene.close()
        # re-open scene vesualization and continue processing
        scene.show()

    """
    def __init__(self, camera_ids=None, resolution=None, framerate=None,
                 calibration_cubes=None, name=None):
        """
        
        :param camera_ids: 
        :param resolution: 
        :param framerate: 
        :param calibration_cubes: 
        :param name: 
        """
        self.view = None
        self.name = name

        try:
            camera_ids = list(camera_ids)
        except TypeError:
            camera_ids = [camera_ids]

        cameras = []
        for i in camera_ids:
            try:
                if isinstance(i, (UnifiedCamera, PiCamera)):
                    camera = i
                else:
                    camera = UnifiedCamera(i)
                cameras.append(camera)
            except IOError:
                for c in cameras:
                    c.close()
                raise 
        self.sync_stream = SyncCameras(cameras)
        self.resolution = resolution
        self.framerate = framerate
        self.calibration_cubes = calibration_cubes
        self.mask = None
        self.areas = []
        self._stop = True
        self._computed_vis = None
        self._thread = None
        self._lock = RLock()

    @property
    def active(self):
        return not self._stop

    @active.setter
    def active(self, value):
        stopped = not value
        if stopped:
            self._stop = stopped
        else:
            self.start()

    @property
    def framerate(self):
        return self.sync_stream._framerate

    @framerate.setter
    def framerate(self, value):
        self.sync_stream.framerate = value
        if value is not None and self.view is not None:
            self.view.interval = 1000//value

    @property
    def resolution(self):
        return self.sync_stream.resolutions

    @resolution.setter
    def resolution(self, value):
        self.sync_stream.resolutions = value

    def computed_vis(self):
        """
        camera feed with processed objects
        """
        vis = self._computed_vis
        if vis is None:
            return self.compute()
        return vis

    def raw_vis(self):
        """
        camera feed
        """
        if self._stop:
            # start stream for a short period
            with self.sync_stream:
                return self._apply_cube(self.sync_stream.capture())
        else:
            self.sync_stream.start()  # ensure it is started
            return self._apply_cube(self.sync_stream.capture())

    def _apply_cube(self, captures, convert_func=None):
        if convert_func:
            return np.hstack([convert_func(c) for c in captures])
        else:
            return np.hstack(captures)

    def _name_event(self):
        if self.view is not None:
            self.view.set_title(self.name)

    def show(self, start=True):
        """
        creates a window to visualize the scene
        """
        # start processing
        if start:
            self.start()

        # create view if None
        if self.view is None:

            class View(EventFigure):
                def update_func(selfo, *args):
                    # _computed_vis is the computed visualization 
                    # at any given frame and if it is None it will
                    # not update the animation in the window
                    #t = time()
                    #print("Visualization taken in {}".format(t-self.view._time))
                    #self.view._time = t
                    return self._computed_vis
            
            # interval can be any value but if it is 0 it is stopped
            # the refreshing of the window is determined by the self.framerate
            self.view = View(self.computed_vis(), interval=1000//self.framerate,
                             blit=False, title=self.name)
            self.view._time = time()

        self._computed_vis.astype(np.uint8)  # test vis
        # show window
        self.view.show()
        return self.view

    def compute(self, frame=None):
        # process image to follow and detect objects in scene
        if frame is None:
            frame = self.raw_vis()
        # process frame
        frame_processed = frame
        self._computed_vis = frame_processed
        return frame_processed

    def update(self):
        # start streaming and computing
        try:
            with self.sync_stream:
                for images in self.sync_stream.capture_continuous():
                    self.compute(self._apply_cube(images))
                    if self._stop:
                        break
        finally:
            self._stop = True
            #print("thread {} ended".format(self))

    def start(self):
        # start the thread to read frames from the video stream
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = t = Thread(target=self.update, args=())
                t.daemon = False
                self._stop = False  # thread started
                t.start()
        return self

    def close(self, window=True):
        with self._lock:
            if window:
                self.close_window()
            else:
                self._last_frame = self._computed_vis
            if self._thread is not None and self._thread.is_alive():
                self._stop = True
                self._thread.join()

    def close_window(self):
        if self.view:
            self.view.close()

    def closed(self):
        return self._stop
    
    def closed_window(self):
        if self.view:
            self.view.is_closed()
        return True  # if there is not view the it is closed

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def __json_enco__(self):
        pass


class Area(Agent):
    """
    An Area is an specific region of a Scene e.g. two doors (the areas)
    can be in a store (the scene). In the real world, an Area can
    be among several Scenes but for implementation simplicity every
    Area must only be inside an specific Scene. The Area can tell when
    an object is inside it or outside.
    """
    pass


class Line(Agent):
    """
    A line is a special kind of Area but that cannot have objects inside,
    it just tells when an object passes from one side to the other.
    """
    pass


class Object(Agent):
    """
    It is any entity in the World that has its own characteristics or
    features and that can be tracked in the real world.
    """
    def __init__(self, tracker_type='MEDIANFLOW'):
        super(Object, self).__init__()

        tracker_type = tracker_type.upper()
        if int(cv_minor_ver) < 3:
            tracker = cv2.Tracker_create(tracker_type)
        else:
            if tracker_type == 'BOOSTING':
                tracker = cv2.TrackerBoosting_create()
            if tracker_type == 'MIL':
                tracker = cv2.TrackerMIL_create()
            if tracker_type == 'KCF':
                tracker = cv2.TrackerKCF_create()
            if tracker_type == 'TLD':
                tracker = cv2.TrackerTLD_create()
            if tracker_type == 'MEDIANFLOW':
                tracker = cv2.TrackerMedianFlow_create()
            if tracker_type == 'GOTURN':
                tracker = cv2.TrackerGOTURN_create()
        self.tracker = tracker


class Detector(Space):
    """
    Here a Detector creates an Object or Entity from the real world
    which will have its own behaviour or "personality". This Detector is
    the one that classifies the objects and finds them in the real world
    if they are "lost" or they are not in the scenes anymore until
    they reappear again.
    """
    pass