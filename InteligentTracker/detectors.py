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
from .core import Space, Group
import cv2

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

DETECTOR_PATH = "/usr/local/share/OpenCV/haarcascades/"
face_cascade = cv2.CascadeClassifier(DETECTOR_PATH+'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(DETECTOR_PATH+'haarcascade_eye.xml')


class Detector(Space):
    """
    Here a Detector creates an Object or Entity from the real world
    which will have its own behaviour or "personality". This Detector is
    the one that classifies the objects and finds them in the real world
    if they are "lost" or they are not in the scenes anymore until
    they reappear again.
    """
    def __init__(self):
        self.parent = None
        self.children = []
        self.objects = []

    def detect_objects(self):
        pass

    def __json_enco__(self):
        pass


class EyeDetector(Detector):
    pass


class FaceDetector(Detector):
    def detect_objects(self):
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3,
                                              minNeighbors=5, minSize=(30, 30),
                                              flags=cv2.CASCADE_SCALE_IMAGE)


class PeopleDetector(Detector):
    pass


class ObjectDetector(Detector):
    pass


class MovementDetector(Detector):
    pass


class ColorDetector(Detector):
    pass