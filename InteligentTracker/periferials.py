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

# import third party modules
import cv2
from time import time, sleep
from threading import Thread, Event, RLock
from collections import Counter
from numbers import Number

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


class UnifiedCamera(object):
    """
    Emulate PiCamera in a system that does not have PiCamera support
    with a normal cv2.VideoCapture supported by OpenCV
    """
    # https://github.com/waveform80/picamera/blob/master/picamera/camera.py
    def __init__(self, camera_num=None):
        self.resolution = None
        self.framerate = None
        if camera_num is None:
            for camera_num in range(100):
                _camera = cv2.VideoCapture(camera_num)
                if _camera.isOpened():
                    break
                _camera.release()
            else:
                raise IOError("no camera found")
        else:
            _camera = cv2.VideoCapture(camera_num)

        self._camera_num = camera_num
        self._camera = _camera
        self.closed = False

    def start_preview(self):
        self._camera.open(self._camera_num)
        if not self._camera.isOpened():
            raise IOError("camera {} could not be oppened".format(self._camera_num))
        self._camera.read()  # activate it
        self.closed = False

    def capture(self, rawCapture, format="jpeg",
                           use_video_port=False):
        (grabbed, frame) = self._camera.read()

        if not grabbed:
            return frame

        res = self.resolution
        if res is not None and frame.shape[:2] != res:
            frame = cv2.resize(frame, res)

        format = format.lower()
        if format in ('rgb', 'jpeg'):
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif format == ('png', 'rgba'):
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        elif format == 'bgra':
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

        #rawCapture.array[:] = frame
        return frame

    def capture_continuous(self, rawCapture, format="jpeg",
                           use_video_port=False):

        #if self.resolution is None:
        #    self.resolution = rawCapture.shape[:2]

        diff_time = 1/self.framerate  # second / frame per second
        timer = time() + diff_time  # do not wait in first frame
        while True:
            timer_new = time()
            elapsed = (timer_new - timer)
            if elapsed < diff_time:
                remain = diff_time-elapsed
                sleep(remain)
                timer_new += remain  # timer_new = time()
            timer = timer_new

            yield self.capture(rawCapture, format, use_video_port)

    def close(self):
        self._camera.release()
        self.closed = True

    def __enter__(self):
        self.start_preview()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __str__(self):
        return "{}:{}".format(type(self), self._camera_num)

try:
    from picamera.array import PiRGBArray
    from picamera import PiCamera
except ImportError:
    import numpy as np

    class PiRGBArray(object):
        """
        Emulate PiRGBArray in a system that does not have PiCamera support
        with a normal camera input supported by OpenCV
        """
        def __init__(self, camera, size=None):
            self.array = None
            self.camera = camera
            self.size = size

        @property
        def size(self):
            return self._size

        @size.setter
        def size(self, value):
            self._size = value
            self.array = np.zeros(value[:2][::-1] + (3,), np.uint8)

        @size.deleter
        def size(self):
            del self._size

        def truncate(self, val=0):
            #self.array[:] = val
            return

        def close(self):
            self.array = None

    PiCamera = UnifiedCamera  # emulates PiCamera


class VideoStream(object):

    def __init__(self, src=None, usePiCamera=False, resolution=(320, 240),
                 framerate=30, format='rgb', trigger=None):
        # initialize the camera and stream
        if usePiCamera:
            self.camera = PiCamera()
        else:
            if isinstance(src, (UnifiedCamera, PiCamera)):
                self.camera = src
            else:
                self.camera = UnifiedCamera(src)
        self.resolution = resolution
        self.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)

        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self._stop = True  # thread is stopped or non existent
        if trigger is None:
            trigger = Event()
        self.trigger = trigger
        self.format = format
        self._thread_free = Event()
        self._order = Event()
        self._lock = RLock()
        self._thread = None

    @property
    def resolution(self):
        return self.camera.resolution

    @resolution.setter
    def resolution(self, value):
        self.camera.resolution = value

    @property
    def framerate(self):
        return self.camera.framerate

    @framerate.setter
    def framerate(self, value):
        self.camera.framerate = value

    def update(self):
        # initialize events
        self._order.clear()  # there are not orders yet
        self._thread_free.set()  # notify thread is free to receive orders
        toggle = True
        try:
            self.camera.start_preview()  # start camera
            # keep looping infinitely until the thread is stopped
            while not self._stop:
                # because self.trigger can be shared it is possible that
                # self.read function was called setting self.trigger once
                # but this can be turned off while in other threads so
                # we have to check self.thread_free is not set meaning
                # that it has to produce a frame, thus it should not
                # be blocked
                #if self._thread_free.is_set():
                #    self.trigger.clear()  # make the thread wait until event
                #    #self.__debug("event waiting in {}'s thread".format(id(self)))
                #    self.trigger.wait()  # wait until read function or event calls
                #    self._thread_free.clear()  # tell thread is busy
                #    #self.__debug("event was unblocked in {}'s thread".format(id(self)))
                #    self._order.set()  # there is an order

                # if the thread indicator variable is set, stop the thread
                # and resource camera resources
                #if self._stop:
                #    break

                self.frame = self.camera.capture(self.rawCapture, self.format)
                #print("{}taking photo in {}".format((""," ")[toggle],id(self)))
                #toggle = not toggle
                # notify frame was produced and thread is free
                # as quickly as possible
                #self._thread_free.set()
                self.rawCapture.truncate(0)
        finally:
            # ending thread
            #self.rawCapture.close()
            self.camera.close()
            self._thread_free.set()  # prevents blocking in main
            self._stop = True
            #print("thread {} ended".format(self))

    def read(self):
        # FIXME: cameras are not synchronised
        # FIXME: there is a time lag between the real world when framerates are low
        # even though the frames are low each time it is refreshed should
        # show exactly the image taken in the real world
        with self._lock:
            # send event to read
            #self.__debug("reading in {}".format(id(self)), start_debug=True)
            # if thread_free is not set then thread is already producing frame
            # if thread_free is set but frame is not None then we are forced
            # to produce new frame
            if self._stop:
                raise RuntimeError("{} must be started".format(type(self)))

            # update frame
            if self._thread_free.is_set() and not self._order.is_set():  # and self.frame is None:
                self._thread_free.clear()  # tell thread will be busy
                self.trigger.set()  # start processing in thread
                #self.__debug("event set in {}".format(id(self)))

            # give latest frame
            try:
                return self.get_frame()
            finally:
                if self.frame is None:
                    self.close()
                    raise IOError("camera '{}' not working".format(self.camera))

    def get_frame(self):
        """
        safely give frame from latest read. if latest read has not ended
         it waits for it to end and gives the frame.
        """
        # wait for latest frame
        timeout = self._thread_free.wait(3)
        if not timeout:
            raise Exception("There was a timeout")
        self._order.clear()
        return self.frame

    def start(self):
        # start the thread to read frames from the video stream
        with self._lock:
            # if several threads are trying to start it wait
            # if while this lock was waiting and this thread ended in another
            # lock, open the tread again to prevent inconsistencies
            if self._thread is None or not self._thread.is_alive():
                self._thread = t = Thread(target=self.update, args=())
                t.daemon = False
                self._stop = False  # thread started
                t.start()
        return self

    def close(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                # indicate that the thread should be stopped
                self._stop = True
                self._thread_free.clear()
                self.trigger.set()  # un-pause threads
                self._thread.join()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @classmethod
    def __debug(cls, data=None, start_debug=False):
        if not hasattr(cls, "checks"):
            cls.checks = Counter()
            cls.check_cum = set()

        if start_debug and data in cls.check_cum:
            cls.checks[frozenset(cls.check_cum)] += 1
            cls.check_cum = set()
            cls.check_cum.add(data)
        else:
            cls.check_cum.add(data)


class SyncCameras(object):
    def __init__(self, cameras, resolution=None, framerate=None):
        self._framerate = 30
        self._resolution = None
        self.event = Event()  # http://effbot.org/zone/thread-synchronization.htm
        self.streams = []
        for i in cameras:
            s = VideoStream(i, trigger=self.event)
            self.streams.append(s)
        self.resolutions = resolution
        self.framerate = framerate

    @property
    def framerate(self):
        return self._framerate

    @framerate.setter
    def framerate(self, value):
        if value and self._framerate != value:
            self._framerate = value

    @property
    def resolutions(self):
        return self._resolution

    @resolutions.setter
    def resolutions(self, value):
        if value:
            if isinstance(value[0], Number):
                # case resolution for all cameras
                # format: (width, high)
                for i in self.streams:
                    i.resolution = value
            else:
                # case resolution for each camera
                # format: [(width, high) ... (width, high)]
                for i, value in zip(self.streams, value):
                    i.resolution = value
        
        # get resolutions
        self._resolution = [i.resolution for i in self.streams]

    def capture(self):
        try:
            return [i.read() for i in self.streams]
        except Exception:
            self.close()
            raise

    def capture_continuous(self):
        """
        continuously produce camera feeds
        """
        diff_time = 1/self.framerate  # second / frame per second
        timer = time() + diff_time  # do not wait in first frame
        while True:
            timer_new = time()
            elapsed = (timer_new - timer)
            diff_time = 1 / self.framerate  # allow to change
            if elapsed < diff_time:
                remain = diff_time-elapsed
                sleep(remain)
                timer_new += remain  # timer_new = time()
            #print("sync at {}".format(timer_new - timer))
            timer = timer_new
            yield self.capture()
    
    def close(self):
        for i in self.streams:
            i.close()

    def start(self):
        for i in self.streams:
            i.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # TODO method to add and remove cameras