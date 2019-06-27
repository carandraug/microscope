#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

"""Interface to IDS cameras.

The interface makes use of `is_WaitForNextImage` instead of the
`is_EnableEvent`, `is_InitEvent`, etc... because `is_WaitForNextImage`
is supposedly platform independent.  It is also meant to work better
with image sequences.

"""

import ctypes
import typing
from typing import Tuple

import Pyro4
import numpy as np

import microscope.devices
from microscope._wrappers import ueye


class IDSuEye(microscope.devices.TriggerTargetMixIn,
              microscope.devices.CameraDevice):
    """IDS uEye camera.

    Args:
        serial_number (str): the camera serial number.  If set to
            `None`, it uses the first available camera.
    """
    def __init__(self, serial_number: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._handle = ueye.HIDS()

        ## Someday, we should make this a configuration.  Is there
        ## scope to make this part of the CameraDevice specification?
        self._ring_buffer_length = 10

        if _number_of_ids_cameras() == 0:
            raise RuntimeError('no IDS cameras found')

        if serial_number is None:
            ## We can pass a camera ID of zero to InitCamera to
            ## initialise the first available camera.
            self._handle = ueye.HIDS(0)
        else:
            for info in _get_info_of_all_cameras():
                if info.SerNo == serial_number.encode():
                    device_id = info.dwDeviceID
                    break
            else:
                raise RuntimeError("No camera found with serial number '%s'"
                                   % serial_number)
            self._handle = ueye.HIDS(device_id | ueye.USE_DEVICE_ID)

        status = ueye.InitCamera(ctypes.byref(self._handle), None)
        _check_status(status, ueye.InitCamera)

        ## After Init, the camera is in freerun mode (enabled)
        self.enabled = True
        self._sensor_shape = self._read_sensor_shape() # type: Tuple[int, int]
        self._set_our_default_state()

        ## After Init, the camera is in freerun mode which we consider
        ## enabled.  But after construction, the device must be in
        ## disabled mode.
        self.disable()


    def _set_our_default_state(self) -> None:
        self.set_trigger(microscope.devices.TriggerType.SOFTWARE,
                         microscope.devices.TriggerMode.ONCE)

        ## XXX: we don't know what colourmode should be default.  We
        ## do need to change it because by default it's not even a
        ## grayscale colourmode.  So try all greyscale modes, starting
        ## with the highest bit depth.

        ## There's no function to find the supported colormodes, we
        ## need to try and see what works.
        for mode in (ueye.CM_MONO16, ueye.CM_MONO12, ueye.CM_MONO10,
                     ueye.CM_MONO8):
            status = ueye.SetColorMode(self._handle, mode)
            if status == ueye.SUCCESS:
                break
            elif status == ueye.INVALID_COLOR_FORMAT:
                continue # try next mode
            else:
                raise RuntimeError('failed to set color mode (error code %d)'
                                   % status)
        else:
            raise RuntimeError('no colormode of interest is supported')

        self.prepare-ring-buffer()
        # for buffer in self._
        # ## Having a fixed buffer that we keep reusing is good enough
        # ## while we don't support ROIs, binning, and hardware trigges.
        # colourmode = ueye.SetColorMode(self._handle, ueye.GET_COLOR_MODE)
        # dtype = _COLOURMODE_TO_DTYPE[colourmode]
        # self._buffer = np.empty(self._sensor_shape[::-1], dtype=dtype)
        # buffer_p = self._buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_char))
        # mem_id = ctypes.c_int()
        # status = ueye.SetAllocatedImageMem(self._handle, *self._sensor_shape,
        #                                    self._buffer.itemsize * 8, buffer_p,
        #                                    mem_id)
        # if status != ueye.SUCCESS:
        #     raise RuntimeError()
        # status = ueye.SetImageMem(self._handle, buffer_p, mem_id)
        # if status != ueye.SUCCESS:
        #     raise RuntimeError()


    def initialize(self) -> None:
        pass # Already done in __init__


    def __del__(self):
        ## FIXME: we shouldn't need to do this.  But the parent
        ## classes destructors will call disable() and then
        ## enable(). But if __init__ failed for some reason, then
        ## those methods will also fail, so we need to prevent those
        ## errors.  This only works because once we have a valid
        ## handler we set enabled to something.
        if self.enabled is not None:
            super().__del__()


    def _on_shutdown(self) -> None:
        status = ueye.ExitCamera(self._handle)
        if status != ueye.SUCCESS:
            ## If we fail to shutdown, it may be because it is already closed.
            ## FIXME: Device.shutdown should be the one checking this,
            ## before calling _on_shutdown()
            if self._is_open():
                raise RuntimeError('failed to shutdown camera (error code %d)'
                                       % status)


    def enable(self) -> None:
        ## FIXME: parent only sets to return of _on_enable, but should
        ## probably do it unless there's an error?
        super().enable()
        self.enabled = True


    def _on_enable(self) -> None:
        ## FIXME: if a software trigger was sent while the camera was
        ## disable, the acquisition will happen now.  Maybe if we free
        ## the image memory during disable, and only set it again
        ## during enable, we can work around that.
        if self._supports_standby():
            status = ueye.CameraStatus(self._handle, ueye.STANDBY, ueye.FALSE)
            if status != ueye.SUCCESS:
                raise RuntimeError('failed to enter standby')


    def _on_disable(self) -> None:
        if not self.enabled:
            ## TODO: this should probably happen in Device.disable
            return
        if self._supports_standby():
            status = ueye.CameraStatus(self._handle, ueye.STANDBY, ueye.TRUE)
            if status != ueye.SUCCESS:
                raise RuntimeError('failed to enter standby')
            self.enabled = False


    def get_exposure_time(self) -> float:
        time_msec = ctypes.c_double()
        ## We do the whole casting of the pointer to void_p the hard
        ## way so that it works fine in our mocked libs.  If we figure
        ## out a way to do the right thing on MockCFuncPtr this could
        ## be simplified.
        status = ueye.Exposure(self._handle, ueye.EXPOSURE_CMD.GET_EXPOSURE,
                               ctypes.cast(ctypes.byref(time_msec),
                                           ctypes.c_void_p),
                               ctypes.sizeof(time_msec))
        if status != ueye.SUCCESS:
            raise RuntimeError('failed to to read exposure time')
        return (time_msec.value /1000.0)


    def set_exposure_time(self, value: float) -> None:
        ## TODO: The range of valid exposure times is dependent on the
        ## pixel clock, which is also dependent on the colourmode, and
        ## the framerate.  These are all configurable.  The camera we
        ## have has discrete pixel clocks, so we need to get all of
        ## them.  I guess in theory we should find the highest pixel
        ## clock that provides the required exposure time since that
        ## will give the highest precision on the exposure time
        ## itself.  For example, with pixel clock at 30MHz and
        ## framerate of 50 fps, the exposure time is between 0.09 and
        ## 150 milliseconds while with pixel clock at 474 MHz the
        ## range is between 0.02 and 10.14 milliseconds.
        raise NotImplementedError()


    def _get_sensor_shape(self) -> Tuple[int, int]:
        return self._sensor_shape


    def _get_roi(self) -> Tuple[int, int, int, int]:
        return (0, 0, *self._sensor_shape)
        raise NotImplementedError()

    def _set_roi(self, left: int, top: int, width: int, height: int) -> None:
        raise NotImplementedError()


    def _get_binning(self) -> microscope.devices.Binning:
        ## TODO: needs testing because our camera does not support binning
        binning = ueye.SetBinning(self._handle, ueye.GET_BINNING)
        h_bin = binning & ueye.BINNING_MASK_HORIZONTAL
        v_bin = binning & ueye.BINNING_MASK_VERTICAL
        return microscope.devices.Binning(h=_FLAG_TO_HORZ_BINNING[h_bin],
                                          v=_FLAG_TO_VERT_BINNING[v_bin])

    def _set_binning(self, h_bin: int, v_bin: int) -> None:
        ## TODO: needs actual testing because our cameras do not
        ## support binning at all.
        try:
            h_bits = _HORIZONTAL_BINNING_TO_BITS[h_bin]
            v_bits = _VERTICAL_BINNING_TO_BITS[v_bin]
        except KeyError:
            raise ValueError('unsupported binning mode %dx%d' % (h_bin, v_bin))

        ## Even if the SDK has support for this binning mode, the
        ## camera itself may not support it.
        binning_mask = h_bits & v_bits
        supported = ueye.SetBinning(self._handle, ueye.GET_SUPPORTED_BINNING)
        if (supported & binning_mask) != binning_mask:
            raise ValueError('unsupported binning mode %dx%d' % (h_bin, v_bin))

        status = ueye.SetBinning(self._handle, binning_mask)
        if status != ueye.IS_SUCCESS:
            raise RuntimeError('Failed to set binning')

        ## TODO: Changing binning affects exposure time, so we need to
        ## set it again to whatever was before.  When we find out how
        ## that works.
        return None


    def get_sensor_temperature(self) -> float:
        """Return temperature of camera sensor in degrees Celsius.

        Not all cameras will have a temperature sensor.  Documentation
        says only USB3 and GigE uEye cameras.
        """
        device_info = ueye.DEVICE_INFO()
        status = ueye.DeviceInfo(self._handle.value | ueye.USE_DEVICE_ID,
                                 ueye.DEVICE_INFO_CMD_GET_DEVICE_INFO,
                                 ctypes.byref(device_info),
                                 ctypes.sizeof(device_info))
        if status != ueye.SUCCESS:
            raise RuntimeError('failed to get device info')

        ## Documentation for wTemperature (uint16_t)
        ##   Bit 15: algebraic sign
        ##   Bit 14...11: filled according to algebraic sign
        ##   Bit 10...4: temperature (places before the decimal point)
        ##   Bit 3...0: temperature (places after the decimal point)
        ##
        ## We have no clue what to do with bits 14...11.
        bits = device_info.infoDevHeartbeat.wTemperature
        sign = bits >> 15
        integer_part = bits >> 4 & 0b111111
        fractional_part = bits & 0b1111
        return ((-1)**sign) * float(integer_part) + (fractional_part/16.0)


    def set_trigger(self, ttype, tmode) -> None:
        if ttype == microscope.devices.TriggerType.SOFTWARE:
            status = ueye.SetExternalTrigger(self._handle,
                                             ueye.SET_TRIGGER_SOFTWARE)
            if status != ueye.SUCCESS:
                raise RuntimeError('failed to set software trigger mode')
        else:
            ## TODO: need to try this.  In Theory should be easy.
            raise NotImplementedError()

        self._trigger_type = ttype

        if tmode == microscope.devices.TriggerMode.ONCE:
            pass
        else:
            ## TODO: not clear what the camera supports.  See the
            ## "Camera basics > Operating Modes > Trigger mode" and
            ## the "Programming > "How to proceed > Capturing images"
            ## sections on the SDK manual.
            raise NotImplementedError()

        self._trigger_mode = tmode

    def get_cycle_time(self) -> float:
        ## It is possible to set a delay time between the arrival of a
        ## trigger signal and the start of exposure.  Because we don't
        ## have a method for the user to set it, and by default it is
        ## set to zero, we don't even bother to read it.

        ## From "Camera basics > Operating modes > Trigger mode":
        ##
        ## The time required for capturing a frame in trigger mode can
        ## be approximated with the following formula:
        ##
        ##     t_capture = exposure_time + (1 / max_frame_rate)
        ##     t_capture = exposure_time + (1 / (1 / min_frame_duration))
        ##     t_capture = exposure_time + min_frame_duration
        min_frame_duration = ctypes.c_double()
        max_frame_duration = ctypes.c_double()
        increment = ctypes.c_double()
        status = ueye.GetFrameTimeRange(self._handle, min_frame_duration,
                                        max_frame_duration, increment)
        if status != ueye.SUCCESS:
            raise RuntimeError()
        return self.get_exposure_time() +  min_frame_duration.value


    def _fetch_data(self) -> typing.Optional[np.ndarray]:
        ## FIXME: this is enough for software trigger and "slow"
        ## acquisition rates.  To achive faster speeds we need to set
        ## a ring buffer and maybe consider making use of freerun
        ## mode.
        status = ueye.WaitEvent(self._handle, ueye.SET_EVENT_FRAME, 1)
        if status == ueye.TIMED_OUT:
            return None
        elif status == ueye.SUCCESS:
            data = self.read-next-in-buffer
            data = self._buffer.copy()
            status = ueye.DisableEvent(self._handle, ueye.SET_EVENT_FRAME)
            if status != ueye.SUCCESS:
                raise RuntimeError('failed to disable event')
            return data
        else:
            ## Does this fails if we never set a an event in the first place?
            raise RuntimeError('failed waiting for new image (error %d)'
                               % status)


    def trigger(self) -> None:
        if self._trigger_type != microscope.devices.TriggerType.SOFTWARE:
            raise RuntimeError("current trigger type is '%s', not SOFTWARE"
                               % self._trigger_type)
        ## XXX: to support START/STROBE modes, I think we need to call
        ## CaptureVideo instead.
        status = ueye.EnableEvent(self._handle, ueye.SET_EVENT_FRAME)
        if status != ueye.SUCCESS:
            raise RuntimeError()
        status = ueye.FreezeVideo(self._handle, ueye.DONT_WAIT)
        if status != ueye.SUCCESS:
            ## if status == 108, it's because there is no active memory
            raise RuntimeError('failed to give software trigger (error %d)'
                               % status)

    def soft_trigger(self) -> None:
        self.trigger()


    def abort(self):
        status = ueye.StopLiveVideo(self._handle, ueye.FORCE_VIDEO_STOP)
        _check_status(status, ueye.StopLiveVideo)


    def _is_open(self) -> bool:
        """Camera is open if it is not in closed mode, i.e., it is init"""
        ## IDS cameras have an internal device ID.  This device ID is
        ## generated by the driver depending on order of connection
        ## and camera type.  This device ID is not persistent.
        ##
        ## There is also a camera handle used by the SDK to identify
        ## an open camera, i.e., a camera after InitCamera.  This
        ## camera handle is a uint32_t.
        ##
        ## Technically, it is not documented that the device ID and
        ## the camera handle are the same value.  However, our
        ## experience is that this is true.
        for info in _get_info_of_all_cameras():
            if info.dwDeviceID == self._handle.value:
                return info.dwInUse == 1
        else:
            raise RuntimeError('unable to find info on our camera')


    def _supports_standby(self) -> bool:
        return ueye.CameraStatus(self._handle, ueye.STANDBY_SUPPORTED,
                                 ueye.GET_STATUS) == ueye.TRUE


    def _read_sensor_shape(self) -> Tuple[int, int]:
        sensor_info = ueye.SENSORINFO()
        status = ueye.GetSensorInfo(self._handle, ctypes.byref(sensor_info))
        _check_status(status, ueye.GetSensorInfo)
        return (sensor_info.nMaxWidth, sensor_info.nMaxHeight)


_FLAG_TO_HORZ_BINNING = {
    0 : 1,
    ueye.BINNING_2X_HORIZONTAL : 2,
    ueye.BINNING_3X_HORIZONTAL : 3,
    ueye.BINNING_4X_HORIZONTAL : 4,
    ueye.BINNING_5X_HORIZONTAL : 5,
    ueye.BINNING_6X_HORIZONTAL : 6,
    ueye.BINNING_8X_HORIZONTAL : 8,
    ueye.BINNING_16X_HORIZONTAL : 16,
} # type: typing.Mapping[int, int]

_HORZ_BINNING_TO_FLAG = {v:k for k, v in _FLAG_TO_HORZ_BINNING.items()}


_FLAG_TO_VERT_BINNING = {
    0 : 1,
    ueye.BINNING_2X_VERTICAL : 2,
    ueye.BINNING_3X_VERTICAL : 3,
    ueye.BINNING_4X_VERTICAL : 4,
    ueye.BINNING_5X_VERTICAL : 5,
    ueye.BINNING_6X_VERTICAL : 6,
    ueye.BINNING_8X_VERTICAL : 8,
    ueye.BINNING_16X_VERTICAL : 16,
} # type: typing.Mapping[int, int]

_VERT_BINNING_TO_FLAG = {v:k for k, v in _FLAG_TO_VERT_BINNING.items()}


_COLOURMODE_TO_DTYPE = {
    ueye.CM_MONO10 : np.uint16,
    ueye.CM_MONO12 : np.uint16,
    ueye.CM_MONO16 : np.uint16,
    ueye.CM_MONO8 : np.uint8,
} # type: typing.Mapping[int, np.dtype]


def _number_of_ids_cameras() -> int:
    n_cameras = ctypes.c_int(0)
    status = ueye.GetNumberOfCameras(ctypes.byref(n_cameras))
    _check_status(status, ueye.GetNumberOfCameras)
    return n_cameras.value


def _get_info_of_all_cameras() -> typing.Iterable[ueye.UEYE_CAMERA_INFO]:
    n_cameras = _number_of_ids_cameras()
    camera_list = ueye.camera_list_factory(n_cameras)
    camera_list.dwCount = n_cameras
    status = ueye.GetCameraList(ctypes.cast(ctypes.byref(camera_list),
                                            ueye.PUEYE_CAMERA_LIST))
    _check_status(status, ueye.GetCameraList)
    return camera_list.uci


def _error_msg(status: int, func: typing.Callable) -> str:
    return "%s() failed (error code %d)" % (func.__name__, status)

def _check_status(status: int, func: typing.Callable) -> None:
    if status != ueye.SUCCESS:
        raise RuntimeError(_error_msg(status, func))


class _ImageMemory:
    def __init__(self, shape, colourmode):
        colourmode = ueye.SetColorMode(camera._handle, ueye.GET_COLOR_MODE)
        self._array = np.empty(camera._sensor_shape[::-1], dtype=dtype)
        self._pointer = self._array.ctypes.data_as(ctypes.POINTER(ctypes.c_char))
        self._mem_id = ctypes.c_int()
        status = ueye.SetAllocatedImageMem(camera._handle,
                                           *camera._sensor_shape,
                                           self._buffer.itemsize * 8, buffer_p,
                                           self._mem_id)
        if status != ueye.SUCCESS:
            raise RuntimeError()


class _CameraRingBuffer:
    """Keep reading the next item.

    The following actions will need to rebuild a new ring buffer:

    * Close/Open the camera
    * Change mode with different number of bytes
    * Change ROI

    The following is fine:
    * standby
    * change mode with same number of bytes
    """
    def __init__(self, camera: IDSuEye, length: int) -> None:
        if length < 1:
            raise ValueError('length must be a positive integer')
        self._camera = camera
        self._buffer = [None] * length
        self._next = 0

    def reset(self):
        colourmode = ueye.SetColorMode(self._camera._handle,
                                       ueye.GET_COLOR_MODE)
        dtype = _COLOURMODE_TO_DTYPE[colourmode]
        if self._buffer[0].itemsize != dtype().itemsize:
            make-new-buffer

        status = ueye.ClearSequence(self._camera._handle)
        _check_status(status, ueye.ClearSequence)

        for i in range(len(self._buffer)):
            ueye.AddToSequence(h, bufs_p[i], mems[i])

        # dtype = 
        # self._buffer = np.empty(self._sensor_shape[::-1], dtype=dtype)
        # buffer_p = self._buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_char))
        # mem_id = ctypes.c_int()
        # status = ueye.SetAllocatedImageMem(self._handle, *self._sensor_shape,
        #                                    self._buffer.itemsize * 8, buffer_p,
        #                                    mem_id)


    def read_next(self) -> np.ndarray:
        obj = self._buffer[self._next]
        self._next = (self._next +1) % len(self._buffer)
        return obj
