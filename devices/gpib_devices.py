import os
import warnings
#warnings.simplefilter("always")
import time
import re
from device import SetDevice
if "nt" in os.name:
    try:
        import visa
    except ImportError:
       warnings.warn("cannot import visa library, limited to TCP/IP device support only",
                    ImportWarning)
elif "posix" in os.name:
    try:
        import Gpib
    except ImportError:
        warnings.warn("cannot import GPIB library, limited to TCP/IP device support only",
                    ImportWarning)

# Forward declaring classes
class Aeroflex8310(object):
    pass

class Agilent11713A(object):
    pass

class Keysight11713C(object):
    pass

class Emco1060(object):
    pass

class SC110V(object):
    pass

class GpibDevice(object):
    supported_atten = [Aeroflex8310.__name__.lower(), Agilent11713A.__name__.lower(), Keysight11713C.__name__.lower()]
    supported_turntable = [Emco1060.__name__.lower()]
    supported_tilt = [SC110V.__name__.lower()]

    def __init__(self, board, device):
        if not isinstance(board, int):
            raise TypeError("GPIB board number must be an integer")
        if board < 0 or board > 11:
            raise ValueError("GPIB board number must be between 0 and 11")
        if not isinstance(device, int):
            raise TypeError("GPIB device number must be an integer")
        if device < 0 or device > 30:
            raise ValueError("GPIB device number must be between 0 and 30")
        self._board = board
        self._device = device
        if "nt" in os.name:
            init_str = "GPIB%d::%d::INSTR" % (self._board, self._device)
            self._rm = visa.ResourceManager()
            self.instr = self._rm.open_resource(init_str)
        elif "posix" in os.name:
            self.instr = Gpib.Gpib(self._board, self._device)

    @property
    def board(self):
        return self._board

    @property
    def device(self):
        return self._device

    @property
    def id(self):
        self.write("*IDN?")
        ret = self.instr.read()
        if isinstance(ret, (str, unicode)):
            ret = ret.strip()
        return ret

    def reset(self):    # idk if this is just for Aeroflex8310
        self.instr.write("*RST")

    def write(self, gpib_str):
        self.instr.write(gpib_str)

    def read(self):
        return self.instr.read()

    @staticmethod
    def get_devices():
        if "posix" in os.name:
            raise NotImplementedError("get_devices() is not supported on Posix")
        devices= dict()
        rm = visa.ResourceManager()
        for resource in rm.list_resources():
            search = re.search("GPIB(\d+)::(\d+)::INSTR", resource)
            if search is not None:
                board  = int(search.group(1))
                device = int(search.group(2))
            if resource.lower().find("gpib") == 0:
                instr_id = rm.open_resource(resource).query("*IDN?").strip()
                if instr_id.lower().find("8310") != -1:
                    devices[GpibDevice.supported_atten[0]] = (board, device)
                elif instr_id.lower().find("11712a") != -1:
                    devices[GpibDevice.supported_atten[1]] = (board, device)
                elif instr_id.lower().find("11713c") != -1:
                    devices[GpibDevice.supported_atten[2]] = (board, device)
                elif instr_id.lower().find("1060") != -1:
                    devices[GpibDevice.supported_turntable[0]] = (board, device)
                elif instr_id.lower().find("110") != -1:
                    devices[GpibDevice.supported_tilt[0]] = (board, device)
                else:
                    if "unknown" in devices.keys():
                        if not isinstance(devices["unknown"], list):
                            devices["unknown"] = [devices["unknown"], (board, device)]
                        else:
                            devices["unknown"].append((board, device))
                    else:
                        devices["unknown"] = (board, device)
        return devices

class Aeroflex8310(GpibDevice, SetDevice):
    def __init__(self, board=0, device=3, start=None, stop=None, step=None, current=None):
        GpibDevice.__init__(self, board, device)
        self.write("REL 0")   # Turn off relative mode
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)

    def set(self, channel, value):
        if not isinstance(channel, int):
            raise TypeError("Aeroflex8310 channel must be an integer")
        if channel < 0:
            raise ValueError("Aeroflex8310 channel must be an positive integer")
        if not isinstance(value, int):
            raise TypeError("Aeroflex8310 value must be an integer")
        if value < 0 or value > 103:
            raise ValueError("Aeroflex8310 attenuator value must be an integer between 0 and 103")
        self.write("CHAN "+str(channel))
        self.write("ATTN "+str(value))

class Emco1060(GpibDevice, SetDevice):
    def __init__(self, board=0, device=10, start=None, stop=None, step=None, current=None): # is actually at 0, 10 but 10, 10 works with Stallin
        GpibDevice.__init__(self, board, device)
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)
        self.low_limit = 0
        self.hi_limit = 359

        self.write("CL "+str(self.low_limit))
        self.write("WL "+str(self.hi_limit))

        self.write("CP")
        self.cur_pos = int(self.read())

    @property
    def value(self):
        self.write("CP?")
        ret = self.read()
        if isinstance(ret, str):
            ret = ret.strip()
        return ret

    @value.setter
    def value(self, degree):
        if not isinstance(degree, int):
            raise TypeError("Emco1060 degree must be an integer")
        if degree < 0 or degree >= 360:
            raise ValueError("Emco1060 degree must be between 0 and 360")
        if degree > self.cur_pos:
            self.write("WL "+str(degree))
            self.write("CW")  # rotate clockwise
            while self.cur_pos < degree:
                time.sleep(1)
                self.write("CP")
                self.cur_pos = int(self.read())
            self.write("ST")  # stop
            self.write("CP")
            self.cur_pos = int(self.read())
            self.write("WL "+str(self.hi_limit))
        elif degree < self.cur_pos:
            self.write("CL "+str(degree))
            self.write("CC")  # rotate counter-clockwise
            while self.cur_pos > degree:
                time.sleep(1)
                self.write("CP")
                self.cur_pos = int(self.read())
            self.write("ST")  # stop
            self.write("CP")
            self.cur_pos = int(self.read())
            self.write("CL "+str(self.low_limit))
        else:   # if its equal
            pass
        return self.cur_pos

    def set(self, degree=0):
        self.value = degree

class SC110V(GpibDevice, SetDevice):
    def __init__(self, board=0, device=11, start=None, stop=None, step=None, current=None):
        GpibDevice.__init__(self, board, device)
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)
        self.low_limit = -180
        self.hi_limit  =  180

        self.write("CL "+str(self.low_limit))
        self.write("WL "+str(self.hi_limit))

        self.write("CP")
        self.cur_pos = int(self.read())

    @property
    def value(self):
        self.write("CP")
        ret = self.read()
        if isinstance(ret, str):
            ret = ret.strip()
        return ret

    @value.setter
    def value(self, degree):
        if not isinstance(degree, int):
            raise TypeError("SC110V degree must be an integer")
        if degree < -180 or degree > 180:
            raise ValueError("SC110V degree must be between -180 and 180")
        if degree > self.cur_pos:
            self.write("WL "+str(degree))
            self.write("CW")  # rotate clockwise
            while self.cur_pos < degree:
                time.sleep(1)
                self.write("CP")
                self.cur_pos = int(self.read())
            self.write("ST")  # stop
            self.write("CP")
            self.cur_pos = int(self.read())
            self.write("WL "+str(self.hi_limit))
        elif degree < self.cur_pos:
            self.write("CL "+str(degree))
            self.write("CC")  # rotate counter-clockwise
            while self.cur_pos > degree:
                time.sleep(1)
                self.write("CP")
                self.cur_pos = int(self.read())
            self.write("ST")  # stop
            self.write("CP")
            self.cur_pos = int(self.read())
            self.write("CL "+str(self.low_limit))
        else:   # if its equal
            pass
        return self.cur_pos

    def set(self, degree=0):
        self.value = degree

class Agilent11713A(GpibDevice, SetDevice):
    def __init__(self, board=0, device=3, start=None, stop=None, step=None, current=None):
        GpibDevice.__init__(self, board, device)
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)

    def set(self, value):
        self.write(self.__createSetCmd(value))

    def __createSetCmd(self, value):
        def createAttenStr(value, bit_list):
            atten = ""
            atten_on = "A"
            atten_off = "B"
            for bit_set in reversed(bit_list):
                if value >= bit_set[1]:
                    atten_on += str(bit_set[0])
                    value -= bit_set[1]
                else:
                    atten_off += str(bit_set[0])
            if len(atten_on) > 1:
                atten += atten_on
            if len(atten_off) > 1:
                atten += atten_off
            return atten, value

        atten_x = ""
        atten_y = ""
        bit_list = list()

        if not isinstance(value, int):
            raise TypeError("Agilent11713A attenuator value must be an integer")
        if value < 0 or value > 81:
            raise ValueError("Agilent11713A attenuator value must be between 0 and 81")

        for bit, bit_val in enumerate([1, 2, 4, 4, 10, 20, 40], 1):
            bit_list.append((bit, bit_val))

        atten_y, value = createAttenStr(value, bit_list[4:7])
        atten_x, value = createAttenStr(value, bit_list[:4])

        return atten_x+" "+atten_y

class Keysight11713C(GpibDevice, SetDevice):
    def __init__(self, board=0, device=3, start=None, stop=None, step=None, current=None):
        GpibDevice.__init__(self, board, device)
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)

    def __createSetCmd(self, channel, value):
        if len(str(value)) == 1:
            xval=str(value)[0]
            yval='0'
        elif len(str(value)) == 2:
            xval = str(value)[1]
            yval = str(value-int(xval))

        yield "ATT:BANK%d:X %s" % (channel, xval)
        yield "ATT:BANK%d:Y %s" % (channel, yval)

    def set(self, channel, value):
        if not isinstance(channel, int):
            raise TypeError("Keysight11713C channel must be an integer")
        if channel < 1 and channel > 2:
            raise ValueError("Keysight11713C only supports channel 1 and 2")
        if not isinstance(value, int):
            raise TypeError("Keysight11713C attenuator value must be an integer")
        if value < 0 or value > 81:
            raise ValueError("Keysight11713C attenuator value must be between 0 and 81")

        for cmd in self.__createSetCmd(channel, value):
            self.write(cmd)

if __name__ == "__main__":
    print GpibDevice.supported_atten
    print GpibDevice.supported_turntable
    print GpibDevice.supported_tilt
    #atten = Agilent11713A()
    #atten = Aeroflex8310(0, 3)
    #atten.set(20)
    tt = Emco1060(board=0, device=10)
    tt.set(10)
    tilt = SC110V(board=0, device=11)
    tilt.set(10)
    print atten.id
