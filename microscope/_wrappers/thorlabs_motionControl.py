# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 17:54:00 2020

@author: aurel

Wrapper to the Kinesis (thorlabs) C API for NanoMax stage
"""

import ctypes

from ctypes import c_char_p, c_int, c_short, c_bool, POINTER, c_double
from ctypes.wintypes import DWORD


# path = "Thorlabs.MotionControl.Benchtop.Piezo.dll"
SDK = ctypes.WinDLL("Thorlabs.MotionControl.Benchtop.StepperMotor.dll")
# SDK = ctypes.CDLL(path)

# from BMC stuff
RC = c_short  # enum for error codes


def make_prototype(name, argtypes, restype=RC):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func


TLI_BuildDeviceList = make_prototype(
    "TLI_BuildDeviceList", [], restype=c_short
)

TLI_GetDeviceListSize = make_prototype(
    "TLI_GetDeviceListSize", [], restype=c_short
)

TLI_GetDeviceListByTypeExt = make_prototype(
    "TLI_GetDeviceListByTypeExt", [c_char_p, DWORD, c_int], restype=c_short
)
# [receiveBuffer, sizeOfBuffer, typeID]

SBC_Open = make_prototype("SBC_Open", [c_char_p], restype=c_short)
# [serialNo]

SBC_StartPolling = make_prototype(
    "SBC_StartPolling", [c_char_p, c_short, c_int], restype=c_bool
)
# [serialNo, channel, milliseconds]

SBC_ClearMessageQueue = make_prototype(
    "SBC_ClearMessageQueue", [c_char_p, c_short], restype=c_short
)
# [serialNo, channel]

SBC_Home = make_prototype("SBC_Home", [c_char_p, c_short], restype=c_short)
# [serialNo, channel]

SBC_MoveToPosition = make_prototype(
    "SBC_MoveToPosition", [c_char_p, c_short, c_int], restype=c_short
)
# [serialnr, channel, index]

SBC_StopPolling = make_prototype("SBC_StopPolling", [c_char_p, c_short])
# [serialNo, channel]

SBC_Close = make_prototype("SBC_Close", [c_char_p])
# [serialNo]


def make_serialnr(sn):
    """Formatting the 8-digit int serial number (ex 70897524) for e.g SBC_Open"""
    return c_char_p(bytes(str(sn), "utf-8"))


# ----------- Untested methods ------------
SBC_getNumChannels = make_prototype(
    "SBC_getNumChannels", [c_char_p], restype=c_short
)
# [*serialNo]

SBC_GetRealValueFromDeviceUnit = make_prototype(
    "SBC_GetRealValueFromDeviceUnit",
    [c_char_p, c_short, c_int, POINTER(c_double), c_int],
)
# [*serialNo, channel, device_unit, *real unit, unitType]

SBC_MoveRelative = make_prototype(
    "SBC_MoveRelative", [c_char_p, c_short, c_int]
)
# [*serialNo, channel, displacement]

SBC_GetPosition = make_prototype("SBC_GetPosition", [c_char_p, c_short], c_int)
# [*serialNo, channel]

SBC_GetMotorTravelLimits = make_prototype(
    "SBC_GetMotorTravelLimits",
    [c_char_p, c_short, POINTER(c_double), POINTER(c_double)],
)
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
