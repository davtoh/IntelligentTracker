#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (C) 2017 David Toro <davsamirtor@gmail.com>

# compatibility with python 2 and 3
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import object
from past.utils import old_div

# import build-in modules
import os
from collections import deque

# import third party modules
#from RRtoolbox.lib.plotter import fastplt  # DEBUG
#from RRtoolbox.lib.arrayops import overlay
from .core import Space, Group, Agent, cv_major_ver, xrange, TailItem, Point
from .array_utils import norm_range, draw_contour_groups, is_numpy
import numpy as np
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

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))  # get current file path
DETECTOR_PATH = os.path.join(SCRIPT_PATH, "./haarcascades/")  # ""/usr/local/share/OpenCV/haarcascades/"
face_cascade = cv2.CascadeClassifier(os.path.abspath(os.path.join(DETECTOR_PATH, 'haarcascade_frontalface_default.xml')))
eye_cascade = cv2.CascadeClassifier(os.path.abspath(os.path.join(DETECTOR_PATH, 'haarcascade_eye.xml')))


class Detector(Space):
    """
    Here a Detector creates an Object or Entity from the real world
    which will have its own behaviour or "personality". This Detector is
    the one that classifies the objects and finds them in the real world
    if they are "lost" or they are not in the scenes anymore until
    they reappear again.
    """
    available_detectors = {}

    def __init__(self):
        # private Detector color
        self._BGR_color = None
        self.objects = Group(_space_parent=self, name="objects")

    def active_objects(self):
        """
        :return: objects that are active regardless if they are tracking
        """
        for o in self.objects:
            if o.active:
                yield o

    def inactive_objects(self):
        """
        :return: objects that are not active
        """
        for o in self.objects:
            if not o.active:
                yield o

    def tracked_objects(self):
        """
        :return: objects that are active and are tracking
        """
        for o in self.objects:
            if o.active and o.is_tracking:
                yield o

    def untracked_objects(self):
        """
        :return: objects that are not active or are not tracking
        """
        for o in self.objects:
            if not o.active or not o.is_tracking:
                yield o

    def track_objects(self, frame, mask=None):
        """
        only update without creating new objects

        :param frame:
        :param mask:
        :return:
        """
        for o in self.objects:
            if o.active:
                o.update(frame, mask)

    def detect_raw_objects(self, frame, mask=None):
        """To modify behaviour of detection"""
        tail_objects = None
        return tail_objects

    def filter_bad_raw_objects(self, tail_objects, frame, mask=None):
        return

    def process_raw_objects(self, frame, tail_items, bad_items, mask=None):
        """
        create new object or reuse object from a tail_item

        :param frame:
        :param tail_items:
        :param mask:
        :return:
        """
        #TODO objects should not be created inside other objects
        #FIXME if object dissappears from a period of time it is deleted but it should be restored (solve: do not touch o._stray_count but device a mechanism to move object to that new position)
        #TODO needs to implement the features of obejcts. This process should be paralell
        #TODO needs to implement paralelization of obejcts so that it does not take a lot of time if objects are increased

        # create dictionary to classify
        # format (inside, near)
        active_objects_dic = {i:([],[]) for i in self.active_objects()}
        # unclassified
        unclassified = []

        # classify all tail_items with objects
        for ti in tail_items:
            near_flag = False
            for o, (inside, near) in active_objects_dic.items():
                # find out if cnt overlaps with objects from this detector
                # faster check
                if o.tail[0].point_inside(ti):
                    # tail_item inside Object
                    # do not let object tracker grow too much
                    #o.update_tracker(frame, tail_item=ti)
                    inside.append(ti)
                    break
                elif ti.point_inside(o.position):
                    # Object inside tail_item
                    # if object lost track and it was detected again
                    #o.update_tracker(frame, tail_item=ti)
                    inside.append(ti)
                    break
                #elif o.tail[0].cnt_intersect(ti):  # covered by cnt_near
                #    # Object and tail_item touch
                #    break
                else:
                    flag, dist = o.tail[0].cnt_near(ti)
                    if flag:
                        # it is near an object do not create new
                        near_flag = True

                        # append to near raw_objects of object
                        #near.append(ti)

                        # continue finding objects that could contain the raw_obejct
                        continue
            else:
                if not near_flag and ti not in bad_items:
                    # create new object only if raw_object is not any of the
                    # objects that are being tracked
                    o = Object(frame=frame, parent_detector=self,
                               tail_item=ti, mask=mask)
                    self.objects.add_as_contained(o)
                    unclassified.append(o)

        # create or reuse objects as needed
        #for ti in unclassified:
        #    o = Object(frame=frame, parent_detector=self,
        #               tail_item=ti, mask=mask)
        #    self.objects.add_as_contained(o)
        for o, (inside, near) in active_objects_dic.items():
            if not inside:
                if not o.is_tracking:
                    o._stray_count += 1
            else:
                # group tail items and update tracker
                cont = np.vstack(inside)
                hull = cv2.convexHull(cont)
                o.update_tracker(frame, cnt=hull)

        return unclassified

    def delete_stray_objects(self):
        """
        delete all objects that are missing the correct target
        """
        objects = self.objects
        for o in objects:
            if (o.active and not o.live_forever and
                        o._stray_count > o._max_stray_count):
                o._space_delete()  # delete from all groups

    def _compute_objects(self, frame, mask=None, track=True, _debug_good=None,
                         _debug_bad=None):
        """
        complete steps to detect and process objects

        :param frame:
        :param mask:
        :param track:
        :param _debug_good:
        :return:
        """
        # example code
        if track:
            self.track_objects(frame, mask)
        # get raw objects from frame
        raw_objects = self.detect_raw_objects(frame, mask)

        # if there are raw objects to process
        if raw_objects is not None:

            # convert raw_objects items to tail items if not already
            raw_objects = [i if isinstance(i, TailItem) else TailItem(i)
                            for i in raw_objects]

            # filter raw_objects if necessary
            bad_objects = self.filter_bad_raw_objects(raw_objects, frame, mask)
            if bad_objects is None:
                bad_objects = set()
            else:
                bad_objects = set(bad_objects)  # for fast membership

            # debug good raw_objects
            if _debug_good is not None:
                self._debug_detector(_debug_good, [i for i in raw_objects
                                                   if i not in bad_objects])

            # debug bad raw_objects
            if _debug_bad is not None:
                self._debug_detector(_debug_bad, bad_objects)

            # process tail item into an object
            objs = self.process_raw_objects(frame, raw_objects, bad_objects, mask)

            # delete all objects that are missing the correct target
            self.delete_stray_objects()

            return objs

    def get_BGR_color(self):
        """
        get detector color from Parent detector or randomly generated
        """
        if self._BGR_color is None:
            try:
                # inherit color from parent
                self._BGR_color = norm_range(self._space_parent.get_BGR_color())
            except AttributeError:
                self._BGR_color = norm_range(np.random.rand(3)*255)
        return self._BGR_color

    @classmethod
    def register_detector(cls, detector_class, name=None):
        if issubclass(detector_class, Detector) and detector_class is not Detector:
            if name is None:
                name = detector_class.__name__.lower()
            if name in cls.available_detectors:
                raise ValueError("name '{}' is already registered".format(name))
            cls.available_detectors[name] = detector_class
        else:
            raise TypeError("class must be a subclass of {}".format(Detector))
    
    @classmethod    
    def get_detector(cls, name):
        try:
            return cls.available_detectors[name]
        except KeyError:
            try:
                return cls.available_detectors[name.lower()]
            except KeyError:
                raise KeyError("name '{}' is not registered".format(name))

    def __json_enco__(self):
        pass

    def _debug_detector(self, vis, mask):
        # construct a mask if mask is cnts
        if not is_numpy(mask):
            cnts = [i.cnt if isinstance(i, TailItem) else i for i in mask]
            mask = draw_contour_groups([cnts], shape=vis.shape, binary=True)
        pallet = np.array([[0, 0, 0], self.get_BGR_color()])
        a = pallet[(mask > 0).astype(np.int)]
        # a = np.zeros_like(frame)
        # a[mask>0] = color
        vis[mask > 0] = (vis * 0.5 + a * 0.5)[mask > 0].astype(np.uint8)


def affine(phi, img):
    """
    Increase robustness to descriptors by calculating other invariant perspectives to image.

    :param phi: rotation of image (in degrees)
    :param img: image to find Affine transforms
    :param mask: mask to detect keypoints (it uses default, mask[:] = 255)
    :return: skew_img, skew_mask, Ai (invert Affine Transform)

    Ai - is an affine transform matrix from skew_img to img

    """
    h, w = img.shape[:2]  # get 2D shape
    A = np.float32([[1, 0, 0], [0, 1, 0]])  # init Transformation matrix
    if phi != 0.0:  # simulate rotation
        phi = np.deg2rad(phi)  # convert degrees to radian
        s, c = np.sin(phi), np.cos(phi)  # get sine, cosine components
        # build partial Transformation matrix
        A = np.float32([[c, -s], [s, c]])
        corners = [[0, 0], [w, 0], [w, h], [0, h]]  # use corners
        tcorners = np.int32(np.dot(corners, A.T))  # transform corners
        x, y, w, h = cv2.boundingRect(
            tcorners.reshape(1, -1, 2))  # get translations
        A = np.hstack([A, [[-x], [-y]]])  # finish Transformation matrix build
        img = cv2.warpAffine(
            img, A, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        h, w = img.shape[:2]  # get new 2D shape
    Ai = cv2.invertAffineTransform(A)
    return img, Ai


class InvariantCascade(object):

    def __init__(self, angles=None):
        self.angles = angles

    def transformations(self, frame):
        #cols, rows = frame.shape[:2]
        for angle in self.angles:
            #angle = angle*np.pi/180
            #x, y = float(frame.shape[0])/2, float(frame.shape[1])/2
            #M = cv2.getRotationMatrix2D((y, x), angle, 1)
            #cols2, rows2 = np.dot(M, (cols, rows, 1))
            #M = np.array(((np.cos(angle), np.sin(angle), 0), (-np.sin(angle), np.cos(angle), 0)))
            #yield M, angle, cv2.warpAffine(frame, M, (int(cols2), int(rows2)))
            img, Ai = affine(angle, frame)
            yield Ai, angle, img

    def reconstruct(self, Ai, angle, bbox):
        #H = np.linalg.inv(np.append(M, ((0, 0, 1),), 0))
        # TODO: virtual coordinates not with real coordinates
        x, y, sz_x, sz_y = bbox
        xn, yn = np.dot(Ai, (x, y, 1))
        return Agent.get_rotated_box_from_bounding_box((xn, yn, sz_x, sz_y))[:-1]+(-angle,)


class EyeDetector(Detector):
    def detect_raw_objects(self, frame, mask=None):
        min_size = 0.1
        max_size = 0.5
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # http://answers.opencv.org/question/116587/rejectlevels-and-levelweights-of-detectmultiscale/
        eyes = eye_cascade.detectMultiScale(gray,
                                            minSize=(int(w * min_size),
                                                     int(h * min_size)),
                                            maxSize=(int(w * max_size),
                                                     int(h * max_size)),
                                            flags=cv2.CASCADE_SCALE_IMAGE)

        return [TailItem(bbox=bbox) for bbox in eyes]

Detector.register_detector(EyeDetector)


class FaceDetector(Detector):
    def detect_raw_objects(self, frame, mask=None):
        min_scale = 0.05  # 0.1
        h, w = frame.shape[:2]
        minSize = (int(w * min_scale), int(h * min_scale))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # https://stackoverflow.com/a/20805153/5288758
        # https://stackoverflow.com/a/22250382/5288758
        #faces = face_cascade.detectMultiScale(gray, minSize=minSize,
        #                                      scaleFactor=1.2, minNeighbors=6,
        #                                      flags=cv2.CASCADE_SCALE_IMAGE)
        #normal = [TailItem(bbox=bbox) for bbox in faces]
        # TODO complete invariance
        normal = []
        to_rotate = InvariantCascade([0, 20, 40, -20, -40])
        #to_rotate = InvariantCascade([10])
        for M, i, f in to_rotate.transformations(gray):
            faces = face_cascade.detectMultiScale(f, minSize=minSize,
                                                  scaleFactor=1.3,
                                                  minNeighbors=5,
                                                  flags=cv2.CASCADE_SCALE_IMAGE)

            normal.extend([TailItem(rbox=to_rotate.reconstruct(M, i, bbox)) for bbox in faces])

        return normal

Detector.register_detector(FaceDetector)


class PeopleDetector(Detector):
    pass

Detector.register_detector(PeopleDetector)


class ObjectDetector(Detector):
    pass

Detector.register_detector(ObjectDetector)


class MovementDetector(Detector):
    pass

Detector.register_detector(MovementDetector)


class ColorDetector(Detector):
    """
    Detect objects by color
    """

    def __init__(self, color_lower, color_upper):
        super(ColorDetector, self).__init__()
        self.color_lower = norm_range(color_lower)
        self.color_upper = norm_range(color_upper)

    def get_HSV_color_range(self):
        """
        return lower and upper HSV ranges
        """
        return self.color_lower, self.color_upper

    def set_HSV_color_range(self, color_lower=None, color_upper=None):
        """
        set lower and upper HSV ranges
        """
        if color_lower:
            self.color_lower = norm_range(color_lower)
        if color_upper:
            self.color_upper = norm_range(color_upper)

    def get_HSV_color(self):
        """
        return media HSV color from lower and upper HSV ranges
        """
        lower, upper = self.get_HSV_color_range()
        lower, upper = np.array(lower), np.array(upper)
        return (lower+upper)/2

    def get_BGR_color(self):
        """
        return media BGR color from lower and upper HSV ranges
        """
        return cv2.cvtColor(np.array([[self.get_HSV_color()]], np.uint8),
                            cv2.COLOR_BGR2HSV)[0, 0]

    def detect_raw_objects(self, frame, mask=None):
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # construct a mask for the color, then perform a series of dilation
        # and erosion operations to remove any small blobs left in it
        mk = cv2.inRange(hsv, self.color_lower, self.color_upper)
        mk = cv2.erode(mk, None, iterations=2)
        mk = cv2.dilate(mk, None, iterations=2)

        # find contours in the mask and initialize the current
        # (x, y) center of the ball
        cnts = cv2.findContours(mk, cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)[-2]
        return cnts

    def filter_bad_raw_objects(self, tail_objects, frame, mask=None):
        # only proceed if at least one contour was found
        ignore = False
        ignore_z = 0.001  # percent
        #z_must_be = np.min(frame.shape[:2])/ignore_z  # z as radius
        z_must_be = frame.shape[0]*frame.shape[1]*ignore_z  # z as area
        bad_objects = []
        for ti in tail_objects:
            #((x, y), z) = cv2.minEnclosingCircle(cnt)  # z as radius
            M = cv2.moments(ti.cnt)
            z = M["m00"]  # z as area
            x, y = (int(old_div(M["m10"], M["m00"])),
                    int(old_div(M["m01"], M["m00"])))
            # complete more data in tail item
            ti._pt = Point(*(x, y, z))

            if mask is not None:
                # find out if cnt overlaps with objects from other detectors
                #ignore = mask[y, x]
                pass

            # only proceed if cnt is not covered by other trackers
            # and z meets a minimum size
            if ignore and z < z_must_be:
                bad_objects.append(ti)
        return bad_objects

    @classmethod
    def __json_deco__(cls, data):
        return cls(data[0], data[1])

    def __json_enco__(self):
        return self.get_HSV_color_range()

Detector.register_detector(ColorDetector)


class Object(Agent):
    """
    It is any entity in the World that has its own characteristics or
    features and that can be tracked in the real world.
    """
    def __init__(self, frame, parent_detector,
                 max_tail_len=30, tracker_type='MEDIANFLOW', key_pts=None,
                 descriptors=None, **kwargs):
        super(Object, self).__init__()
        self._space_parent = parent_detector
        # private position deltas
        (self._dX, self._dY, self._dZ) = (None, None, None)
        # private object color
        self._BGR_color = None
        # private flag to recompute positions and tracked object
        self._to_recompute = True
        # unique features of object
        self.key_pts = key_pts  # key points for descriptors
        self.descriptors = descriptors  # descriptions for unique object
        # create deques
        self._direction_cover = 10  # last points to use to calculate direction
        self.tail = None  # deque containing points
        self.max_tail_len = max_tail_len  # maximum cached points in tail
        # tracker mechanism
        self.tracker_type = tracker_type
        self.tracker = None
        self._is_tracking = False
        # to delete stray objects
        self._stray_count = 0
        self._max_stray_count = 10
        self.live_forever = False  # do not let stray count to delete object
        # to detect zones where the object passes
        self._in_zones = []

        # first data
        self.add_to_tail(**kwargs)
        # update tracker
        self.update_tracker(frame)

    @property
    def cnt(self):
        return self.tail[0].cnt

    @cnt.setter
    def cnt(self, value):
        return

    @property
    def rotated_box(self):
        return self.tail[0].rbox

    @rotated_box.setter
    def rotated_box(self, value):
        return

    @property
    def dX(self):
        """get X position"""
        self.compute()  # if necessary update before giving answer
        return self._dX

    @property
    def dY(self):
        """get Y position"""
        self.compute()  # if necessary update before giving answer
        return self._dY

    @property
    def dZ(self):
        """get Z position"""
        self.compute()  # if necessary update before giving answer
        return self._dZ

    @property
    def tail_len(self):
        return len(self.tail)

    @property
    def max_tail_len(self):
        return self.tail.maxlen

    @max_tail_len.setter
    def max_tail_len(self, new_len):
        if not self._enough_items(new_len):
            raise ValueError("max_tail_len must be greater than {} and got "
                             "'{}'".format(self._enough_items(), new_len))

        try:
            old_len = self.tail.maxlen
        except AttributeError:
            # if tail is None force new tail operation
            old_len = new_len + 1
        if old_len != new_len:
            c_len = min([old_len, new_len])  # where tails can be merged
            cached_tail = self.tail  # old tail
            self.tail = deque(maxlen=new_len)  # new tail
            if cached_tail:  # either if None or no tail items
                for i, p in enumerate(cached_tail):
                    if i > c_len:
                        # break if either, old or new, lack
                        # the next tail items
                        break
                    # add from last tail items
                    self.tail.append(p)

    @property
    def is_tracking(self):
        return self._is_tracking

    @is_tracking.setter
    def is_tracking(self, value):
        if value and not self._is_tracking:
            # tracking again then clean path
            last = self.tail[0]
            self.tail.clear()
            self.tail.append(last)

        self._is_tracking = value

    @property
    def in_zones(self):
        return self._in_zones

    @in_zones.setter
    def in_zones(self, zones):
        # leave the new ones in zones and
        # find the ones that must be eliminated
        to_eliminate = []
        _in_zones = self._in_zones
        for oz in _in_zones:
            if oz in zones:
                zones.remove(oz)
            else:
                to_eliminate.append(oz)
        # eliminate zones that object is no more in
        for i in to_eliminate:
            _in_zones.remove(i)
            i._space_remove_child(self)
        # add new zones
        for nz in zones:
            _in_zones.append(nz)
            nz._space_add_child(self)

    @in_zones.deleter
    def in_zones(self):
        self.in_zones = []

    def _enough_items(self, no_items=None):
        """
        test whether number of tail items are enough to be covered
         and calculated by the direction attribute

        :param no_items: number of items in tail
        :return: True if no_items passes can be processed. If no_items is None
            it returns the no_items what would be considered True.
        """
        to_cover = self._direction_cover * 2
        if no_items is None:
            return to_cover
        if no_items >= to_cover:
            return True

    @property
    def position(self):
        """
        :return: last point or position
        """
        return self.tail[0].pt

    def get_BGR_color(self):
        """
        get object color assigned from Detector or randomly generated
        """
        if self._BGR_color is None:
            try:
                # inherit color from parent
                self._BGR_color = norm_range(self._space_parent.get_BGR_color())
            except AttributeError:
                self._BGR_color = norm_range(np.random.rand(3)*255)
        return self._BGR_color

    def add_to_tail(self, *args, **kwargs):
        """
        add a tail_item itself or from a contour (cnt), bounding box (bbox)
        or rotated box (rbox) to the tail. The point (pt) can be specified
        on creation but not if tail_item is given

        :param args: {0}
        :param kwargs: {0}
        :return: tail_item
        """
        frame = kwargs.pop("frame", None)
        mask = kwargs.pop("mask", None)
        try:
            tf = kwargs["tail_item"]
        except KeyError:
            tf = TailItem(*args, **kwargs)
        self.tail.appendleft(tf)
        self._to_recompute = True
        # update key_points and descriptors
        if frame is not None:
            self._update_description(frame, tf)
        if mask is not None:
            self._fill_mask(mask, tf)
        return tf
    add_to_tail.__doc__ = add_to_tail.__doc__.format(TailItem._fields)

    def _update_description(self, frame, tail_item):
        return

    def _fill_mask(self, mask, tail_item):
        cv2.drawContours(mask, [tail_item.cnt], -1, 1, -1)

    def point_inside(self, point):
        """
        test whether point is inside object in last position

        :param point: point or x-coordinate, y-coordinate
        :return: True if inside or in contour, else False
        """
        return self.tail[0].point_inside(point)

    def point_near(self, point):
        """
        test whether point is near object in last position

        :param point: point or x-coordinate, y-coordinate
        :return: True if inside or in contour, else False
        """
        return self.tail[0].point_near(point)

    def cnt_intersect(self, cnt):
        """
        test whether last internal cnt from tail is intersected
        with external cnt

        :param cnt: external contour
        :return: True if contours intersect, else False
        """
        return self.tail[0].cnt_intersect(cnt)

    def cnt_near(self, cnt):
        """
        test whether last internal cnt from tail is near
        with external cnt

        :param cnt: external contour
        :return: True if contours intersect, else False
        """
        return self.tail[0].cnt_near(cnt)

    def direction(self, x_axis=("left", "right"), y_axis=("up", "down"),
                  z_axis=("far", "near")):
        """
        get tracked object direction in a readable form
        
        :param x_axis: names of the extremes in the x axis. ("left", "right")
        :param y_axis: names of the extremes in the y axis. ("up", "down")
        :param z_axis: names of the extremes in the z axis. ("far", "near")
        :return: x_axis, y_axis, z_axis directions
        """

        (dirX, dirY, dirZ) = ("", "", "")
        if not self.compute():  # if necessary update before giving answer
            # if there was no update but it needed to update
            return "-".join((dirX, dirY, dirZ))

        dX, dY, dZ = self._dX, self._dY, self._dZ
        # ensure there is significant movement in the
        # x-direction,
        if np.abs(dX) > 0:
            dirX = x_axis[1] if np.sign(dX) == 1 else x_axis[0]

        # y-direction,
        if np.abs(dY) > 0:
            dirY = y_axis[1] if np.sign(dY) == 1 else y_axis[0]

        # and z-direction
        if np.abs(dZ) > 0:
            dirZ = z_axis[1] if np.sign(dY) == 1 else z_axis[0]

        return "-".join((dirX, dirY, dirZ))

    def _compute(self):
        # check there are enough points
        tail = self.tail
        if not self._enough_items(len(tail)):
            return  # still to compute, nothing done

        cover = self._direction_cover
        # how many points to cover
        #average = np.average([np.array(tail[i]) for i in np.arange(cover)], 0)
        #rolled = np.average([np.array(tail[-i-1]) for i in np.arange(cover)], 0)
        average = (np.sum(np.array([np.array(tail[i].pt)*(cover-i)
                                   for i in xrange(cover)]), 0)
                   / np.sum(np.arange(cover) + 1))
        rolled = (np.sum(np.array([np.array(tail[-i-1].pt)*(cover-i)
                                 for i in xrange(cover)]), 0)
                / np.sum(np.arange(cover) + 1))
        # compute the difference between the x and y coordinates
        self._dX, self._dY, self._dZ = [int(i) for i in (average - rolled)]
        self._to_recompute = False  # computed

    def update_tracker(self, frame, mask=None, tracker_type=None, **kwargs):
        if tracker_type is None:
            tracker_type = self.tracker_type

        tk_name = tracker_type.upper()
        if int(cv_major_ver) < 3:
            tracker = cv2.Tracker_create(tk_name)
        elif tk_name == 'BOOSTING':
            tracker = cv2.TrackerBoosting_create()
        elif tk_name == 'MIL':
            tracker = cv2.TrackerMIL_create()
        elif tk_name == 'KCF':
            tracker = cv2.TrackerKCF_create()
        elif tk_name == 'TLD':
            tracker = cv2.TrackerTLD_create()
        elif tk_name == 'MEDIANFLOW':
            tracker = cv2.TrackerMedianFlow_create()
        elif tk_name == 'GOTURN':
            tracker = cv2.TrackerGOTURN_create()
        else:
            raise ValueError("tracker_type not supported")

        # add tail if tracker was created
        if kwargs:
            # renewing tracker and correct it
            tf = self.add_to_tail(mask=mask, frame=frame, **kwargs)
        else:
            # renewing tracker from last item in tail
            tf = self.tail[0]

        # register new tracker if tail was added successfully
        self.tracker_type = tracker_type
        self.tracker = tracker
        self.is_tracking = tracker.init(frame, tf.bbox)

    def update(self, frame, mask=None):
        # Update tracker
        self.is_tracking, bbox = self.tracker.update(frame)
        if self.is_tracking:
            self.add_to_tail(mask=mask, frame=frame, bbox=bbox)

    def draw_circle(self, frame, color=None):
        # draw the circle and centroid on the frame,
        # then update the list of tracked points
        if color is None:
            color = self.get_BGR_color()
        else:
            color = norm_range(color)
        try:
            x, y, _ = self.position
            (_, radius) = cv2.minEnclosingCircle(self.tail[0].cnt)
            center = (int(x), int(y))
            cv2.circle(frame, center, int(radius), color, 2)
            cv2.circle(frame, center, 5, norm_range([255-i for i in color]), -1)
        except IndexError:
            pass

    def draw_tail(self, frame, color=None, iterate=None):
        """
        Draw object tail on frame

        :param frame: frame to draw on
        :param color: color of tail (1x3 array)
        :param iterate: iterate over positions
        :return:
        """
        if color is None:
            color = self.get_BGR_color()
        else:
            color = norm_range(color)
        tail = self.tail
        if iterate is None:
            iterate = xrange(1, len(tail))
        # loop over the set of tracked points
        for i in iterate:
            # if either of the tracked data are None, ignore them
            if tail[i - 1] is None or tail[i] is None:
                continue
            # otherwise, compute the thickness of the line and
            # draw the connecting lines
            thickness = int(np.sqrt(old_div(self.tail_len, float(i + 1))) * 2.5)
            cv2.line(frame, tail[i - 1].pt[:2], tail[i].pt[:2], color, thickness)

    def draw_stats(self, frame, position=None, fontFace=None, fontScale=None,
                   color=None, thickness=None, tag=None):
        """

        :param frame:
        :param position:
        :param fontFace:
        :param fontScale:
        :param color:
        :param thickness:
        :param tag:
        :return:
        """
        if position is None:
            position = (10, frame.shape[0] - 10)
        if fontFace is None:
            fontFace = cv2.FONT_HERSHEY_SIMPLEX
        if fontScale is None:
            fontScale = 0.35
        if color is None:
            color = self.get_BGR_color()
        else:
            color = norm_range(color)
        if thickness is None:
            thickness = 1
        if tag is None:
            tag = "dx: {dx}, dy: {dy}, dz: {dz} \n{direction}"
        # show the movement deltas and the direction of movement on
        # the frame
        text = tag.format(dx=self.dX, dy=self.dY, dz=self.dZ,
                          direction=self.direction())
        cv2.putText(frame, text, position, fontFace=fontFace,
                    fontScale=fontScale, color=color, thickness=thickness)

    def __json_enco__(self):
        return self.max_tail_len

    def _parent_changed_event(self, old_parent):
        return