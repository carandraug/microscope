#!/usr/bin/env python3

## Copyright (C) 2020 Ian Dobbie <ian.dobbie@bioch.ox.ac.uk>
## Copyright (C) 2020 Mick Phillips <mick.phillips@gmail.com>
##
## This file is part of Microscope.
##
## Microscope is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## Microscope is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Microscope.  If not, see <http://www.gnu.org/licenses/>.

"""RaspberryPi camera modules.
"""

import logging

import microscope
import microscope.abc
import picamera
import picamera.array
import RPi.GPIO as GPIO


_logger = logging.getLogger(__name__)


GPIO_Trigger = 21


# TODO: replace with microscope.TriggerType and microscope.TriggerMode
TRIGGER_MODES = {
    "internal": None,
    "external": microscope.abc.TRIGGER_BEFORE,
    "external start": None,
    "external exposure": microscope.abc.TRIGGER_DURATION,
    "software": microscope.abc.TRIGGER_SOFT,
}


class PiCamera(microscope.abc.Camera):
    def __init__(self, **kwargs) -> None:
        super(PiCamera, self).__init__(**kwargs)
        # example parameter to allow setting.
        #        self.add_setting('_error_percent', 'int',
        #                         lambda: self._error_percent,
        #                         self._set_error_percent,
        #                         lambda: (0, 100))
        self._acquiring = False
        self._exposure_time = 0.1
        self._triggered = False
        self.camera = None
        # Region of interest.
        self.roi = microscope.ROI(None, None, None, None)
        # Cycle time
        self.exposure_time = 0.001  # in seconds
        self.cycle_time = self.exposure_time
        # initialise in soft trigger mode
        self.set_trigger(
            microscope.TriggerType.SOFTWARE, microscope.TriggerMode.ONCE
        )
        # setup hardware triggerline
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_Trigger.GPIO.IN)

        # when a rasing edge is detected on port GPIO_Trigger,
        # regardless of whatever else is happening in the program, the
        # function self._HW_trigger will be run
        GPIO.add_event_detect(
            GPIO_Trigger, GPIO.RAISING, callback=self._HW_trigger, bouncetime=10
        )

        if not self.camera:
            try:
                # initialise camera in still image mode.
                self.camera = picamera.PiCamera(sensor_mode=2)
            except:
                raise Exception("Problem opening camera.")
        _logger.info("Initializing camera.")
        # create img buffer to hold images.
        # disable camera LED by default
        self.setLED(False)
        self._get_sensor_shape()

    def _HW_trigger(self):
        """Function called by GPIO interupt, needs to trigger image capture"""
        print("PiCam HW trigger")

    def _fetch_data(self):
        if self._acquiring and self._triggered:
            with picamera.array.PiYUVArray(self.camera) as output:
                self.camera.capture(output, format="yuv", use_video_port=False)
                # just return intensity values
                _logger.info("Sending image")
                self._triggered = False
                return output.array[:, :, 0]

    def initialize(self):
        pass

    def _do_disable(self):
        self.abort()

    def _do_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        self._acquiring = True
        # actually start camera
        _logger.info("Acquisition enabled.")
        return True

    def abort(self):
        _logger.info("Disabling acquisition.")
        if self._acquiring:
            self._acquiring = False

    def set_trigger_type(self, trigger):
        # DEPRECATED, implement methods defined in TriggerTargetMixin
        if trigger == microscope.abc.TRIGGER_SOFT:
            GPIO.remove_event_detect(GPIO_Trigger)
            self.trigger = microscope.abc.TRIGGER_SOFT
        elif trigger == microscope.abc.TRIGGER_BEFORE:
            GPIO.add_event_detect(
                GPIO_Trigger, RISING, self.HWtrigger, self.exposure_time
            )
            self.trigger = microscope.abc.TRIGGER_BEFORE

    def get_trigger_type(self):
        # DEPRECATED: use the trigger_* properties
        return self.trigger

    def _get_roi(self):
        """Return the current ROI (left, top, width, height)."""
        return self.roi

    def _set_binning(self, h_bin, v_bin):
        return True

    def _get_binning(self):
        return microscope.Binning(1, 1)

    @microscope.abc.keep_acquiring
    def _set_roi(self, left, top, width, height):
        """Set the ROI to (left, tip, width, height)."""
        self.roi = microscope.ROI(left, top, width, height)

    # set camera LED status, off is best for microscopy.
    def setLED(self, state=False):
        print("self.camera.led(state)")

    def set_exposure_time(self, value):
        # exposure times are set in us.
        self.camera.shutter_speed = int(value * 1.0e6)

    def get_exposure_time(self):
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return self.camera.exposure_speed * 1.0e-6

    def get_cycle_time(self):
        # fudge to make it work initially
        # exposure times are in us, so multiple by 1E-6 to get seconds.
        return self.camera.exposure_speed * 1.0e-6 + 0.1

    def _get_sensor_shape(self):
        res = self.camera.resolution
        self._set_roi(0, 0, res[0], res[1])
        return res

    def soft_trigger(self):
        # DEPRECATED: implement _do_trigger instead as required by
        # TriggerTargetMixin
        _logger.info(
            "Trigger received; self._acquiring is %s." % self._acquiring
        )
        if self._acquiring:
            self._triggered = True

    def HWtrigger(self, pin):
        _logger.info("HWTrigger received")

    def _do_shutdown(self) -> None:
        raise NotImplementedError()

    def _do_trigger(self) -> None:
        raise NotImplementedError()

    def set_trigger(
        self, ttype: microscope.TriggerType, tmode: microscope.TriggerMode
    ) -> None:
        raise NotImplementedError()

    @property
    def trigger_type(self) -> microscope.TriggerType:
        raise NotImplementedError()

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        raise NotImplementedError()


# ongoing implemetation notes

# should be able to use rotation and hflip to set specific output image
# rotations

# roi's can be set with the zoom function, default is (0,0,1,1) meaning all the data.

# Need to setup a buffer for harware triggered data aquisition so we can
# call the acquisition and then download the data at our leasure
