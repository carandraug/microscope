# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 17:54:00 2020

@author: aurel

Wrapper to the Kinesis (thorlabs) C API for NanoMax stage
"""

import ctypes

from ctypes import c_char_p, c_int, c_short, c_bool, POINTER, c_double
from ctypes.wintypes import DWORD



#path = "Thorlabs.MotionControl.Benchtop.Piezo.dll"
SDK = ctypes.WinDLL("Thorlabs.MotionControl.Benchtop.StepperMotor.dll")
# SDK = ctypes.CDLL(path)

# from BMC stuff
RC = c_short  # enum for error codes
def make_prototype(name, argtypes, restype=RC):
    func = getattr(SDK, name)
    func.argtypes = argtypes
    func.restype = restype
    return func

TLI_BuildDeviceList = make_prototype("TLI_BuildDeviceList",[],restype=c_short)

TLI_GetDeviceListSize = make_prototype("TLI_GetDeviceListSize",[],restype=c_short)

TLI_GetDeviceListByTypeExt = make_prototype("TLI_GetDeviceListByTypeExt",[c_char_p,DWORD,c_int],restype=c_short)
# [receiveBuffer, sizeOfBuffer, typeID]

SBC_Open = make_prototype("SBC_Open", [c_char_p],restype = c_short)
# [serialNo]

SBC_StartPolling = make_prototype("SBC_StartPolling",[c_char_p,c_short,c_int], restype=c_bool)
# [serialNo, channel, milliseconds]
 
SBC_ClearMessageQueue = make_prototype("SBC_ClearMessageQueue",[c_char_p,c_short],restype = c_short)
# [serialNo, channel]

SBC_Home = make_prototype("SBC_Home",[c_char_p,c_short],restype = c_short)
# [serialNo, channel]

SBC_MoveToPosition = make_prototype("SBC_MoveToPosition",[c_char_p,c_short, c_int], restype = c_short)
# [serialnr, channel, index]

SBC_StopPolling = make_prototype("SBC_StopPolling",[c_char_p, c_short])
# [serialNo, channel]

SBC_Close = make_prototype("SBC_Close",[c_char_p])
# [serialNo]

def make_serialnr(sn):
    """Formatting the 8-digit int serial number (ex 70897524) for e.g SBC_Open"""
    return c_char_p(bytes(str(sn), "utf-8"))

# ----------- Untested methods ------------
SBC_getNumChannels = make_prototype("SBC_getNumChannels", [c_char_p],restype = c_short)
# [*serialNo]

SBC_GetRealValueFromDeviceUnit = make_prototype("SBC_GetRealValueFromDeviceUnit", 
                                [c_char_p, c_short, c_int, POINTER(c_double), c_int])
#[*serialNo, channel, device_unit, *real unit, unitType]

SBC_MoveRelative =  make_prototype("SBC_MoveRelative",[c_char_p, c_short, c_int])
#[*serialNo, channel, displacement]