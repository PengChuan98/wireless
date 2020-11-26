# -*- coding: iso-8859-1 -*-
# prog_atten_exceptions.py

from jfw50pa_serial import JFW50PASerial

# A class that wraps exception handling for the ProgAtten class.
# The class ProgAtten inherits from ProgAttenExcept.
class JFW50PAExcept(object):
    @staticmethod
    def _checkAttenNum(num):
        if not isinstance(num, int):
            raise TypeError("num must be an integer ")
        if (num < 1 or num > 4):
            raise ValueError("num must be between 1 and 4")

    @staticmethod
    def _checkAttenNums(num1,num2):
        if num1 == num2:
            raise ValueError("attenuator addresses cannot be the same")

    @staticmethod
    def _checkAttenValue(value):
        if not isinstance(value, int):
            raise TypeError("value must be an integer")
        if value < 0 or value > 63:
            raise ValueError("value must be between 0 and 63")

    @staticmethod
    def _checkAttenFaderStartStop(start,stop):
        if start == stop:
            raise ValueError("values can't be the same value")

    @staticmethod
    def _checkTime(t):
        if not isinstance(t, int):
            raise TypeError("value must be an integer")
        if t < 0 or t > 9999:
            raise ValueError("value must be between 0 and 63")

    @staticmethod
    def _checkAttenTime(time):
        if not isinstance(time, str):
            raise TypeError("value must be M (milliseconds) or S (seconds)")
        if not ((time == 'M') or (time == 'm') or (time == 'S') or (time == 's')):
            raise TypeError("value must be M (milliseconds) or S (seconds)")

    @staticmethod
    def _checkIfSerial(serial_obj):
        if not isinstance(serial_obj,JFW50PASerial):
            raise TypeError("must be in serial mode to set baudrate")
