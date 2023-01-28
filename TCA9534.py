# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Chris Burton
#
# SPDX-License-Identifier: MIT

"""
`TCA9534`
=======

CircuitPython library for Texas Instrument PCA9534 and TCA9534 ICs.

* Author(s): Chris Burton

Usage Notes
-----------
Inversion only applies when reading a pin.

"""

try:
    # This is only needed for typing
    from typing import Optional
    import busio
except ImportError:
    pass

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const
import digitalio

_TCA9534_DEFAULT_I2C_ADDR = const(0x20)       # Default I2C address
_TCA9534_REGISTER_INPUT_PORT = const(0x00)    # Default XXXX XXXX
_TCA9534_REGISTER_OUTPUT_PORT = const(0x01)   # Default 1111 1111 
_TCA9534_REGISTER_INVERSION = const(0x02)     # Default 0000 0000 (No inversion)
_TCA9534_REGISTER_CONFIGURATION = const(0x03) # Default 1111 1111 (All Inputs)

class TCA9534:
    def __init__(self, i2c: I2C, address: int = _TCA9534_DEFAULT_I2C_ADDR, reset: bool = True) -> None:
        self.i2c_device = I2CDevice(i2c, address)
        self._output = bytearray([0])
        self._inversion = bytearray([0])
        self._configuration = bytearray([0])

        if reset:
            # Reset to all inputs, disable inversion, set outputs to 1
            with self.i2c_device as i2c:
                i2c.write( bytearray([_TCA9534_REGISTER_CONFIGURATION, 0xFF]) )
                i2c.write( bytearray([_TCA9534_REGISTER_INVERSION, 0x00]) )
                i2c.write( bytearray([_TCA9534_REGISTER_OUTPUT_PORT, 0xFF]) )

        with self.i2c_device as i2c:
            i2c.write_then_readinto( bytearray([_TCA9534_REGISTER_OUTPUT_PORT, ]), self._output )
            i2c.write_then_readinto( bytearray([_TCA9534_REGISTER_INVERSION, ]), self._inversion )
            i2c.write_then_readinto( bytearray([_TCA9534_REGISTER_CONFIGURATION, ]), self._configuration )

    def read_gpio(self) -> int:
        buf = bytearray([0])
        with self.i2c_device as i2c:
            i2c.write_then_readinto( bytearray([_TCA9534_REGISTER_INPUT_PORT, ]), buf )
        return buf[0]

    def write_gpio(self, val: int) -> None:
        self._output[0] = val & 0xFF
        with self.i2c_device as i2c:
            i2c.write( bytearray([_TCA9534_REGISTER_OUTPUT_PORT, self._output[0]]) )

    def set_iodir(self, val: int) -> None:
        self._configuration[0] = (val & 0xFF)
        with self.i2c_device as i2c:
            i2c.write( bytearray([_TCA9534_REGISTER_CONFIGURATION, self._configuration[0]]) )

    def get_iodir(self) -> int:
        return self._configuration[0]

    def get_inv(self) -> int:
        return self._inversion[0]

    def set_inv(self, val: int) -> None: # Inversion only applies to inputs
        self._inversion[0] = val & 0xFF
        with self.i2c_device as i2c:
            i2c.write( bytearray([_TCA9534_REGISTER_INVERSION, self._inversion[0]]) )

    def get_pin(self, pin: int) -> "DigitalInOut":
        assert 0<= pin <= 7
        return DigitalInOut(pin, self)

    def write_pin(self, pin: int, val: bool) -> None:
        if val:
            self.write_gpio(self.output | (1<<pin))
        else:
            self.write_gpio(self.output & ~(1<<pin))

    def read_pin(self, pin: int) -> bool:
        return (self.read_gpio() >> pin) & 0x1

class DigitalInOut:
    def __init__(self, pin_number: int, tca: TCA9534) -> None:
        self._pin = pin_number
        self._tca = tca

    def switch_to_output(self, value: bool = False, **kwargs) -> None:
        if value:
            self._tca.write_gpio( self._tca._output[0] | ( 1<<self._pin ) )
        else:
            self._tca.write_gpio( self._tca._output[0] & ~( 1<<self._pin ) )
        self._tca.set_iodir( ((self._tca._configuration[0] & (1<<self._pin)) >> self._pin) & ~( 1<<self._pin ) )

    def switch_to_input(self, **kwargs) -> None:
        self._tca.set_iodir( ((self._tca._configuration[0] & (1<<self._pin)) >> self._pin) | ( 1<<self._pin ) )

    @property
    def value(self) -> bool:
        return (self._tca.read_gpio() & (1<<self._pin)) >> self._pin

    @value.setter
    def value(self, val: bool) -> None:
        if val:
            self._tca.write_gpio( self._tca._output[0] | ( 1<<self._pin ) )
        else:
            self._tca.write_gpio( self._tca._output[0] & ~( 1<<self._pin ) )

    @property
    def direction(self) -> digitalio.Direction:
        if ((self._tca._configuration[0] & (1<<self._pin)) >> self._pin):
            return digitalio.Direction.INPUT
        else:
            return digitalio.Direction.OUTPUT

    @direction.setter
    def direction(self,val: digitalio.Direction) -> None:
        if val == digitalio.Direction.INPUT:
            self._tca.set_iodir( ((self._tca._configuration[0] & (1<<self._pin)) >> self._pin) | ( 1<<self._pin ) )
        elif val == digitalio.Direction.OUTPUT:
            self._tca.set_iodir( ((self._tca._configuration[0] & (1<<self._pin)) >> self._pin) & ~( 1<<self._pin ) )
        else:
            raise ValueError("Expected INPUT or OUTPUT direction!")

    @property
    def invert_polarity(self) -> bool:
        return self._tca._inversion[0] & (1<<self._pin) >> self._pin

    @invert_polarity.setter
    def invert_polarity(self, val: bool) -> None:
        if val:
            self._tca.set_inv( self._tca.get_inv() | (1<<self._pin) )
        else:
            self._tca.set_inv( self._tca.get_inv() & ~(1<<self._pin) )
