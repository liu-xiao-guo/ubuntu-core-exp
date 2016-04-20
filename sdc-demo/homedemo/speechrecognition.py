# -*- coding: utf-8 -*-
# Copyright (C) 2016 Canonical
#
# Authors:
#  Didier Roche
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from gi.repository import GLib
import logging
import os

from servers import WebClientsCommands
from sphero import Sphero
from tools import Singleton, suppress

logger = logging.getLogger(__name__)


class SpeechRecognition(object):
    """We are reading a file for now on speech recognition"""
    __metaclass__ = Singleton

    FILENAME = "speech.recognition"

    def __init__(self):
        """Create this Speech recognition object"""
        self._source_id = None
        self._enabled = False
        GLib.timeout_add_seconds(1, self.check_speech_recognition)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if self._enabled:
            logger.info("Enabling speech recognition feature")
        else:
            logger.info("Disabling speech recognition feature")
        WebClientsCommands.sendSpeechRecognitionStateAll()

    def check_speech_recognition(self):
        # Read file on disk
        with suppress(IOError):
            # we want to always remove the speech recognition file, even if enabled
            if self.enabled:
                with open(self.FILENAME) as f:
                    room_name = f.read().strip()
                    Sphero().move_to(room_name)
            with suppress(OSError):
                os.remove(self.FILENAME)

        return True
