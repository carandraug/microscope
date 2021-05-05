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

"""Wrapper to Thorlabs.MotionControl.Benchtop.StepperMotor.dll."""

import ctypes
from ctypes import c_bool, c_char_p, c_double, c_int, c_short
from ctypes.wintypes import DWORD


SDK = ctypes.CDLL("Thorlabs.MotionControl.Benchtop.StepperMotor.dll")


# enums
MOTOR_HOMED
MOTOR_HOMING


def prototype(name, argtypes, restype=c_short):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


Close = prototype("SBC_Close", [c_char_p])

GetMotorTravelLimits = prototype(
    "SBC_GetMotorTravelLimits",
    [c_char_p, c_short, ctypes.POINTER(c_double), ctypes.POINTER(c_double)],
)

GetPosition = prototype("SBC_GetPosition", [c_char_p, c_short], c_int)

GetStatusBits = prototype("SBC_GetStatusBits", [c_char_p, c_short], DWORD)

Home = prototype("SBC_Home", [c_char_p, c_short])

IsChannelValid = prototype("SBC_IsChannelValid", [c_char_p, c_short], c_bool)

LoadSettings = prototype("SBC_LoadSettings", [c_char_p, c_short], c_bool)

MoveRelative = prototype("SBC_MoveRelative", [c_char_p, c_short, c_int])

MoveToPosition = prototype("SBC_MoveToPosition", [c_char_p, c_short, c_int])

Open = prototype("SBC_Open", [c_char_p])

RequestStatusBits = prototype("SBC_RequestStatusBits", [c_char_p, c_short])


def make_serialnr(sn):
    """Formatting the 8-digit int serial number (ex 70897524) for e.g SBC_Open"""
    return c_char_p(bytes(str(sn), "utf-8"))


# ----------- Untested methods ------------
SBC_getNumChannels = prototype(
    "SBC_getNumChannels", [c_char_p], restype=c_short
)
# [*serialNo]

SBC_GetRealValueFromDeviceUnit = prototype(
    "SBC_GetRealValueFromDeviceUnit",
    [c_char_p, c_short, c_int, POINTER(c_double), c_int],
)
# [*serialNo, channel, device_unit, *real unit, unitType]

# [*serialNo, channel, displacement]

# [*serialNo, channel]

# [serial_number, channel, min_position, max_position]


errors_dict = {
    1: "FT_InvalidHandle - The FTDI functions have not been initialized",
    2: "FT_DeviceNotFound - The Device could not be found",
    3: "FT_DeviceNotOpened - The Device must be opened before it can be accessed",
    4: "FT_IOError - An I/O Error has occured in the FTDI chip.",
    5: "FT_InsufficientResources - There are Insufficient resources\
to run this application. ",
    6: "FT_InvalidParameter - An invalid parameter has been supplied\
to the device. ",
    7: "FT_DeviceNotPresent - The Device is no longer present ",
    8: "FT_IncorrectDevice - The device detected does not match that expected",
    16: "FT_NoDLLLoaded - The library for this device could not be found",
    17: "FT_NoFunctionsAvailable - No functions available for this device",
    18: "FT_FunctionNotAvailable - The function is not available for this device",
    19: "FT_BadFunctionPointer - Bad function pointer detected",
    20: "FT_GenericFunctionFail - The function failed to complete succesfully",
    21: "FT_SpecificFunctionFail - The function failed to complete succesfully",
    32: "TL_ALREADY_OPEN - Attempt to open a device that was already open",
    33: "TL_NO_RESPONSE - The device has stopped responding. ",
    34: "TL_NOT_IMPLEMENTED - This function has not been implemented. ",
    35: "TL_FAULT_REPORTED - The device has reported a fault.",
    36: "TL_INVALID_OPERATION - The function could not be completed at this time.",
    41: "TL_FIRMWARE_BUG - The firmware has thrown an error ",
    42: "TL_INITIALIZATION_FAILURE - The device has failed to initialize ",
    43: "TL_INVALID_CHANNEL - An Invalid channel address was supplied ",
    37: "TL_UNHOMED - The device cannot perform this function until it has been Homed. ",
    38: "TL_INVALID_POSITION - The function cannot be performed as\
it would result in an illegal position.",
    39: "TL_INVALID_VELOCITY_PARAMETER - An invalid velocity parameter\
was supplied. The velocity must be greater than zero. ",
    44: "TL_CANNOT_HOME_DEVICE - This device does not support Homing\
Check the Limit switch parameters are correct",
    45: "TL_JOG_CONTINOUS_MODE - An invalid jog mode was supplied\
for the jog function. ",
    46: "TL_NO_MOTOR_INFO - There is no Motor Parameters available to convert\
Real World Units. ",
    47: "TL_CMD_TEMP_UNAVAILABLE - Command temporarily unavailable, Device may\
be busy.",
}
