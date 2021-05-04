#!/usr/bin/env python3

## Copyright (C) 2020 Aurelien Barbotin
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

import ctypes
from ctypes import c_char_p, c_int, c_short
from ctypes.wintypes import DWORD


SDK = ctypes.CDLL("Thorlabs.MotionControl.DeviceManager.dll")


def make_prototype(name, argtypes, restype=c_short):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


BuildDeviceList = make_prototype("TLI_BuildDeviceList", [])

GetDeviceListSize = make_prototype("TLI_GetDeviceListSize", [])

GetDeviceListByTypeExt = make_prototype(
    "TLI_GetDeviceListByTypeExt", [c_char_p, DWORD, c_int]
)
