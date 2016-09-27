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


import os
import logging
import sys

log = logging.getLogger()


def omero_reader_enabled():
    try:
        value = int(os.environ['OMERO_READER_ENABLED'])
        return bool(value)
    except ValueError:
        message = "OMERO_READER_ENEABLED value should be 0 or 1"
        log.error(message)
        return False
    except KeyError:
        message = "Environment varible OMERO_READER_ENEABLED not set"
        log.warning(message)
        return False


def omero_on_the_path():
    try:
        sys.modules['omero.clients']
        return True
    except KeyError:
        return False
