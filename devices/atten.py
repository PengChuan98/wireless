from jfw50pa import JFW50PA
from agilent_j7211a import AgilentJ7211
from rc4dat import RC4DAT
from gpib_devices import GpibDevice, Aeroflex8310, Agilent11713A, Keysight11713C
from device import SetDevice

class Attenuator(object):
    supported = GpibDevice.supported_atten + [JFW50PA.__name__.lower(), AgilentJ7211.__name__.lower(), RC4DAT.__name__.lower(),]

    @classmethod
    def connect(cls, model, **kwargs):
        atten = None
        if model.lower() not in cls.supported:
            raise TypeError("%s is not a supported attenuator model" % (model.lower()))
        if model.lower() in GpibDevice.supported_atten:
            if "board" not in kwargs and "device" not in kwargs:
                raise TypeError("%s requires a GPIB board and device number" % (model.lower()))
            if model.lower() == cls.supported[0]:
                atten = Aeroflex8310(**kwargs)
            elif model.lower() == cls.supported[1]:
                atten = Agilent11713A(**kwargs)
            elif model.lower() == cls.supported[2]:
                atten = Keysight11713C(**kwargs)
        elif model.lower() == cls.supported[3]:
            if "ip" not in kwargs and "port" not in kwargs:
                raise TypeError("%s requires either an ip address or serial port" % (cls.supported[3]))
            atten = JFW50PA(**kwargs)
            atten.Open()
        elif model.lower() == cls.supported[4]:
            if "ip" not in kwargs:
                raise TypeError("%s requires an ip address" % (cls.supported[4]))
            atten = AgilentJ7211(**kwargs)
        elif model.lower() == cls.supported[5]:            
            atten = RC4DAT(**kwargs)
        return atten

    @classmethod
    def reinit(cls, old_dev):
        if old_dev.__class__.__name__.lower() in GpibDevice.supported_atten:
            return cls.connect(old_dev.__class__.__name__.lower(), board=old_dev.board,
                                device=old_dev.device, start=old_dev.start,
                                stop=old_dev.stop, step=old_dev.step,
                                current=old_dev.current)
        elif old_dev.__class__.__name__.lower() == cls.supported[3]:
            return cls.connect(old_dev.__class__.__name__.lower(), ip=old_dev.pa.ip_addr,
                                start=old_dev.start, stop=old_dev.stop, step=old_dev.step,
                                current=old_dev.current)
        elif old_dev.__class__.__name__.lower() == cls.supported[4]:
            return cls.connect(old_dev.__class__.__name__.lower(), ip=old_dev.ip,
                                start=old_dev.start, stop=old_dev.stop, step=old_dev.step,
                                current=old_dev.current)


if __name__ == "__main__":
#    atten = Attenuator.connect("aeroflex8310", board=0, device=3)
    #atten = Attenuator.connect("jfw50pa", ip="192.168.0.250")

#    for i in atten.iter(0, 10, 2):
#        atten.set(channel=1, value=i)
#        time.sleep(1)

#    Attenuator.reinit(atten)
    #atten.set(value=10)
    #print Attenuator.supported
#   atten = Attenuator("JFW50PA", ip_addr="192.168.0.250")
#    atten = Attenuator("agilentj7211", ip="192.168.0.101", display=True)
#    atten.set(value=20)
    atten = Attenuator.connect("rc4dat")
    atten.set(1,1)
    import time
    time.sleep(3)
    print atten.Read()
    atten.Close()
    print Attenuator.supported
#   atten.set(channel=1, value=18)
#   atten.setAttenuator(2, 10)
#   atten.Send()
