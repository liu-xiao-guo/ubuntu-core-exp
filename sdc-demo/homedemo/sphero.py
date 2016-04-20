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

import logging
import os
import sys
from time import sleep, time
from mock import Mock

from home import Home
from servers import WebClientsCommands
from tools import MainLoop, Singleton

# enable importing kulka as if it was an external module
sys.path.insert(0, os.path.dirname(__file__))
import kulka

_sphero = None
logger = logging.getLogger(__name__)


class Sphero(object):
    """The Sphero protected (only one thread access to it) representation"""
    __metaclass__ = Singleton

    default_sphero_color = (221, 72, 20)

    def __init__(self, without_sphero=False):
        if not without_sphero:
            logger.debug("Connecting to sphero")
            sphero_hw = "sphero.hw"
            try:
                self.sphero = kulka.Kulka(open(sphero_hw).read().strip())
            except IOError:
                logger.error("Couldn't connect to sphero: {} doesn't exist".format(sphero_hw))
                sys.exit(1)
            logger.debug("Connected to sphero")
            self.sphero.set_inactivity_timeout(3600)
            self.sphero.set_rgb(*self.default_sphero_color)
        else:
            logger.info("Using a false sphero")
            self.sphero = Mock()
        self._current_room = Home().start_room
        self.last_move = time()
        self.in_calibration = False

    @property
    def current_room(self):
        return self._current_room

    @current_room.setter
    def current_room(self, value):
        self._current_room = value
        WebClientsCommands.sendCurrentRoomAll()

    @MainLoop.in_mainloop_thread
    def start_calibration(self):
        """Start calibration phase and turn off stabilizers. Prevent any other move until end_calibration is called"""
        self._start_calibration_sync()

    def _start_calibration_sync(self):
        """Sync version of start calibration"""
        logger.info("Calibration starting")
        self.in_calibration = True
        self.sphero.set_back_led(255)
        self.sphero.set_rgb(0, 0, 0)
        self.sphero.setheading(1)

    @MainLoop.in_mainloop_thread
    def recenter(self, angle):
        """Move centering to calibration angle"""
        logger.debug("Rotating center by {}".format(angle))
        self._start_calibration  # ensure we started calibration mode
        self.sphero.move(0, angle)

    def end_calibration(self):
        """End calibration phase and turn on stabilizer again"""
        logger.info("Calibration done")
        self.sphero.set_rgb(*default_sphero_color)
        self.sphero.set_back_led(0)
        self.sphero.setheading(0)
        self.in_calibration = False

    @MainLoop.in_mainloop_thread
    def quit(self):
        logger.info("Exit requested")
        MainLoop.quit()

    @MainLoop.in_mainloop_thread
    def move_to(self, room_name):
        '''Ask moving to a specific room_name. Ensure one action is finished before starting the next one'''
        if self.in_calibration:
            logger.info("Move action received, but in calibration mode")
            return
        room = Home().rooms.get(room_name, None)
        if not room:
            logger.error("{} isn't a valid room".format(room_name))
            MainLoop().quit()
        self._move_to_sync(room)

    def _move_to_sync(self, room, ingoback=False):
        '''Internal move_to implementation, without passing to the main loop as it can recall itself (travel back)'''
        logger.info("Travelling to {}".format(room.name))
        previous_room = self.current_room

        for path in self.current_room.paths[room.name]:
            logger.debug("Issuing roll{}".format(path))
            self.sphero.roll(*path)
            sleep(3)

        # set that we are in new room
        self.current_room = room

        # execute event
        if not ingoback:
            logger.info("Executing room event: {}".format(room.event.__name__))
            room.event(self.sphero)

        self.last_move = time()

        # travel back to previous room
        if not room.stay:
            logger.info("We can't stay in that room, travelling back")
            self._move_to(previous_room, ingoback=True)
