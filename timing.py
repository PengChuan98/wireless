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
import time
import subprocess
import math
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest

import numpy as np
from devices import Attenuator, GpibDevice, JFW50PA, apcpdu

__version__ = "1.0.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False


####################################################################
####  _______ _           _               __  __       _        ####
#### |__   __(_)         (_)             |  \/  |     (_)       ####
####    | |   _ _ __ ___  _ _ __   __ _  | \  / | __ _ _ _ __   ####
####    | |  | | '_ ` _ \| | '_ \ / _` | | |\/| |/ _` | | '_ \  ####
####    | |  | | | | | | | | | | | (_| | | |  | | (_| | | | | | ####
####    |_|  |_|_| |_| |_|_|_| |_|\__, | |_|  |_|\__,_|_|_| |_| ####
####                               __/ |                        ####
####                              |___/                         ####
####################################################################

class Timing(QThread):

    PRINT = 1
    NOPRINT = 0
    rssi_timepoint = pyqtSignal(list)

    def __init__(self, parent=None):
        super(Timing, self).__init__(parent)
        self.stopped = False
        self.mutex = QMutex()
        self.completed = False


    def initialize(self, solcom, routcom, lincom, commands, rssi50, rssi80,\
        findAPchk, connAP, connAfterIntrchk, connFromBootchk, fiveGHz, direct,\
        apcIP, outlet, ssid, samples, curAtten):
        self.solcom           = solcom
        self.routcom          = routcom
        self.lincom           = lincom
        self.commands         = commands
        self.rssi50           = rssi50
        self.rssi80           = rssi80
        self.findAPchk        = findAPchk
        self.connAP           = connAP
        self.connAfterIntrchk = connAfterIntrchk
        self.connFromBootchk  = connFromBootchk
        self.fiveGHz          = fiveGHz
        self.wifiD            = direct
        self.apcIP            = apcIP
        self.outlet           = outlet
        self.ssid             = ssid
        self.numSamp          = int(samples)
        self.finalAtten       = curAtten

        self.onlyRSSI         = False


    def onlyRSSIset(self, RSSI, solcom):
        self.targetRSSI = RSSI
        self.solcom = solcom
        self.onlyRSSI = True

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
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

        if not self.ipaddrCheck(4):
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Not Connected')
            self.connectToNet()
        if self.onlyRSSI:
            self.setRSSI(self.targetRSSI)
        else:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting Timing Tests')
            if self.rssi50:
                self.targetRSSI = -50
                self.setRSSI(self.targetRSSI)
                self.timingTests()
                self.calculations()
            if self.rssi80:
                self.targetRSSI = -80
                self.setRSSI(self.targetRSSI)
                self.timingTests()
                self.calculations()
            if not (self.rssi50 or self.rssi80):
                self.targetRSSI = self.finalAtten
                self.timingTests()
                self.calculations()
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
            if not self.stopped:
                self.stop()
            self.emit(SIGNAL("finished(bool)"), self.completed)
            self.emit(SIGNAL("auxstatUpdate(QString)"), "0")


    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - destination ('sol', 'lin', or 'rout')
            :disp - optional print output to textBrowser
        """
        if dest == 'sol':
            try:
                ser = serial.Serial(self.solcom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                return 'Error'
                pass
        elif dest == 'lin':
            try:
                ser = serial.Serial(self.lincom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                return 'Error'
                pass
        elif dest == 'rout':
            try:
                ser = serial.Serial(self.routcom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                return 'Error'
                pass
        else:
            return -1
        ser.isOpen()
        out = ''
        time.sleep(.2)
        ser.write(ToSend + '\r\n')
        time.sleep(.3)
        if dest == 'sol':
        #print ser.inWaiting()
            for x in range(0, 200):
                out += ser.read(ser.inWaiting())
                if 'UDW bad command' in out:
                    time.sleep(.25)
                    ser.write(ToSend + '\r\n')
                    time.sleep(.25)
                    out = ''
                elif 'returns' in out:
                    break

                time.sleep(.05)

        else:
            while ser.inWaiting() > 0:
                out += ser.read(1)
        if out != '' and disp:
            print out
            #form.textBrowser.append(unicode(out))
        ser.close()
        return out

    def calculations(self):
        info = []
        times = []
        print '========TIME SUMMARY========\n'
        print 'findTime: ',self.ftaray,'\n', 'connectTime: ',self.ctaray,'\n', 'interruptRecoverTime: ', self.itaray,'\n', 'powerRecoverTime: ', self.rtaray
        if self.ftaray:
            std = np.nanstd(self.ftaray)
            ave = [np.nanmean(self.ftaray)]
            ave.extend([std, max(self.ftaray), min(self.ftaray)])
            info.append(ave)
        else:
            info.append(None)
        if self.ctaray:
            std = np.nanstd(self.ctaray, axis=0).tolist()
            ave = np.nanmean(self.ctaray, axis=0).tolist()
            times = [x[1] for x in self.ctaray]
            ave.extend([std[1], max(times), min(times)])
            info.append(ave)
        else:
            info.append(None)
        if self.ftaray and self.ctaray:
            ave = [info[1][0],info[0][0]+info[1][1], np.sqrt(np.power(info[0][1],2)+np.power(info[1][2],2))]
            info.append(ave)
        else:
            info.append(None)
        if self.itaray:
            std = np.nanstd(self.itaray, axis=0).tolist()
            ave = np.nanmean(self.itaray, axis=0).tolist()
            times = [x[1] for x in self.itaray]
            ave.extend([std[1], max(times), min(times)])
            info.append(ave)
        else:
            info.append(None)
        if self.rtaray:
            std = np.nanstd(self.rtaray, axis=0).tolist()
            ave = np.nanmean(self.rtaray, axis=0).tolist()
            times = [x[1] for x in self.rtaray]
            ave.extend([std[1], max(times), min(times)])
            info.append(ave)
        else:
            info.append(None)
        self.rssi_timepoint.emit(info)

    def ipaddrCheck(self,checkTime):
        #self.emit(SIGNAL("mainstatUpdate(QString)"), 'Verify connection')
        ipexist = False
        for chk in range(checkTime):
            self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address check #" + str(chk))
            ipInfo = self.SendCmd(self.commands['get_config'], 'sol', self.NOPRINT)
            m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', ipInfo, re.U)
            if m:
                if m.group(1) is not None and (m.group(1) != '0.0.0.0'):
                    self.IPaddr = str(m.group(1))
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address valid")
                    ipexist = True
                    break
                else:
                    time.sleep(1)
                if m.group(2) is not None and (m.group(2) != '0.0.0.0'):
                    self.IPaddr = str(m.group(2))
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address valid")
                    ipexist = True
                    break
                else:
                    time.sleep(1)
            else:
                time.sleep(1)
        if ipexist:
            return True
        else:
            return False

    def timingTests(self):
        self.ftaray = []
        self.ctaray = []
        self.itaray = []
        self.rtaray = []
        reset_flag = False
        for samp in range(self.numSamp):
            if self.findAPchk:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting Find AP #'+str(samp+1))
                if not reset_flag:
                    self.networkReset()
                    reset_flag = True
                begin = time.time()
                if self.findAP():
                    findtime = time.time() - begin
                    print 'findTime: ', findtime
                    self.ftaray.append(findtime)
                else:
                    self.ftaray.append(np.nan)
            if self.connAP:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting timing for Connecting to AP #'+str(samp+1))
                if not reset_flag:
                    self.networkReset()
                    reset_flag = True
                begin = time.time()
                self.connectToNet()
                reset_flag = False
                if self.ipaddrCheck(120):
                    contime = time.time() - begin
                    print 'conTime: ', contime

                    self.ctaray.append([self.getRSSI(),contime])
                else:
                    self.ctaray.append([self.getRSSI(),np.nan])
            if self.connAfterIntrchk:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting timing for Interrupt Recovery #'+str(samp+1))
                self.AttenControl(79, False)
                for t in range(60):
                    self.emit(SIGNAL("auxstatUpdate(QString)"), str(60-t)+'s left for interrupt')
                    time.sleep(1)
                self.emit(SIGNAL("auxstatUpdate(QString)"), "Recovering")
                self.AttenControl(self.finalAtten, False)
                begin = time.time()
                if self.ipaddrCheck(120):
                    intTime = time.time() - begin
                    print 'intTime: ', intTime
                    self.itaray.append([self.getRSSI(),intTime])
                else:
                    self.itaray.append([self.getRSSI(),np.nan])
            if self.connFromBootchk:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting timing for Reboot Recovery #'+str(samp+1))
                self.emit(SIGNAL("auxstatUpdate(QString)"), "Retting power on printer")
                if self.powerReset():
                    time.sleep(8)
                    begin = time.time()
                    if self.ipaddrCheck(150):
                        rebootTime = time.time() - begin
                        print 'reboot: ', rebootTime
                        self.rtaray.append([self.getRSSI(),rebootTime])
                else:
                    self.rtaray.append([self.getRSSI(),np.nan])

    def findAP(self):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Finding SSID passive scan: ' + self.ssid)
        found = False
        for k in range(6):
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'check #' + str(k))
            cmdscan='udws "nca.get_wireless_scan"'
            time.sleep(.1)
            ssidlist = self.SendCmd(cmdscan,'sol',self.PRINT)
            m = re.search(self.ssid, ssidlist, re.U)
            errno = re.search('Connection timed out', ssidlist, re.U)
            if m:
                found = True
                break
            elif errno:
                strcmdx='udws "nca.disable_adaptor"'
                self.SendCmd(strcmdx,'sol',self.PRINT)
                time.sleep(2)
                strcmdx='udws "nca.enable_adaptor"'
                time.sleep(10)
            else:
                time.sleep(3.9)
        return found

    def networkReset(self):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Setting Wifi to Factory Defaults')
        self.SendCmd(self.commands['defaults'], 'sol', self.PRINT)
        self.SendCmd(self.commands['reset'   ], 'sol', self.PRINT)
        for x in range(45):  #Waiting for reset to finish
            timeleft=45-x
            self.emit(SIGNAL("auxstatUpdate(QString)"), str(timeleft) + ' s left')
            time.sleep(1)
        cmd = 'udws "nca.set_adaptor_power_state WIFI0, 1 "'
        self.SendCmd(cmd, 'sol', self.PRINT)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Finished Wifi Reset')


    def connectToNet(self):
        self.SendCmd(self.commands['connect'], 'sol', self.PRINT)


    def powerReset(self):
        pdu = apcpdu('snmp', self.apcIP)
        actualPorts = pdu.snmp().sPDUOutletConfigTableSize()+1
        self.emit(SIGNAL("auxstatUpdate(QString)"), 'Reset Outlet# '+ str(self.outlet))
        try:
            if (self.outlet)>actualPorts:
                return False
            else:
                pdu.snmp().sPDUOutletCtl(int(self.outlet), 3)   #Reset
                return True
        except:
            print 'EXCEPTION ERROR'
            return False


    def getRSSI(self):
        SNRInfo = self.SendCmd(self.commands['get_config'], 'sol', self.NOPRINT)
        #Find RSSI and Noise
        rssi = re.search('signalStrength:\s*(-\d+)', SNRInfo, re.U)
        if rssi:
            if rssi.group(1) is not None:
                rssi = rssi.group(1)
                return int(rssi)
            else:
                return self.targetRSSI
        elif rssi is None:      #backup command to get rssi
            SNRInfo = self.SendCmd(self.commands['get_rssi'], 'sol', self.NOPRINT)
            #Find RSSI and Noise
            rssi = re.search('(-\d{2})', SNRInfo, re.U)
            if rssi is not None:
                rssi = rssi.group(1)
                return int(rssi)
            else:
                return self.targetRSSI
        else:
            return self.targetRSSI

    def setRSSI(self, targetRSSI):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Setting to Target RSSI: ' + str(targetRSSI))
        rssi = self.getRSSI()
        print 'current RSSI', rssi, '\ttarget: ',targetRSSI
        if (rssi > (targetRSSI-3)) and (rssi < (targetRSSI+3)):
            print 'it is all good'
            pass
        else:
            searchary = [15,8,4,2,1]
            self.finalAtten = 30
            self.AttenControl(self.finalAtten, True)
            for x in range(5):
                if not self.ipaddrCheck(10):
                    self.finalAtten -= searchary[x]
                rssi = self.getRSSI()
                print 'RSSI: ', rssi
                if rssi:
                    if int(targetRSSI) > int(rssi):
                        self.finalAtten -= searchary[x]
                        print 'target is lower db reduce attenution'
                    elif int(targetRSSI) < int(rssi):
                        self.finalAtten += searchary[x]
                        print 'target is higher db increase attenution'
                    else:
                        print 'target is reached'
                        break
                    self.AttenControl(self.finalAtten, True)

        self.onlyRSSI = False


    def AttenControl(self, attnstr, wait):
        val = int(attnstr)
        if val > 79:
            val = 79
        elif val < 0:
            val = 0
        self.emit(SIGNAL("AttenUpdate(QString)"), str(val))
        if wait:
            time.sleep(12)
