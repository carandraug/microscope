#!/usr/bin/env python3

## Copyright (C) 2020 David Miguel Susano Pinto <carandraug@gmail.com>
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

"""This module is deprecated and only kept for backwards compatibility.
"""

from microscope import ROI, AxisLimits, Binning, TriggerMode, TriggerType
from microscope.abc import Camera as CameraDevice
from microscope.abc import Controller as ControllerDevice
from microscope.abc import DataDevice, DeformableMirror, Device
from microscope.abc import FilterWheel as FilterWheelBase
from microscope.abc import FloatingDeviceMixin
from microscope.abc import LightSource as LaserDevice
from microscope.abc import SerialDeviceMixin as SerialDeviceMixIn
from microscope.abc import Stage as StageDevice
from microscope.abc import StageAxis
from microscope.abc import TriggerTargetMixin as TriggerTargetMixIn
from microscope.abc import keep_acquiring
from microscope.device_server import device
