class Device(object):
    device_list = dict()

    def __init__(self):
        if self.__class__.__name__ in self.__class__.device_list:
            if not isinstance(self.__class__.device_list, list):
                val = [self.__class__.device_list[self.__class__.__name__], self]
            else:
                val = self.__class__.device_list[self.__class__.__name__] + [self]
        else:
            val = self
        self.__class__.device_list[self.__class__.__name__] = val

    @classmethod
    def list(cls):
        return cls.device_list

class SetDevice(Device):
    def __init__(self, start=None, stop=None, step=None, current=None):
        Device.__init__(self)
        if start is not None:
            if not isinstance(start, int):
                raise TypeError("start value must be an integer")
            if start < 0:
                raise ValueError("start value must be greater than 0")
        self._start = start
        if stop is not None:
            if not isinstance(stop, int):
                raise TypeError("stop value must be an integer")
            if stop < 0:
                raise ValueError("stop value must be greater than 0")
        self._stop = stop
        if step is not None:
            if not isinstance(step, int):
                raise TypeError("step value must be an integer")
        self._step = step
        if current is not None:
            if not isinstance(current, int):
                raise TypeError("current value must be an integer or None")
            if current < start or current > stop:
                raise ValueError("current value must be between start and stop values")
        self._current = current

    def iter(self, start, stop, step=1):
        if self._current is None:
            if not isinstance(start, int):
                raise TypeError("starting attenuator value must be an integer")
            if start < 0:
                raise ValueError("starting attenuator value must be positive")
            self._start = start
            if not isinstance(stop, int):
                raise TypeError("stopping attenuator value must be an integer")
            if stop < 0:
                raise ValueError("stopping attenuator value must be positive")
            self._stop = stop
            if not isinstance(step, int):
                raise TypeError("attenuator step must be an integer")
            self._step = step
            if self._step < 0 and self._start < self._stop:
                if self._step < 0:
                    tmp = self._stop
                    self._stop  = self._start - 1
                    self._start = tmp
                else:
                    self._step = -1 * self._step
                    self._stop -= 1
            else:
                self._stop += 1

            for i in range(self._start, self._stop, self._step):
                self._current = i
                yield i
            self._current = None
        else:
            for i in range(self._current, self._stop, self.step):
                self._current = i
                yield i

    @property
    def start(self):
        return self._start

    @property
    def stop(self):
        return self._stop

    @property
    def step(self):
        return self._step

    @property
    def current(self):
        return self._current
