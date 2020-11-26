#!/usr/bin/env python

import socket
from device import SetDevice

class AgilentJ7211Error(Exception):
    pass

class AgilentJ7211(socket.socket, SetDevice):
    port = 5025
    display_screens = {"attenuation":"ATT", "io":"IO", "program":"PROG",
            "cycle":"CYCL", "information":"INF", "utility":"UTIL"}

    def __init__(self, ip, buf_size=1024, timeout=1, display=False, start=None,
                stop=None, step=None, current=None):
        self._ip = ip
        if buf_size < 1:
            raise ValueError("read buffer size must be greater than 0")
        self._buf_size = buf_size
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.settimeout(timeout)
        self.connect((self._ip, self.__class__.port))
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)
        self._is_relative = self.enable_relative
        self._relative = None
        self._relative_level = None
        self._en_display = display

    @property
    def ip(self):
        return self._ip

    @property
    def buf_size(self):
        return self._buf_size

    @buf_size.setter
    def buf_size(self, value):
        if not isinstance(value, int):
            raise TypeError("read buffer size must be an integer")
        if value < 1:
            raise ValueError("read buffer size must be greater than 0")
        self._buf_size = value

    def __get(self):
        ret = self.recv(self._buf_size)
        if ret:
            ret = ret.strip()
        return ret

    @staticmethod
    def __proc_int_str(int_str):
        sign = int_str[0]
        val = int(int_str[1:])
        if sign == "-":
            val = -1 * val
        return val
  
    @property
    def id(self):
        if self._en_display:
            self.display("information")
        self.send("*IDN?\r\n")
        return self.__get()

    def set(self, value):
        self.value = value
        
    @property
    def value(self):
        if self._en_display:
            self.display("attenuation")
        self.send("ATT?\r\n")
        return self.__proc_int_str(self.__get())

    @value.setter
    def value(self, value):
        if not isinstance(value, int):
            raise TypeError("attenuator value must be an integer")
        if value < 0 or value > 121:
            raise ValueError("attenuator value must be between 0 & 121")
        if self._en_display:
            self.display("attenuation")
        self.send("ATT %d\r\n" % (value))

    @property
    def step_size(self):
        self.send("ATT:STEP?\r\n")
        if self._en_display:
            self.display("attenuation")
        return self.__proc_int_str(self.__get())

    def step(self):
        if self._en_display:
            self.display("attenuation")
        self.send("ATT:INCR\r\n")

    @step_size.setter
    def step_size(self, value):
        if not isinstance(value, int):
            raise TypeError("attenuator step value must be an integer")
        if value < -121 or value > 121:
            raise ValueError("attenuator step value must be between -121 & 121")
        if self._en_display:
            self.display("attenuation")
        self.send("ATT:STEP %d\r\n" % (value))

    @property
    def enable_relative(self):
        self.send("ATT:REL:STAT?\r\n")
        self._is_relative = self.__get()
        return self._is_relative

    @enable_relative.setter
    def enable_relative(self, state):
        cmd_str = "ATT:REL:STAT "
        if isinstance(state, int):
            if state != 0 and state != 1:
                raise ValueError("state must either be 0 or 1")
            elif state == 0:
                self._relative_level = None
            elif state == 1:
                self._relative_level = 0
            cmd_str += str(state)
        elif isinstance(state, str):
            if state.lower() != "on" and state.lower() != "off" \
                    and state.lower() != "0" and state.lower() != "1":
                raise ValueError("state must either be on or off")
            elif state.lower() == "off" or state.lower() == "0":
                self._relative_level = None
            elif state.lower() == "on" or state.lower() == "1":
                self._relative_level = 0
            cmd_str += state
        elif isinstance(state, bool):
            if state == True:
                cmd_str += "on"
            elif state == False:
                cmd_str += "off"
        cmd_str +="\r\n"
        self.send(cmd_str)

    @property
    def relative(self):
        return self._relative_level

    @relative.setter
    def relative(self, level):  # adds onto previous relative level, disable to restart
        if self._relative_level != 1:
            raise AgilentJ7211Error("relative attenuation is not enabled")
        if not isinstance(level, int):
            raise TypeError("attenuator reference level must be an integer")
        if level < 0:
            raise ValueError("relative attenuation level must be positive")
        if (self._relative_level + level) < 0 or \
                (self._relative_level + level) > 121:
            raise ValueError("relative attenuation level must be between 0 & 121")
        self.send("ATT:REL:LEV %d" % (level))
        self._relative_level += level

    def __iadd__(self, increment):
        if not isinstance(increment, int):
            raise TypeError("attenuator increment value must be an integer")
        if increment < 0 or increment > 121:
            raise ValueError("attenuator increment value must be between 0 & 121")
        if self._en_display:
            self.display("attenuation")
        self.send("ATT:INCR %d\r\n"% (increment))
        return self

    def __isub__(self, decrement):
        if not isinstance(decrement, int):
            raise TypeError("attenuator decrement value must be an integer")
        if decrement < 0 or decrement > 121:
            raise ValueError("attenuator decrement value must be between 0 & 121")
        if self._en_display:
            self.display("attenuation")
        self.send("ATT:DECR %d\r\n"% (decrement))
        return self

    def cvalue(self, attenuation, frequency=None):
        if not isinstance(attenuation, int):
            raise TypeError("attenuator value must be an integer")
        if attenuation < 0 or attenuation > 121:
            raise ValueError("attenuator value must be between 0 & 121")
        cmd_str = "CORR? %d" % (attenuation)
        if frequency is not None:
            if not isinstance(frequency, int) and not isinstance(frequency, float):
                raise TypeError("frequency must be either an integer or float")
            if frequency < 0 or frequency > 6:
                raise TypeError("frequency must be between 0 & 6 GHz")
            if isinstance(frequency, int):
                cmd_str += ",%d\r\n" % (frequency)
            elif isinstance(frequency, float):
                cmd_str += ",%.2f\r\n" % (frequency)
        if self._en_display:
            self.display("attenuation")
        atten.send(cmd_str)
        return atten.__get()

    @property
    def en_display(self):
        return self._en_display

    @en_display.setter
    def en_display(self, enable):
        if enable != True and enable != False:
            raise TypeError("en_display must either be True or False")
        self._en_display = enable

    def display(self, disp_str):
        if disp_str.lower() not in self.__class__.display_screens.keys() and \
                disp_str.upper() not in self.__class__.display_screens.values():
            raise ValueError("%d is not a valid display screen")
        if disp_str.lower() in self.__class__.display_screens.keys():
            self.send("DISP:%s\r\n" % (self.__class__.display_screens[disp_str.lower()]))
        else:
            self.send("DISP:%s\r\n" % (disp_str.upper()))

    @property
    def cycles(self):
        if self._en_display:
            self.display("cycle")
        self.send("DIAG:REL:CYCL? (@1:8)\r\n")
        ret = self.__get()
        if ret:
            ret = [int(el) for el in ret.split(",")]
        return ret


if __name__ == "__main__":
    atten = AgilentJ7211("192.168.0.101", display=True)
    prev_val = atten.value
    print prev_val
#    if isinstance(atten.value, int):
#        print "HERE"

    atten.value += 1

    print atten.cycles
#    print atten.value
    #print atten.id
#    atten.relative = "0"
#    print atten.relative
    #atten.step_size = -10
    #print atten.step_size
    #atten.step()
#    print atten
#    atten -= 5
#    print atten
#    print atten.cvalue(25, 3.05)
#    print atten.id
#    print atten.value
#    atten.value = 999
#    print atten.value
    #atten.close()
