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

"""Wrapper to libueye.

There is the Python package pyueye which provides a ctypes wrapper to
libueye.  However, it's undocumented so we always need to go back to
the C documentation to know how to use it.  In addition, pyueye has
its own Python magic so we also need to read its source.  So we have
our own.  Our is also undocumented but has the minimum of Python magic
so reading the C documentation should be enough.

Function and macro constants names are the same as in the C library,
except the ``is_`` and ``IS_`` prefix which got removed.  In addition,
C enums form Python enums and the member names do not include the enum
name.

"""

import ctypes
import enum
import platform


if platform.system() == 'Windows':
    _bits, _linkage = platform.architecture()
    if _bits == '64bit':
        _libname = 'ueye_api_64'
    else:
        _libname = 'ueye_api'
else:
    _libname = 'libueye_api.so'

## TODO: seems like all functions are declared with __cdecl so we
## should be using CDLL not WinDLL, even on windows.  Right?  They
## only get declared with __stdcall if _IDS_VBSTD or _FALC_VBSTD are
## defined.
_SDK = ctypes.CDLL(_libname)


## Error codes
NO_SUCCESS = -1
SUCCESS = 0
INVALID_CAMERA_HANDLE = 1
IS_IO_REQUEST_FAILED = 2 # an io request to the driver failed
CANT_OPEN_DEVICE = 3 # returned by is_InitCamera
INVALID_MODE = 101
NO_ACTIVE_IMG_MEM = 108
TIMED_OUT = 122
INVALID_PARAMETER = 125
INVALID_BUFFER_SIZE = 159
INVALID_COLOR_FORMAT = 174

## Device enumeration
USE_DEVICE_ID = 0x8000

## live/freeze parameters
GET_LIVE = 0x8000
WAIT = 0x0001
DONT_WAIT = 0x0000
FORCE_VIDEO_STOP = 0x4000
FORCE_VIDEO_START = 0x4000
USE_NEXT_MEM = 0x8000


## Trigger modes
GET_EXTERNALTRIGGER = 0x8000
GET_TRIGGER_STATUS = 0x8001
GET_TRIGGER_MASK = 0x8002
GET_TRIGGER_INPUTS = 0x8003
GET_SUPPORTED_TRIGGER_MODE = 0x8004
GET_TRIGGER_COUNTER = 0x8000

SET_TRIGGER_MASK = 0x0100
SET_TRIGGER_CONTINUOUS = 0x1000
SET_TRIGGER_OFF = 0x0000
SET_TRIGGER_HI_LO = (SET_TRIGGER_CONTINUOUS | 0x0001)
SET_TRIGGER_LO_HI = (SET_TRIGGER_CONTINUOUS | 0x0002)
SET_TRIGGER_SOFTWARE = (SET_TRIGGER_CONTINUOUS | 0x0008)
SET_TRIGGER_HI_LO_SYNC = 0x0010
SET_TRIGGER_LO_HI_SYNC = 0x0020
SET_TRIGGER_PRE_HI_LO = (SET_TRIGGER_CONTINUOUS | 0x0040)
SET_TRIGGER_PRE_LO_HI = (SET_TRIGGER_CONTINUOUS | 0x0080)

GET_TRIGGER_DELAY = 0x8000
GET_MIN_TRIGGER_DELAY = 0x8001
GET_MAX_TRIGGER_DELAY = 0x8002
GET_TRIGGER_DELAY_GRANULARITY = 0x8003

## Timing
GET_PIXEL_CLOCK = 0x8000
GET_PIXEL_CLOCK_INC = 0x8005


## Binning
GET_BINNING = 0x8000
GET_SUPPORTED_BINNING = 0x8001
GET_BINNING_TYPE = 0x8002
GET_BINNING_FACTOR_HORIZONTAL = 0x8004
GET_BINNING_FACTOR_VERTICAL = 0x8008

BINNING_DISABLE = 0x00

BINNING_2X_VERTICAL = 0x0001
BINNING_2X_HORIZONTAL = 0x0002
BINNING_4X_VERTICAL = 0x0004
BINNING_4X_HORIZONTAL = 0x0008
BINNING_3X_VERTICAL = 0x0010
BINNING_3X_HORIZONTAL = 0x0020
BINNING_5X_VERTICAL = 0x0040
BINNING_5X_HORIZONTAL = 0x0080
BINNING_6X_VERTICAL = 0x0100
BINNING_6X_HORIZONTAL = 0x0200
BINNING_8X_VERTICAL = 0x0400
BINNING_8X_HORIZONTAL = 0x0800
BINNING_16X_VERTICAL = 0x1000
BINNING_16X_HORIZONTAL = 0x2000

BINNING_MASK_VERTICAL = (BINNING_2X_VERTICAL
                         | BINNING_3X_VERTICAL
                         | BINNING_4X_VERTICAL
                         | BINNING_5X_VERTICAL
                         | BINNING_6X_VERTICAL
                         | BINNING_8X_VERTICAL
                         | BINNING_16X_VERTICAL)
BINNING_MASK_HORIZONTAL = (BINNING_2X_HORIZONTAL
                           | BINNING_3X_HORIZONTAL
                           | BINNING_4X_HORIZONTAL
                           | BINNING_5X_HORIZONTAL
                           | BINNING_6X_HORIZONTAL
                           | BINNING_8X_HORIZONTAL
                           | BINNING_16X_HORIZONTAL)


## Pixel formats
GET_COLOR_MODE = 0x8000

CM_FORMAT_PLANAR = 0x2000
CM_FORMAT_MASK = 0x2000

CM_ORDER_BGR = 0x0000
CM_ORDER_RGB = 0x0080
CM_ORDER_MASK = 0x0080

CM_SENSOR_RAW8 = 11
CM_SENSOR_RAW10 = 33
CM_SENSOR_RAW12 = 27
CM_SENSOR_RAW16 = 29
CM_MONO8 = 6
CM_MONO10 = 34
CM_MONO12 = 26
CM_MONO16 = 28

CM_BGR5_PACKED = (3 | CM_ORDER_BGR)

CM_BGR565_PACKED = (2 | CM_ORDER_BGR)

CM_RGB8_PACKED = (1 | CM_ORDER_RGB)
CM_BGR8_PACKED = (1 | CM_ORDER_BGR)

CM_RGBA8_PACKED = (0 | CM_ORDER_RGB)
CM_BGRA8_PACKED = (0 | CM_ORDER_BGR)

CM_RGBY8_PACKED = (24 | CM_ORDER_RGB)
CM_BGRY8_PACKED = (24 | CM_ORDER_BGR)

CM_RGB10_PACKED = (25 | CM_ORDER_RGB)
CM_BGR10_PACKED = (25 | CM_ORDER_BGR)

CM_RGB10_UNPACKED = (35 | CM_ORDER_RGB)
CM_BGR10_UNPACKED = (35 | CM_ORDER_BGR)

CM_RGB12_UNPACKED = (30 | CM_ORDER_RGB)
CM_BGR12_UNPACKED = (30 | CM_ORDER_BGR)

CM_RGBA12_UNPACKED = (31 | CM_ORDER_RGB)
CM_BGRA12_UNPACKED = (31 | CM_ORDER_BGR)

CM_JPEG = 32

CM_UYVY_PACKED = 12
CM_UYVY_MONO_PACKED = 13
CM_UYVY_BAYER_PACKED = 14

CM_CBYCRY_PACKED = 23

CM_RGB8_PLANAR = (1 | CM_ORDER_RGB | CM_FORMAT_PLANAR)

CM_ALL_POSSIBLE = 0xFFFF
CM_MODE_MASK = 0x007F


## Event constants
SET_EVENT_FRAME = 2


## Camera info constants
GET_STATUS = 0x8000
STANDBY = 24
STANDBY_SUPPORTED = 25


DEVICE_INFO_CMD_GET_DEVICE_INFO = 0x02010001

class EXPOSURE_CMD(enum.IntEnum):
    GET_CAPS = 1
    GET_EXPOSURE_DEFAULT = 2
    GET_EXPOSURE_RANGE_MIN = 3
    GET_EXPOSURE_RANGE_MAX = 4
    GET_EXPOSURE_RANGE_INC = 5
    GET_EXPOSURE_RANGE = 6
    GET_EXPOSURE = 7
    GET_FINE_INCREMENT_RANGE_MIN = 8
    GET_FINE_INCREMENT_RANGE_MAX = 9
    GET_FINE_INCREMENT_RANGE_INC = 10
    GET_FINE_INCREMENT_RANGE = 11
    SET_EXPOSURE = 12
    GET_LONG_EXPOSURE_RANGE_MIN = 13
    GET_LONG_EXPOSURE_RANGE_MAX = 14
    GET_LONG_EXPOSURE_RANGE_INC = 15
    GET_LONG_EXPOSURE_RANGE = 16
    GET_LONG_EXPOSURE_ENABLE = 17
    SET_LONG_EXPOSURE_ENABLE = 18
    GET_DUAL_EXPOSURE_RATIO_DEFAULT = 19
    GET_DUAL_EXPOSURE_RATIO_RANGE = 20
    GET_DUAL_EXPOSURE_RATIO = 21
    SET_DUAL_EXPOSURE_RATIO = 22


class PIXELCLOCK_CMD(enum.IntEnum):
    GET_NUMBER = 1
    GET_LIST = 2
    GET_RANGE = 3
    GET_DEFAULT = 4
    GET = 5
    SET = 6


TRUE = 1
FALSE = 0


## typedefs so our prototype calls can read, just like the ueye header
BOOL = ctypes.c_int32
BYTE = ctypes.c_ubyte
DWORD = ctypes.c_uint32
HWND = ctypes.c_void_p
INT = ctypes.c_int32
TCHAR = ctypes.c_char
UINT = ctypes.c_uint32
ULONG = ctypes.c_uint32
WORD = ctypes.c_uint16

CHAR = ctypes.c_char
HIDS = DWORD
IDSEXP = INT
IDSEXPUL = ULONG


class SENSORINFO(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ('SensorID', WORD),
        ('strSensorName', CHAR*32),
        ('nColorMode', ctypes.c_char),
        ('nMaxWidth', DWORD),
        ('nMaxHeight', DWORD),
        ('bMasterGain', BOOL),
        ('bRGain', BOOL),
        ('bGGain', BOOL),
        ('bBGain', BOOL),
        ('bGlobShutter', BOOL),
        ('wPixelSize', WORD),
        ('nUpperLeftBayerPixel', ctypes.c_char),
        ('Reserved', ctypes.c_char*13),
    ]

PSENSORINFO = ctypes.POINTER(SENSORINFO)


class UEYE_CAMERA_INFO(ctypes.Structure):
    _pack_ = 8
    _fields_ = [
        ('dwCameraID', DWORD),
        ('dwDeviceID', DWORD),
        ('dwSensorID', DWORD),
        ('dwInUse', DWORD),
        ('SerNo', CHAR*16),
        ('Model', CHAR*16),
        ('dwStatus', DWORD),
        ('dwReserved', DWORD*2),
        ('FullModelName', CHAR*32),
        ('dwReserved2', DWORD*5),
    ]

PUEYE_CAMERA_INFO = ctypes.POINTER(UEYE_CAMERA_INFO)


def _camera_list_type_factory(n_cameras: int):
    class _UEYE_CAMERA_LIST(ctypes.Structure):
        _pack_ = 8
        _fields_ = [
            ('dwCount', ULONG),
            ('uci', UEYE_CAMERA_INFO*n_cameras),
        ]
    return _UEYE_CAMERA_LIST

def camera_list_factory(n_cameras: int):
    """List of camera informations.

    The `is_GetCameraList` function makes use of the `struct array
    hack <http://www.c-faq.com/struct/structhack.html>`_ for the info
    of multiple cameras.  We want to use as little magic as possible
    in our wrapper so that we can just use the C documentation, but
    this hack does not work `unchanged in Python
    <https://stackoverflow.com/questions/51549340/python-ctypes-definition-with-c-struct-arrary>`_.
    The reason is that the array type in Python includes the array
    length which Python does check.  So use this instead::

        camera_list = ueye.camera_list_type_factory(n_cameras)()
        camera_list.dwCount = n_cameras
        GetCameraList(ctypes.cast(ctypes.byref(camera_list),
                                  ueye.PUEYE_CAMERA_LIST))

    """
    return _camera_list_type_factory(n_cameras)()

UEYE_CAMERA_LIST = _camera_list_type_factory(1)
PUEYE_CAMERA_LIST = ctypes.POINTER(UEYE_CAMERA_LIST)


class DEVICE_INFO_HEARTBEAT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('reserved_1', BYTE*24),
        ('dwRuntimeFirmwareVersion', DWORD),
        ('reserved_2', BYTE*8),
        ('wTemperature', WORD),
        ('wLinkSpeed_Mb', WORD),
        ('reserved_3', BYTE*6),
        ('wComportOffset', WORD),
        ('reserved', BYTE*200),
    ]


class DEVICE_INFO_CONTROL(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('dwDeviceId', DWORD),
        ('reserved', BYTE*148),
    ]


class DEVICE_INFO(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('infoDevHeartbeat', DEVICE_INFO_HEARTBEAT),
        ('infoDevControl', DEVICE_INFO_CONTROL),
        ('reserved', BYTE*240),
    ]



def prototype(name, argtypes, restype=IDSEXP):
    func = getattr(_SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


CameraStatus = prototype('is_CameraStatus', [HIDS, INT, ULONG], IDSEXPUL)

DeviceInfo = prototype('is_DeviceInfo', [HIDS, UINT, ctypes.c_void_p, UINT])

DisableEvent = prototype('is_DisableEvent', [HIDS, INT])

EnableEvent = prototype('is_EnableEvent', [HIDS, INT])

ExitCamera = prototype('is_ExitCamera', [HIDS])

Exposure = prototype('is_Exposure', [HIDS, UINT, ctypes.c_void_p, UINT])

FreeImageMem = prototype('is_FreeImageMem',
                         [HIDS, ctypes.POINTER(ctypes.c_char), ctypes.c_int])

FreezeVideo = prototype('is_FreezeVideo', [HIDS, INT])

GetCameraList = prototype('is_GetCameraList', [PUEYE_CAMERA_LIST])

GetNumberOfCameras = prototype('is_GetNumberOfCameras', [ctypes.POINTER(INT)])

GetSensorInfo = prototype('is_GetSensorInfo', [HIDS, PSENSORINFO])

InitCamera = prototype('is_InitCamera', [ctypes.POINTER(HIDS), HWND])

PixelClock = prototype('is_PixelClock', [HIDS, UINT, ctypes.c_void_p, UINT])

SetAllocatedImageMem = prototype('is_SetAllocatedImageMem',
                                 [HIDS, INT, INT, INT,
                                  ctypes.POINTER(ctypes.c_char),
                                  ctypes.POINTER(ctypes.c_int)])

SetBinning = prototype('is_SetBinning', [HIDS, INT])

SetColorMode = prototype('is_SetColorMode', [HIDS, INT])

SetExternalTrigger = prototype('is_SetExternalTrigger', [HIDS, INT])

GetFrameTimeRange = prototype('is_GetFrameTimeRange',
                              [HIDS, ctypes.POINTER(ctypes.c_double),
                               ctypes.POINTER(ctypes.c_double),
                               ctypes.POINTER(ctypes.c_double)])

SetImageMem = prototype('is_SetImageMem',
                        [HIDS, ctypes.POINTER(ctypes.c_char), ctypes.c_int])

StopLiveVideo = prototype('is_StopLiveVideo', [HIDS, INT])

AddToSequence = prototype('is_AddToSequence', [HIDS,
                                               ctypes.POINTER(ctypes.c_char),
                                               ctypes.c_int])

ClearSequence = prototype('is_ClearSequence', [HIDS])


if platform.system() != 'Windows':
    WaitEvent = prototype('is_WaitEvent', [HIDS, INT, INT])
