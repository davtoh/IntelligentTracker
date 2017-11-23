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


class Detector(object):
    def __init__(self):
        self.parent = None
        self.children = []
        self.objects = []

    def __json_enco__(self):
        pass


class EyeDetector(Detector):
    pass


class FaceDetector(Detector):
    pass


class PeopleDetector(Detector):
    pass


class ObjectDetector(Detector):
    pass


class MovementDetector(Detector):
    pass


class ColorDetector(Detector):
    pass