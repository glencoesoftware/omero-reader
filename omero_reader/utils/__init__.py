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
import os
import sys

log = logging.getLogger(__name__)


def omero_reader_enabled():
    try:
        return int(os.environ.get('OMERO_READER_ENABLED', 0)) != 0
    except ValueError:
        log.error("OMERO_READER_ENABLED value should be 0 or 1")
        return False


def omero_on_the_path():
    return 'omero.clients' in sys.modules
