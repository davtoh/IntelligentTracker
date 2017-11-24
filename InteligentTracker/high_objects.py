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
from numbers import Number
from time import time

# import third party modules
from .core import Space, Group
from .periferials import UnifiedCamera, SyncCameras, PiCamera
from .detectors import Detector
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


class World(Space):
    """
    This is the world, here everything must be contained.
    """
    def __init__(self):
        self.scenes = Group(_space_parent=self, name="scenes")
        self.detectors = Group(_space_parent=self, name="detectors")

    def show(self, *args, **kwargs):
        name = kwargs.pop("name", None)
        if name is None:
            for i in self.scenes:
                i.show(*args, **kwargs)
        else:
            self.scenes[name].show(*args, **kwargs)

    def close(self, *args, **kwargs):
        name = kwargs.pop("name", None)
        if name is None:
            for i in self.scenes:
                i.close(*args, **kwargs)
        else:
            self.scenes[name].close(*args, **kwargs)

    def compute(self, *args, **kwargs):
        name = kwargs.pop("name", None)
        if name is None:
            for i in self.scenes:
                i.compute(*args, **kwargs)
        else:
            self.scenes[name].compute(*args, **kwargs)

    def create_scene(self, *args, **kwargs):
        scene = Scene(*args, **kwargs)
        self.scenes.add(scene)
        return scene

    def create_detector(self, *args, **kwargs):
        detector = Detector(*args, **kwargs)
        self.detectors.add(detector)
        return detector

    def assign_detector_to_scene(self, detector_name, scene_name):
        self.scenes[scene_name].add_detector(self.detectors[detector_name])

    def objects(self, detector_name=None, object_name=None):
        if detector_name is not None and object_name is not None:
            yield self.detectors[detector_name].objects[object_name]
        elif detector_name is None:
            for detector in self.detectors:
                if object_name is None:
                    for obj in detector.objects:
                        yield obj
                else:
                    try:
                        yield detector.objects[object_name]
                        break
                    except KeyError:
                        continue
            else:
                if object_name is not None:
                    raise KeyError("object {} not found".format(object_name))
        else:
            for obj in self.detectors[detector_name].objects:
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
            print("thread {} ended".format(self))

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
        with self._lock:
            return self._thread is None or not self._thread.is_alive()
    
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
