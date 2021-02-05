#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 09:46:11 2021

@author: aurelien
"""
import microscope
import typing


try:
    import microscope._wrappers.thorlabs_motionControl as TMC
except Exception as e:
    raise microscope.LibraryLoadError(e) from e
    
import microscope.abc

from ctypes import c_char_p

class ThorlabsNanoMaxAxis(microscope.abc.StageAxis):
    def __init__(self, serial_number, axis):
        """Axis of stepper motor Thorlabs NanoMax stage
        Parameters:
            serial_number (c_char_p): the stage serial number
            axis (int): the index of the axis, starting from 1.
        """
        self.serial_number = serial_number
        self.axis = axis
        
    def limits(self):
        pass
    def move_by(self, delta):
        status = TMC.SBC_MoveRelative(self.serial_number,self.axis,delta)
        if status:
            raise microscope.DeviceError("TBD")
    def move_to(self, pos):
        # pos: int
        status = TMC.SBC_MoveToPosition(self.serial_number, self.axis, pos)
        if status:
            raise microscope.DeviceError("TBD")
            
    def position(self):
        pos = TMC.SBC_GetPosition(self.serial_number, self.axis)
        return pos
    
class ThorlabsNanoMax(microscope.abc.Stage):
    """A Thorlabs Nanomax stage. So far supports only 3-axis, stepper-motor stage"""
    def __init__(self, serial_number: str, **kwargs) -> None:
        super().__init__(**kwargs)
        
        self.serial_number = c_char_p(bytes(str(serial_number), "utf-8"))
        status = TMC.SBC_Open(self.serial_number)

        if status:
            raise microscope.InitialiseError(status)
        # populate axes dict
        self.n_axes = 3 # can be updated later
        axes_names = ["x","y","z"]
        self._axes = {}
        for j in range(self.n_axes):
            axn = axes_names[j]
            self._axes[axn]=ThorlabsNanoMaxAxis(self.serial_number,j+1)

    def enable(self):
        # homing
        # !!! Might need to wait for homing to finish axis by axis
        for channel_nr in range(self.n_axes):
            status = TMC.SBC_Home(self.serial_number, channel_nr+1)
            if status:
                raise microscope.DeviceError("TBD")
        
    
    def _do_shutdown(self):
        status = TMC.SBC_Close(self.serial_number)
        if status:
            raise microscope.DeviceError("Cannot close device")
        
    @property
    def axes(self):
        return self._axes
        
    def move_by(self, delta):
        for ax, delta in self.axes.items():
            self.axes[ax].move_by(delta)
            
    def move_to(self, position):
        for ax, delta in self.axes.items():
            self.axes[ax].move_to(delta)