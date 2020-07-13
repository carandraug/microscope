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

"""Prior controllers

Standard mode only (compatibility mode no).


WIP until we figure interface to stages and multi device devices.

Issues:

multiple filterheels are fine.  However, the same filter position has
different numbers dependening on the connector.  For example, on an 8
filter filterwheel, filter position 8 when connected to filter 1 and
2, is filter position 4 when connected to A axis (filter 3).

filter 3 is when connected to A axis.
"""

import contextlib
import math
import re
import threading
import typing

import serial

import microscope.devices


class _ProScanIIIConnection:
    """Connection to a Prior ProScanIII and wrapper to its commands.

    Devices that are controlled by the same controller should share
    the same connection instance to ensure correct synchronization of
    communications from different threads.  This ensures that commands
    for different devices, or replies from different devices, don't
    get entangled.

    This class also implements the logic to parse and validate
    commands so it can be shared between multiple devices.

    """
    def __init__(self, port: str, baudrate: int, timeout: float) -> None:
        # From the technical datasheet: 8 bit word 1 stop bit, no
        # parity no handshake, baudrate options of 9600, 19200, 38400,
        # 57600 and 115200.
        self._serial = serial.Serial(port=port, baudrate=baudrate,
                                     timeout=timeout, bytesize=serial.EIGHTBITS,
                                     stopbits=serial.STOPBITS_ONE,
                                     parity=serial.PARITY_NONE, xonxoff=False,
                                     rtscts=False, dsrdtr=False)
        self._lock = threading.RLock()

        with self._lock:
            # We do not use the general get_description() here because
            # if this is not a ProScan device it would never reach the
            # '\rEND\r' that signals the end of the description.
            self.command(b'?')
            answer = self.readline()
            if answer != b'PROSCAN INFORMATION\r':
                self.read_until_timeout()
                ## If we got no answer at allanswer is empty, maybe
                ## there is no such prt at all.  That's what we get
                ## when device is off.
                raise RuntimeError('Failed to identify a ProScanIII device on'
                                   ' port %s.  \'?\' command returned \'%s\''
                                   % (port, answer.decode()))
            # A description ends with END on its own line.
            line = self._serial.read_until(b'\rEND\r')
            if not line.endswith(b'\rEND\r'):
                raise RuntimeError('Failed to find end of the \'?\' command')


    def command(self, command: bytes) -> None:
        """Send command to device."""
        with self._lock:
            self._serial.write(command + b'\r')

    def readline(self) -> bytes:
        """Read a line from the device connection."""
        with self._lock:
            return self._serial.read_until(b'\r')

    def read_until_timeout(self) -> None:
        """Read until timeout; used to clean buffer if in an unknown state."""
        with self._lock:
            self._serial.flushInput()
            while len(self._serial.readline()) != 0:
                continue

    def _command_and_validate(self, command: bytes, expected: bytes) -> None:
        """Send command and raise exception if answer is unexpected"""
        with self._lock:
            answer = self.get_command(command)
            if answer != expected:
                self.read_until_timeout()
                raise RuntimeError("command '%s' failed (got '%s')"
                                   % (command.decode(), answer.decode()))

    def get_command(self, command: bytes) -> bytes:
        """Send get command and return the answer."""
        with self._lock:
            self.command(command)
            return self.readline()

    def move_command(self, command: bytes) -> None:
        """Send a move command and check return value."""
        # Movement commands respond with an R at the end of move.
        # Once a movement command is issued the application should
        # wait until the end of move R response is received before
        # sending any further commands.
        # TODO: this times 10 is a bit arbitrary.
        with self.changed_timeout(10 * self._serial.timeout):
            self._command_and_validate(command, b'R\r')

    def set_command(self, command: bytes) -> None:
        """Send a set command and check return value."""
        # Property type commands that set certain status respond with
        # zero.  They respond with a zero even if there are invalid
        # arguments in the command.
        self._command_and_validate(command, b'0\r')

    def get_description(self, command: bytes) -> bytes:
        """Send a get description command and return it."""
        with self._lock:
            self.command(command)
            return self._serial.read_until(b'\rEND\r')


    @contextlib.contextmanager
    def changed_timeout(self, new_timeout: float):
        previous = self._serial.timeout
        try:
            self._serial.timeout = new_timeout
            yield
        finally:
            self._serial.timeout = previous


    def assert_filterwheel_number(self, number: int) -> None:
        assert number > 0 and number < 4

    def assert_axis_name(self, name: str) -> None:
        assert len(name) == 1 and name in 'SXYZA'


    def _has_thing(self, command: bytes, expected_start: bytes) -> bool:
        # Use the commands that returns a description string to find
        # whether a specific device is connected.
        with self._lock:
            description = self.get_description(command)
            if not description.startswith(expected_start):
                self.read_until_timeout()
                raise RuntimeError("Failed to get description '%s' (got '%s')"
                                   % (command.decode(), description.decode()))
        return not description.startswith(expected_start + b'NONE\r')


    def has_filterwheel(self, number: int) -> bool:
        self.assert_filterwheel_number(number)
        # We use the 'FILTER w' command to check if there's a filter
        # wheel instead of the '?' command.  The reason is that the
        # third filter wheel, named "A AXIS" on the controller box and
        # "FOURTH" on the output of the '?' command, can be used for
        # non filter wheels.  We hope that 'FILTER 3' will fail
        # properly if what is connected to "A AXIS" is not a filter
        # wheel.
        return self._has_thing(b'FILTER %d' % number, b'FILTER_%d = ' % number)

    def has_stage(self) -> bool:
        return self._has_thing(b'STAGE', b'STAGE = ')


    def get_n_filter_positions(self, number: int) -> int:
        self.assert_filterwheel_number(number)
        answer = self.get_command(b'FPW %d' % number)
        return int(answer)

    def get_filter_position(self, number: int) -> int:
        self.assert_filterwheel_number(number)
        answer = self.get_command(b'7 %d F' % number)
        return int(answer)

    def set_filter_position(self, number: int, pos: int) -> None:
        self.assert_filterwheel_number(number)
        self.move_command(b'7 %d %d' % (number, pos))


    def go_relative(self, x: int, y: int, z: int = 0) -> None:
        self.move_command(b'GR %d %d %d' % (x, y, z))

    def go(self, xpos: int, ypos: int, zpos: int = 0) -> None:
        self.move_command(b'G %d %d %d' % (xpos, ypos, zpos))

    def go_x(self, pos: int) -> None:
        self.move_command(b'GX %d' % pos)

    def go_y(self, pos: int) -> None:
        self.move_command(b'GY %d' % pos)


    def absolute_position(self) -> typing.Tuple[int, int, int]:
        """Return (x, y, z) absolute positions."""
        answer = self.get_command(b'P')
        positions = [int(p) for p in answer.split(b',')]
        assert len(positions) == 3
        return tuple(positions)

    def absolute_x_position(self) -> int:
        return int(self.get_command(b'PX'))

    def absolute_y_position(self) -> int:
        return int(self.get_command(b'PY'))


    def _enable_command(self, command: bytes, axis: str, mode: bool) -> None:
        self.assert_axis_name(axis)
        self.set_command(b'%s %s %d' % (command, axis.encode(), mode))

    def enable_encoder(self, axis: str, mode: bool) -> None:
        """Enable/disable encoder for given axis."""
        self._enable_command(b'ENCODER', axis, mode)

    def enable_servo(self, axis: str, mode: bool) -> None:
        """Enable/disable servo for given axis."""
        self._enable_command(b'SERVO', axis, mode)

    def is_limit_switch_active(self, axis: str, sign: int) -> bool:
        """Reports whether any limit switch is currently active.

        A limit switch is active if the switch is in contact with the
        axis hardware.

        Args:
            axis: name of the axis
            sign: +1 to check upper limit, -1 to check the lower
              limit.
        """
        if sign not in [-1, +1]:
            raise ValueError('sign must be -1 or +1')
        limits = bin(int(self.get_command(b'LMT'), 16))[2:].zfill(8)
        base_offset = {'X' : 7, 'Y' : 5, 'Z' : 3, '4th' : 1}
        offset = base_offset[axis]
        if sign == -1:
            offset -= 1
        return limits[offset] == '1'


class _ProScanIIIStageAxis(microscope.devices.StageAxis):
    def __init__(self, connection: _ProScanIIIConnection, name: str) -> None:
        super().__init__()
        if name not in ['X', 'Y']:
            raise ValueError('name must be X or Y')
        self._name = name
        self._conn = connection
        self._limits = None # type: typing.Optional[microscope.devices.AxisLimits]

        self._conn.enable_encoder(self._name, True)
        self._conn.enable_servo(self._name, False)

    def _do_enable(self) -> None:
        if self._limits is None:
            self._limits = self._find_limits()

    def _find_limits(self) -> microscope.devices.AxisLimits:
        """Finds the axis limits (also moves the stage to the limits).

        The Prior controller does not report the limits, we need to
        move the stage until it triggers the limit switches and then
        read its position.
        """
        answer = self._conn.get_description(b'STAGE')
        description = {}
        for line in answer.splitlines():
            if line == b'END':
                break
            (key, value) = line.split(b' = ')
            description[key] = value

        size_key = b'SIZE_' + self._name.encode()
        steps_key = b'MICROSTEPS/MICRON'

        # From documentation, we expect something like b'89 MM'.
        length_match = re.search(b'^\d+(?= MM$)', description[size_key])
        if length_match is None:
            raise RuntimeError('failed to parse stage size from \'%s\''
                               % description[size_key].decode())
        axis_length_micron = int(length_match[0]) * 1000

        microsteps_per_micron = int(description[steps_key])

        axis_microsteps = axis_length_micron * microsteps_per_micron
        def _get_limit(sign):
            # We will be moving to the axis limit.  Worst case
            # scenario we are on the opposite side of the axis and
            # need to move the length of the axis.  However, we only
            # have an estimate of that length so we try to move double
            # of that.
            self.move_by(math.copysign(axis_microsteps * 2, sign))
            if not self._conn.is_limit_switch_active(self._name, sign):
                raise RuntimeError('failed to reach limit of axis %s'
                                   % self._name)
            return self.position

        # Record initial position and return to it after hitting the
        # limits.  We don't have bother with a try/finally block
        # because if we fail to find the limits, we probably should
        # stop and not do any more moving at all.
        initial_position = self.position
        lower_limit = _get_limit(-1)
        upper_limit = _get_limit(+1)
        self.move_to(initial_position)

        return microscope.devices.AxisLimits(lower_limit, upper_limit)

    def move_by(self, delta: float) -> None:
        if self._name == 'X':
            self._conn.go_relative(int(delta), 0)
        elif self._name == 'Y':
            self._conn.go_relative(0, int(delta))
        else:
            raise RuntimeError('we should never have got here')

    def move_to(self, pos: float) -> None:
        if self._name == 'X':
            self._conn.go_x(int(pos))
        elif self._name == 'Y':
            self._conn.go_y(int(pos))
        else:
            raise RuntimeError('we should never have got here')

    @property
    def position(self) -> float:
        if self._name == 'X':
            return float(self._conn.absolute_x_position())
        elif self._name == 'Y':
            return float(self._conn.absolute_y_position())
        else:
            raise ValueError()

    @property
    def limits(self) -> microscope.devices.AxisLimits:
        if self._limits is None:
            raise RuntimeError('limits not found, stage must be enabled first.')
        return self._limits


class _ProScanIIIStage(microscope.devices.StageDevice):
    def __init__(self, connection: _ProScanIIIConnection) -> None:
        super().__init__()
        self._conn = connection

        self._axes = {
            'x' : _ProScanIIIStageAxis(self._conn, 'X'),
            'y' : _ProScanIIIStageAxis(self._conn, 'Y'),
        }

    @property
    def axes(self) -> typing.Mapping[str, microscope.devices.StageAxis]:
        return self._axes

    def _move_helper(self, axis_method: str, stage_method: str,
                     pos: typing.Mapping[str, float]) -> None:
        # Helper function to reduce code duplication on move() and move_to()
        if len(pos) == 1:
            axis_name, axis_delta = list(pos.items())[0]
            getattr(self._axes[axis_name], axis_method)(axis_delta)
        elif len(pos) == 2:
            getattr(self._conn, stage_method)(int(pos['x']), int(pos['y']))
        else:
            raise TypeError('invalid number of axes specified')

    def move_by(self, delta: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance. """
        self._move_helper('move_by', 'go_relative', delta)

    def move_to(self, position: typing.Mapping[str, float]) -> None:
        """Move specified axes by the specified distance. """
        self._move_helper('move_to', 'go', position)

    @property
    def position(self) -> typing.Mapping[str, float]:
        # Overload the default implementation so we can do this with a
        # single command to the controller.
        positions = self._conn.absolute_position()
        # TODO: the controller always returns three positions, even if
        # there's no Z axis on the stage on controller.  We need to
        # check what happens when there's a Z stage connected, and
        # what happens when there is no XY stage and only a Z stage.
        return {'x' : positions[0], 'y' : positions[1]}

    @property
    def limits(self) -> typing.Mapping[str, microscope.devices.AxisLimits]:
        # TODO: Vrey importanta
        raise NotImplementedError()


    def _on_shutdown(self) -> None:
        super()._on_shutdown()

    def initialize(self) -> None:
        super().initialize()


class _ProScanIIIFilterWheel(microscope.devices.FilterWheelBase):
    def __init__(self, connection: _ProScanIIIConnection, number: int) -> None:
        super().__init__()
        self._conn = connection
        self._number = number
        self._positions = self._conn.get_n_filter_positions(self._number)

    def get_position(self) -> int:
        return self._conn.get_filter_position(self._number)

    def set_position(self, position: int) -> None:
        self._conn.set_filter_position(self._number, position)

    def _on_shutdown(self) -> None:
        super()._on_shutdown()

    def initialize(self) -> None:
        super().initialize()


class ProScanIII(microscope.devices.ControllerDevice):
    """Prior ProScanIII controller.

    The controlled devices have the following labels:

    `filter 1`
      Filter wheel connected to connector labelled "FILTER 1".
    `filter 2`
      Filter wheel connected to connector labelled "FILTER 1".
    `filter 3`
      Filter wheel connected to connector labelled "A AXIS".
    `stage`
      XY stage.

    This controller is also meant to support three shutters, motor
    stages with encoders, a Z focus, and a fourth axis.  These have
    never been tested because we don't have access to them.

    .. note::

       The Prior ProScanIII can control up to three filter wheels.
       However, a filter position may have a different number
       dependening on which connector it is.  For example, using an 8
       position filter wheel, what is position 1 on the "filter 1" and
       "filter 2" connectors, is position 4 when on the "A axis" (or
       filter 3) connector.
    """
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 0.5,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self._conn = _ProScanIIIConnection(port, baudrate, timeout)
        self._devices = {} # type: typing.Dict[str, microscope.devices.Device]

        # Can have up to three filter wheels, numbered 1 to 3.
        for number in range(1, 4):
            if self._conn.has_filterwheel(number):
                key = 'filter %d' % number
                self._devices[key] = _ProScanIIIFilterWheel(self._conn, number)

        # This is a XY stage only
        if self._conn.has_stage():
            self._devices['stage'] = _ProScanIIIStage(self._conn)

    @property
    def devices(self) -> typing.Mapping[str, microscope.devices.Device]:
        return self._devices
