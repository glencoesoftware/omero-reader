#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Glencoe Software, Inc. All rights reserved.
#
# This software is distributed under the terms described by the LICENCE file
# you can find at the root of the distribution bundle.
# If the file is missing please request a copy by contacting
# info@glencoesoftware.com.
#

import logging
import numpy
import re

from struct import unpack


OMERO_IMPORTED = False
try:
    import omero.clients
    OMERO_IMPORTED = True
except ImportError:
    pass

log = logging.getLogger(__name__)


'''
The rescaling is probably super broken for Signed Types. Need to further
investigate why only single value for scale is used.
For the implementation that's mirrored in here look at:
    https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/formatreader.py#L767
'''


def pixel_range(byte_width, signed):
    max_value = 2 ** (8 * byte_width)
    if signed:
        return (- (max_value / 2.0), (max_value / 2.0) - 1)
    else:
        return (0, max_value - 1)


class OmeroReader(object):

    REGEX_INDEX_FROM_FILE_NAME = re.compile(r'[^\d-]+')
    PIXEL_TYPES = {
        "int8": ['b', numpy.int8, pixel_range(1, True)],
        "uint8": ['B', numpy.uint8, pixel_range(1, False)],
        "int16": ['h', numpy.int16, pixel_range(2, True)],
        "uint16": ['H', numpy.uint16, pixel_range(2, False)],
        "int32": ['i', numpy.int32, pixel_range(4, True)],
        "uint32": ['I', numpy.uint32, pixel_range(4, False)],
        "float": ['f', numpy.float32, (0, 1)],
        "double": ['d', numpy.float64, (0, 1)]}
    SCALE_ONE_TYPE = ["float", "double"]

    def __init__(self, host, session_id, image_id=None, url=None):
        '''
        Initalise the reader by passing:
        url -- 'omero::idd=image_id' format.
        host -- omero server address.
        session_id -- session to join.
        '''
        self.url = url
        self.image_id = image_id
        self.host = host
        self.session_id = session_id
        # Connection setup
        self.client = None
        self.session = None
        self.context = {'omero.group': '-1'}  # Search for image in all groups
        # Omero services
        self.container_service = None
        # Omero objects
        self.omero_image = None
        self.pixels = None
        # Image info
        self.width = None
        self.height = None
        self.metadata = None
        self.extract_id = self.REGEX_INDEX_FROM_FILE_NAME
        # Needed for CellProfiler's reader caching
        self.path = url

    def __enter__(self):
        '''
        '''
        return self

    def __exit__(self):
        '''
        '''
        self.close()

    def close(self):
        '''
        Close connection to the server.
        Important step. Closes all the services on the server freeing up
        the resources.
        '''
        log.debug("Closing OmeroReader [%s]" % self.image_id)
        if self.client is not None:
            self.client.closeSession()

    def init_reader(self):
        '''
        Connect to OMERO server by joining session id.
        Request the OMERO.image from the server.
        Regex converts "omero::iid=image_id" to image_id.
        After reader is initaillised images can be read from the server.
        Connection to the server is terminated on close call.
        '''
        # Check if session object already exists
        if self.session is not None:
            return
        # Parse image id from url
        if self.url is not None:
            self.image_id = int(self.extract_id.sub('', self.url))
        elif self.image_id is None:
            log.error("No url or image Id cannot initialize reader")
            return False
        else:
            self.image_id = int(self.image_id)
        log.debug("Initializing OmeroReader for Image id: %s" % self.image_id)
        # Initialize client object if does not exists
        if self.client is None:
            self.client = omero.client(self.host)
        # Connect to the server
        try:
            self.session = self.client.joinSession(self.session_id)
            self.container_service = self.session.getContainerService()
        except:
            message = "Couldn't connect to OMERO server"
            log.exception(message, exc_info=True)
            raise Exception(message)
        # Get image object from the server
        try:
            self.omero_image = self.container_service.getImages(
                "Image", [self.image_id], None, self.context)[0]
        except:
            message = "Image Id: %s not found on the server." % self.image_id
            log.error(message, exc_info=True)
            raise Exception(message)
        self.pixels = self.omero_image.getPrimaryPixels()
        self.width = self.pixels.getSizeX().val
        self.height = self.pixels.getSizeY().val
        return True

    def read_planes(self, z=0, c=None, t=0, tile=None):
        '''
        Creates RawPixelsStore and reads planes from the OMERO server.
        '''
        channels = []
        if c is None:
            channels = range(self.pixels.getSizeC().val)
        else:
            channels.append(c)
        pixel_type = self.pixels.getPixelsType().value.val
        numpy_type = self.PIXEL_TYPES[pixel_type][1]
        raw_pixels_store = self.session.createRawPixelsStore()
        try:
            raw_pixels_store.setPixelsId(
                self.pixels.getId().val, True, self.context)
            log.debug("Reading pixels Id: %s" % self.pixels.getId().val)
            log.debug("Reading channels %s" % channels)
            planes = []
            for channel in channels:
                if tile is None:
                    sizeX = self.width
                    sizeY = self.height
                    raw_plane = raw_pixels_store.getPlane(
                        z, channel, t, self.context)
                else:
                    x, y, sizeX, sizeY = tile
                    raw_plane = raw_pixels_store.getTile(
                        z, channel, t, x, y, sizeX, sizeY)
                convert_type = '>%d%s' % (
                    (sizeY * sizeX), self.PIXEL_TYPES[pixel_type][0])
                converted_plane = unpack(convert_type, raw_plane)
                plane = numpy.array(converted_plane, numpy_type)
                plane.resize(sizeY, sizeX)
                planes.append(plane)
            if c is None:
                return numpy.dstack(planes)
            else:
                return planes[0]
        except Exception:
            log.error("Failed to get plane from OMERO", exc_info=True)
        finally:
            raw_pixels_store.close()

    def read(self, c=None, z=0, t=0, series=None, index=None,
             rescale=True, wants_max_intensity=False, channel_names=None,
             XYWH=None):
        '''
        Read a single plane from the image reader file.
        :param c: read from this channel. `None` = read color image if
            multichannel or interleaved RGB.
        :param z: z-stack index
        :param t: time index
        :param series: series for ``.flex`` and similar multi-stack formats
        :param index: if `None`, fall back to ``zct``, otherwise load the
            indexed frame
        :param rescale: `True` to rescale the intensity scale to 0 and 1;
            `False` to return the raw values native to the file.
        :param wants_max_intensity: if `False`, only return the image;
            if `True`, return a tuple of image and max intensity
        :param channel_names: provide the channel names for the OME metadata
        :param XYWH: a (x, y, w, h) tuple
        '''
        debug_message = \
            "Reading C: %s, Z: %s, T: %s, series: %s, index: %s, " \
            "channel names: %s, rescale: %s, wants_max_intensity: %s, " \
            "XYWH: %s" % (c, z, t, series, index, channel_names, rescale,
                          wants_max_intensity, XYWH)
        if c is None and index is not None:
            c = index
        log.debug(debug_message)
        if self.session is None:
            self.init_reader()
        message = None
        if t >= self.pixels.getSizeT().val:
            message = "T index %s exceeds sizeT %s" % \
                      (t, self.pixels.getSizeT().val)
            log.error(message)
        if (c or 0) >= self.pixels.getSizeC().val:
            message = "C index %s exceeds sizeC %s" % \
                      (c, self.pixels.getSizeC().val)
            log.error(message)
        if z >= self.pixels.getSizeZ().val:
            message = "Z index %s exceeds sizeZ %s" % \
                      (z, self.pixels.getSizeZ().val)
            log.error(message)
        if message is not None:
            raise Exception("Couldn't retrieve a plane from OMERO image.")
        tile = None
        if XYWH is not None:
            assert isinstance(XYWH, tuple) and len(XYWH) == 4, \
                "Invalid XYWH tuple"
            tile = XYWH
        numpy_image = self.read_planes(z, c, t, tile)
        pixel_type = self.pixels.getPixelsType().value.val
        min_value = self.PIXEL_TYPES[pixel_type][2][0]
        max_value = self.PIXEL_TYPES[pixel_type][2][1]
        log.debug("Pixel range [%s, %s]" % (min_value, max_value))
        if rescale or pixel_type == 'double':
            log.info("Rescaling image using [%s, %s]" % (min_value, max_value))
            # Note: The result here differs from:
            #     https://github.com/emilroz/python-bioformats/blob/a60b5c5a5ae018510dd8aa32d53c35083956ae74/bioformats/formatreader.py#L903
            # Reason: the unsigned types are being properly taken into account
            # and converted to [0, 1] using their full scale.
            # Further note: float64 should be used for the numpy array in case
            # image is stored as 'double', we're keeping it float32 to stay
            # consitent with the CellProfiler reader (the double type is also
            # converted to single precision)
            numpy_image = \
                (numpy_image.astype(numpy.float32) + float(min_value)) / \
                (float(max_value) - float(min_value))
        if wants_max_intensity:
            return numpy_image, max_value
        return numpy_image
