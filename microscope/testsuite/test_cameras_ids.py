#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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

import ctypes
import inspect
import sys

from microscope._defs import ueye


class MockFuncPtr(object):
    """A mock for a C function.

    To identify where it is called unintentionally, this mock will raise
    :exc:`NotImplementedError` if it is called.  To make it callable,
    replace the :meth:`__call` method like so::

        >>> func = MockFuncPtr()
        >>> func()
        Traceback (most recent call last):
        ...
        NotImplementedError: call of mock function not yet implemented
        >>> func._call = lambda : ctypes.c_int(1)
        >>> func()
        c_int(1)

    The reason to replace `__call` instead of `__call__` is that
    implicit invocations of special methods are `not guaranteed to work
    correctly when defined in an object instance
    <https://docs.python.org/3/reference/datamodel.html#special-method-lookup>`_,
    i.e., patching `instance.__call__` may not affect `instance()`.
    This is at least true in CPython.

    .. note:
       This is meant to be a mock of `_FuncPtr` which is a class created
       on the fly in ctypes from the private `_ctypes._CFuncPtr`.
    """
    def __init__(self):
        self.argtypes = None
        self.restype = ctypes.c_int
    def _call(self, *args, **kwargs):
        raise NotImplementedError("call of mock function not yet implemented")
    def __call__(self, *args, **kwargs):
        return self._call(*args, **kwargs)


class MockSharedLib(object):
    """Base class for mock shared libraries.

    Subclasses must list the name of functions from the library it mocks
    in :attr:`functions`.

    Attributes:
        libs (list): list of library names (as passed to
            :class:`ctypes.CDLL`) that this class can mock.
        functions (list): list of of function names from the library to be
            mocked.
    """
    libs = []
    functions = []
    def __init__(self):
        for fname in self.functions:
            setattr(self, fname, MockFuncPtr())


class MockLibueye(MockSharedLib):
    """Mocks uEye API SDK for microscope.cameras.ids."""
    libs = ['libueye_api.so']
    functions = [
        'is_CameraStatus',
        'is_DeviceInfo',
        'is_ExitCamera',
        'is_GetCameraList',
        'is_GetNumberOfCameras',
        'is_GetSensorInfo',
        'is_InitCamera',
        'is_SetColorMode',
        'is_SetExternalTrigger',
    ]

    def __init__(self):
        super().__init__()
        self._id_to_camera = {} # type: Dict[int, IDSCamera]

        for fname in self.functions:
            mock_function_ptr = getattr(self, fname)
            mock_call = getattr(self, fname[3:], None)
            if mock_call is not None:
                mock_function_ptr._call = mock_call

    def plug_camera(self, camera) -> None:
        next_id = 1+ max(self._id_to_camera.keys(), default=0)
        self._id_to_camera[next_id] = camera

    def unplug_camera(self, camera) -> None:
        self._id_to_camera.pop(self.get_id_from_camera(camera))

    def get_next_available_camera(self):
        for device_id in sorted(self._id_to_camera):
            camera = self._id_to_camera[device_id]
            if camera.on_closed():
                return camera
        ## returns None if there is no available camera

    def get_id_from_camera(self, camera):
        device_ids = [i for i, c in self._id_to_camera.items() if c is camera]
        assert len(device_ids) == 1,'somehow we broke internal dict'
        return device_ids[0]

    def InitCamera(self, phCam, hWnd):
        if hWnd is not None:
            raise NotImplementedError('we only run in DIB mode')
        hCam = phCam._obj

        if hCam.value == 0:
            device_id = 0
        elif not (hCam.value & 0x8000):
            raise NotImplementedError("we don't init by camera id")
        else:
            device_id = hCam.value & (~0x8000)

        ## If any error happens, hCam is set to / remains zero.
        hCam.value = 0
        if device_id == 0:
            camera = self.get_next_available_camera()
            if camera is None:
                return 3 # IS_CANT_OPEN_DEVICE
        else:
            try:
                camera = self._id_to_camera[device_id]
            except KeyError: # no such device
                return 3 # IS_CANT_OPEN_DEVICE
        if camera.on_open():
            return 3 # IS_CANT_OPEN_DEVICE

        camera.to_freerun_mode()
        hCam.value = self.get_id_from_camera(camera)
        return 0 # IS_SUCCESS

    def CameraStatus(self, hCam, nInfo, ulValue):
        try:
            camera = self._id_to_camera[hCam.value]
        except KeyError:
            return 1 # IS_INVALID_CAMERA_HANDLE

        if nInfo == ueye.STANDBY_SUPPORTED:
            if ulValue == ueye.GET_STATUS:
                if camera.supports_standby():
                    return ueye.TRUE
                else:
                    return ueye.FALSE
            else:
                raise RuntimeError('for query, ulValue must be GET_STATUS')

        elif nInfo == ueye.STANDBY:
            if ulValue == ueye.FALSE:
                camera.to_freerun_mode()
            elif ulValue == ueye.TRUE:
                camera.to_standby_mode()
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()
        return ueye.SUCCESS

    def DeviceInfo(self):
        pass

    def ExitCamera(self, hCam):
        try:
            camera = self._id_to_camera[hCam.value]
        except KeyError:
            return 1 # IS_INVALID_CAMERA_HANDLE
        if camera.on_closed():
            return 1 # IS_INVALID_CAMERA_HANDLE
        camera.to_closed_mode()
        return 0 # IS_SUCCESS

    def GetCameraList(self, pucl):
        n_cameras = len(self._id_to_camera)

        ## If dwCount is zero, then it's a request to only get the
        ## number of devices and not to fill the rest of the device
        ## info.
        if pucl.contents.dwCount == 0:
            pucl.contents.dwCount = n_cameras
            return 0

        ## The SDK makes use of a nasty struct array hack.  Fail if we
        ## forget to do the proper casting.  If the casting was done
        ## right, then uci will always have a length of one.
        if len(pucl.contents.uci) != 1:
            raise RuntimeError('pucl need to be cast to PUEYE_CAMERA_LIST')

        ## The SDK can handle this case.  However, if we ever got to
        ## that state, we are already doing something wrong.
        if pucl.contents.dwCount != n_cameras:
            raise NotImplementedError('incorrect number of devices')

        uci_correct_type = ueye.UEYE_CAMERA_INFO * n_cameras
        full_uci = ctypes.cast(ctypes.byref(pucl.contents.uci),
                               ctypes.POINTER(uci_correct_type))
        for camera, uci in zip(self._id_to_camera.values(), full_uci.contents):
            uci.dwCameraID = camera.camera_id
            uci.dwDeviceID = self.get_id_from_camera(camera)
            uci.dwSensorID = camera.sensor_id
            uci.dwInUse = 1 if camera.on_open() else 0
            uci.SerNo = camera.serial_number.encode()
            uci.Model = camera.model.encode()
            uci.FullModelName = camera.full_model_name.encode()
        return 0


    def GetNumberOfCameras(self, pnNumCams):
        pnNumCams._obj.value = len(self._id_to_camera)
        return 0


    def GetSensorInfo(self, hCam, pInfo):
        try:
            camera = self._id_to_camera[hCam.value]
        except KeyError:
            return 1

        if camera.on_closed():
            return 1

        pInfo._obj.SensorID = camera.sensor_id
        pInfo._obj.strSensorName = camera.sensor_name.encode()
#        pInfo._obj.nColorMode = camera. # TODO: colormode
        pInfo._obj.nMaxWidth = camera.width
        pInfo._obj.nMaxHeight = camera.height
        pInfo._obj.wPixelSize = int(camera.pixel_size * 100)
        return 0

## Create a map of library names (as they would be named when
## constructing CDLL in any supported OS), to the mock shared library.
_lib_to_mock = dict()
for _, _cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if issubclass(_cls, MockSharedLib):
        for _lib in _cls.libs:
            _lib_to_mock[_lib] = _cls


class CDLL(ctypes.CDLL):
    """A replacement for ctypes.CDLL that will link our mock libraries.
    """
    def __init__(self, name, *args, **kwargs):
        if _lib_to_mock.get(name) is not None:
            self._name = name
            self._handle = _lib_to_mock[name]()
        else:
            super(CDLL, self).__init__(name, *args, **kwargs)

    def __getattr__(self, name):
        if isinstance(self._handle, MockSharedLib):
            return getattr(self._handle, name)
        else:
            super(CDLL, self).__getattr__(name)
