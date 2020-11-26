from gpib_devices import GpibDevice, Emco1060

class Turntable(Emco1060):
    supported = GpibDevice.supported_turntable

    @classmethod
    def connect(cls, model, **kwargs):
        turntable = None
        if model.lower() == cls.supported[0]:
            if len(kwargs) != 2 and "board" not in kwargs and "device" not in kwargs:
                raise TypeError("%s requires GPIB board and device number" % (self.__class__.supported[0]))
            turntable = Emco1060(**kwargs)
        else:
            raise TypeError("%s is not a supported model" % (model))
        return turntable

    @classmethod
    def reinit(cls, old_dev):
        if old_dev.__class__.__name__.lower() in GpibDevice.supported_turntable:
            turntable = cls.connect(old_dev.__class__.__name__.lower(), board=old_dev.board,
                                device=old_dev.device, start=old_dev.start,
                                stop=old_dev.stop, step=old_dev.step, current=old_dev.current)
            turntable.set(turntable.current)
            return turntable

if __name__ == "__main__":
    tt = Turntable.connect("Emco1060", board=0, device=10)
    tt.set(10)
