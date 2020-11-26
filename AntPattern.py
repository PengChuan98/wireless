#!/usr/bin/env python
#  Copyright (c) 2015 Hewlett-Packard Inc.
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#  3. Neither the name of Hewlett-Packard nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
#  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
#  NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#  TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
#  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import platform
import sys
import re
import serial
import serial.tools.list_ports
import visa
import time
import glob
import subprocess
import math

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest
import ota
from devices import Turntable, Tilt

from numpy import *
import matplotlib.pyplot as plt
from numpy.random import rand


__version__ = "1.0.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

########################################################################
########################################################################
####                 _                           __  __       _
####     /\         | |                         |  \/  |     (_)
####    /  \   _ __ | |_ ___ _ __  _ __   __ _  | \  / | __ _ _ _ __
####   / /\ \ | '_ \| __/ _ \ '_ \| '_ \ / _` | | |\/| |/ _` | | '_ \
####  / ____ \| | | | ||  __/ | | | | | | (_| | | |  | | (_| | | | | |
#### /_/    \_\_| |_|\__\___|_| |_|_| |_|\__,_| |_|  |_|\__,_|_|_| |_|
####
####
########################################################################
########################################################################

class AntPattern(QThread):

    PRINT = 1
    NOPRINT = 0

    def __init__(self, parent=None):
        super(AntPattern, self).__init__(parent)
        self.stopped = False
        self.mutex = QMutex()
        self.completed = False


    def initialize(self, **kargs):
        self.solcom     = kwargs['solcom']
        self.routcom    = kwargs['routcom']
        self.lincom     = kwargs['lincom']
        self.commands   = kwargs['commands']
        self.iperf      = kwargs['iperf']
        self.fiveGHz    = kwargs['fiveGHz']
        self.wifiD      = kwargs['direct']
        self.tTable     = kwargs['tTable']
        self.autoRun    = kwargs['autrorun']
        if 'manStart' in kwargs:
            self.manStart = kwargs['manStart']
        if 'manStop' in kwargs:
            self.manStop = kwargs['manStop']
        if 'manSweepStep' in kwargs:
            self.manSweepStep = kwargs['manSweepStep']
        if 'manSweepTime' in kwargs:
            self.manSweepTime = kwargs['manSweepTime']
        if 'autoStartDeg' in kwargs:
            self.autoStartDeg = kwargs['autoStartDeg']
        if 'autoStopDeg' in kwargs:
            self.autoStopDeg = kwargs['autoStopDeg']
        if 'autoStepDeg' in kwargs:
            self.autoStepDeg = kwargs['autoStepDeg']
        if 'tiltStartDeg' in kwargs:
            self.tiltStartDeg = kwargs['tiltStartDeg']
        if 'tiltStopDeg' in kwargs:
            self.tiltStopDeg = kwargs['tiltStopDeg']
        if 'tiltStepDeg' in kwargs:
            self.tiltStepDeg = kwargs['tiltStepDeg']
        if 'autoStartAtt' in kwargs:
            self.autoStartAtt = kwargs['autoStartAtt']
        if 'autoStopAtt' in kwargs:
            self.autoStopAtt = kwargs['autoStopAtt']
        if 'autoStepAtt' in kwargs:
            self.autoStepAtt = kwargs['autoStepAtt']

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
            self.emit(SIGNAL("logUpdate(QString)"), 'TurnTable stopped')
            print "stopping"
        finally:
            self.mutex.unlock()


    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()


    def run(self):
        tt = Turntable.connect("Emco1060", board=0, device=10)
        tilt = Tilt.connect("SC110V", board=0, device=11) # TBD - set board & device
        if self.autorun:
            self.ota = ota.Overtheair(self)
            doAutoAntPattern()
        else:
            tablesweep()

        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        if not self.stopped:
            self.stop()
        self.emit(SIGNAL("finished(bool)"), self.completed)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "0")


    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - COM port number destination
            :disp - optional print output to textBrowser
        """
        if dest == 'sol':
            ser = serial.Serial(self.solcom,115200,timeout=10,writeTimeout=10)
        elif dest == 'lin':
            ser = serial.Serial(self.lincom,115200,timeout=10,writeTimeout=10)
        elif dest == 'rout':
            try:
                ser = serial.Serial(self.routcom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                print "Serial Error in chan chg"
                return 'Error'
                pass
        else:
            return -1
        ser.isOpen()
        out = ''
        ser.write(ToSend + '\r\n')
        time.sleep(.5)
        if dest == 'sol':
        #print ser.inWaiting()
            for x in range(0, 200):
                out += ser.read(ser.inWaiting())
                if 'returns' in out:
                    break
                time.sleep(.05)

        else:
            while ser.inWaiting() > 0:
                out += ser.read(1)
        if out != '' and disp:
            print out
            #form.textBrowser.append(unicode(out))
        return out

    def tablesweep(self):
        for r in range (self.manStart, self.manStop, self.manSweepStep):
            TurnTableControl(r)
            time.sleep(self.manSweepTime)

    def doAutoAntPattern(self):
        self.manual = True
        attenlist = []
        for a in range (self.autoStartAtt, self.autoStopAtt, self.autoStepAtt):
            attenlist.append(r)

        for r in range (self.autoStartDeg, self.autoStopDeg, self.autoStepDeg):
            TurnTableControl(r)
            for t in range (self.tiltStartDeg, self.tiltStopDeg, self.tiltStepDeg):
                TiltControl(t)
                if self.ota.isRunning():
                    self.ota.stop()
                    self.ota.wait()
                self.ota.initialize(
                    self.solcom,
                    self.routcom,
                    self.lincom,
                    self.manual,
                    attenlist,
                    self.commands,
                    self.iperf,
                    self.samples,
                    self.fiveGHz,
                    self.wifiD,
                    self.piAddr)
                self.ota.start()
                time.sleep(3)

    def TurnTableControl(self, degree):
        try:
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Updating Turntable: '+ str(degree))
            self.tt.set(degree)
        except:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Fail Turntable')
            time.sleep(2)

        time.sleep(6)

    def TiltControl(self, degree):
        try:
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Updating Tilt: '+ str(degree))
            self.tilt.set(degree)
        except:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Fail Tilt')
            time.sleep(2)

        time.sleep(6)
