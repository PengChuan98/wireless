
from PyQt4.QtCore import *
import time

__version__ = "1.0.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

################################
####  __  __                ####
#### |  \/  |     (_)       ####
#### | \  / | __ _ _ _ __   ####
#### | |\/| |/ _` | | '_ \  ####
#### | |  | | (_| | | | | | ####
#### |_|  |_|\__,_|_|_| |_| ####
####                        ####
################################

class Clockcheck(QThread):

    def __init__(self, parent=None):
        super(Clockcheck, self).__init__(parent)
        self.stopped = False
        self.mutex = QMutex()

    def initialize(self, ptime, ftime, stime, tag):
        self.ptime = ptime
        self.ftime = ftime
        self.stime = stime
        self.tag = tag

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
            print "stopping old clock"
        finally:
            self.mutex.unlock()

    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()

    def run(self):
        self.clocksweep(self.ptime, self.ftime, self.stime, self.tag)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Checking if app froze')
        if not self.stopped:
            self.stop()

    def clocksweep(self, pt, ft, st, tag):
        # Handling NoneType
        if tag is None:
            tag = 999 # Some value which can not be a channel number or degree
        while pt < ft:
            time.sleep(st)
            pt = time.time()
            self.emit(SIGNAL("clockRemain(float)"), (ft-pt))
            print "thread for %s \n" %tag # Saketh debug
        self.emit(SIGNAL("clockTag(int)"), tag)
