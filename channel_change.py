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

import exceptions
import traceback
import os
import platform
import sys
import re
import time
import serial
import serial.tools.list_ports
import glob
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest
import configobj
import importlib
#from AccessPoints import AccessPoint
import AP

__version__ = "1.0.0"


MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

from TancCommon import FiveGHzRouters, TwofourOnlyRouters

################################################################################

class ChannelChange(QThread):

    debug = True
    PRINT = 1
    NOPRINT = 0
    #INVALID_FIRST_OR_LAST = frozenset("0123456789_")
    #STRIPHTML_RE = re.compile(r"<[^>]*?>", re.IGNORECASE|re.MULTILINE)
    #ENTITY_RE = re.compile(r"&(\w+?);|&#(\d+?);")
    #SPLIT_RE = re.compile(r"\W+", re.IGNORECASE|re.MULTILINE)

    aChannels = [36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,149,153,157,161,165,184,188,192,196,200,204,208,212,216]
    bChannels = [1,2,3,4,5,6,7,8,9,10,11,12,13,14]
    validIpStart = '192.168.'
    sadface = """\n
     .-^^^^^^-.
   .'          '.
  /   O      O   .
 :           `    :
 |                |   Channel Incorrect
 :    .------.    :
  .  '        '  /
   '.          .'
     '-......-'"""


    # Close TCP/IP (SSH) session to Access Point
    def close(self):
        if self.ap:
            del(self.ap)
            self.ap = None


    # Open TCP/IP (SSH) session to Access Point
    def open(self):
        if not self.ap:
            if (self.router in FiveGHzRouters) or (self.band == '2.4' and self.router in TwofourOnlyRouters):
                ap_factory = AP.AccessPointFactory()
                for retry in range(3):
                    try:
                        self.ap = ap_factory.getAccessPoint(self.router, self.band)
                        break
                    except Exception as e:
                        print 'ChannelChange.open exception: ' + str(e.__class__) + ': ' + str(e)
                        traceback.print_exc()
            if not self.ap:
                print 'Could not open router ' + self.router
        return self.ap


    # Destructor
    def __del__(self):
        self.close()

    # Constructor
    # Caveat: cannot change band of object!
    def __init__(self, band, lock, parent = None):
        super(ChannelChange, self).__init__(parent)

        # Validate input
        if not isinstance(band, str):
            raise TypeError('band must be a string')
        if band != '5' and band != '2.4':
            raise ValueError('band must be either "2.4" or "5"')

        self.band               = band
        self.lock               = lock
        self.ap                 = None
        self.mutex              = QMutex()
        self.stopped            = False
        self.completed          = False


    def initialize(self, solcom, routcom, channel, commands, tcpip, router,
                   security, mode, chwidth, otacheck, ssid=None):
        # Validate input
        if not isinstance(solcom, str):
            raise TypeError('solcom must be a string')
        if not isinstance(channel, str):
            raise TypeError('channel must be a string')
        if not isinstance(security, str):
            raise TypeError('security must be a string')
        if not isinstance(mode, str):
            raise TypeError('mode must be a string')
        if not isinstance(chwidth, str):
            raise TypeError('chwidth must be a string')
        if tcpip:
            if not isinstance(router, str):
                raise TypeError('router must be a string')
        else:
            if not isinstance(routcom, str):
                raise TypeError('routcom must be a string')
        if self.band == '5':
            if not int(channel) in ChannelChange.aChannels:
                raise ValueError('channel ' + channel + ' invalid for ' + self.band + ' GHz')
        else:
            if not int(channel) in ChannelChange.bChannels:
                raise ValueError('channel ' + channel + ' invalid for ' + self.band + ' GHz')

        self.solcom             = solcom
        self.routcom            = routcom
        self.channel            = channel
        self.commands           = commands
        self.tcpip              = tcpip
        self.router             = router
        self.mode               = mode
        self.chwidth            = chwidth
        self.security           = security
        self.otacheck           = otacheck
        self.ssid               = ssid

        self.stopped            = False
        self.completed          = False


    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
        finally:
            self.mutex.unlock()


    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()


    def run(self):
        if self.tcpip:
            self.changeProcessIP()
        else:
            self.changeProcess()
        self.stop()
        self.emit(SIGNAL("finished(bool)"), self.completed)
        if self.otacheck:
            self.emit(SIGNAL("otaloop(int)"), int(self.channel))


    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - COM port to send data to ("sol" or "rout")
            :disp - optional print output to textBrowser
        """
        ser = None
        out = 'Error'
        if dest == 'sol':
            for retry in range(3):
                try:
                    ser = serial.Serial(self.solcom,115200,timeout=10,writeTimeout=10)
                    break
                except(OSError, serial.SerialException):
                    print 'Serial Error in ChannelChange ' + self.solcom
                    pass
        elif dest == 'rout':
            try:
                ser = serial.Serial(self.routcom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                print 'Serial Error in ChannelChange ' + self.routcom
                pass
        if ser and ser.isOpen():
            out = ''
            ser.write(str(ToSend + '\r\n'))
            time.sleep(.5)
            if dest == 'sol':
                for x in range(0, 200):
                    out += ser.read(ser.inWaiting())
                    if 'returns' in out:
                        break
                    time.sleep(.025)

            else:
                while ser.inWaiting() > 0:
                    out += ser.read(1)
        if disp and out:
            print out
        return out


    def updateChannel(self, channel):
        if self.band == '5':
            self.emit(SIGNAL("chanaUpdate(QString)"), channel)
        else:
            self.emit(SIGNAL("chanbgUpdate(QString)"), channel)


    # Re-connect to AP
    def connect(self):
        for key in ['connect', 'associate']:
            cmd = self.commands[key]
            if cmd:
                if ChannelChange.debug:
                    print 'ChannelChange.SendCmd(' + cmd + ')'
                self.SendCmd(cmd, 'sol', self.PRINT)


    # Verify IP address and channel
    def verify(self, timeout):
        print 'verify(' + str(timeout) + ')' # TBD
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Verifying IP and channel')
        self.emit(SIGNAL("IPUpdate(QString)"), "No IP")
        ipInfo      = None
        ip          = None
        channel     = None
        channelSent = None
        count = 0
        t = time.clock()
        while (count < timeout) and not (ip and channel):
            self.emit(SIGNAL("auxstatUpdate(QString)"), str(count) + ' seconds')
            print 'ChannelChange.verify: ' + str(count) + ' seconds'
            ipInfo = self.SendCmd(self.commands['get_config'], 'sol', self.PRINT)

            # Supress unwanted sol serial port output
            lines = ipInfo.split('\n')
            ipInfo = ''
            for line in lines:
                if ':' in line:
                    if len(ipInfo) == 0:
                        ipInfo = line
                    else:
                        ipInfo += '\n' + line

            if 'IPv4 address configured by AutoIP' in ipInfo:
                ipInfo = 'ChannelChange.verify: AutoIP invalid\n' + ipInfo
                print 'ChannelChange.verify: ' + ipInfo
                self.emit(SIGNAL("logUpdate(QString)"), ipInfo)
            else:
                #Find IP address update Text, Channel and Select if SOL/std
                m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', ipInfo, re.U)
                chan = re.search('Channel:\s+(\d{1,3})', ipInfo, re.U)
                if m and chan:
                    if m.group(1):
                        ip = str(m.group(1))
                    elif m.group(2):
                        ip = str(m.group(2))
                    channel = str(chan.group(1))
                    if channel and channelSent != channel:
                        self.updateChannel(channel)
                        channelSent = channel
                    if ip and channel:
                        self.emit(SIGNAL("IPUpdate(QString)"), ip)
                        if ip.startswith(ChannelChange.validIpStart):
                            try:
                                if int(self.channel) == int(channel):
                                    break
                                else:
                                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Channel Incorrect!")
                                    self.emit(SIGNAL("logUpdate(QString)"), \
                                    "Incorrect Channel on printer: requested=" + self.channel + " reported=" + channel)
                                    channel = None
                                    self.connect()
                            except (ValueError, AttributeError):
                                pass
                        else:
                            ip = None
            count += 1
            t += 1
            now = time.clock()
            if t > now:
                time.sleep(t - now)

        if ip and channel:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Channel Verified')
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Channel change Success!')
            self.emit(SIGNAL("logUpdate(QString)"), 'Channel ' + self.channel + ' change Success in ' + str(count) + ' seconds!\n' + ipInfo)
        else:
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Channel change Failure!')
            self.emit(SIGNAL("logUpdate(QString)"), 'Channel ' + self.channel + ' change Failure in ' + str(count) + ' seconds!')
            self.emit(SIGNAL("logUpdate(QString)"), ChannelChange.sadface) # TBD - this is silly!
        time.sleep(2)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        self.emit(SIGNAL("auxstatUpdate(QString)"), '0')


    def changeProcessIP(self):
        print 'changeProcessIP:'\
            + ' router='   + self.router\
            + ' solcom='   + self.solcom\
            + ' channel='  + self.channel\
            + ' chwidth='  + self.chwidth\
            + ' mode='     + self.mode\
            + ' security=' + self.security

        # Update Access Point settings
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Changing Channel Settings')
        self.open()
        if self.ap:
            #print 'Channel ' + self.channel + '. In changeProcessIP ' + self.band + ' GHz'
            bChanged = False
            # TBD - AccessPointWl doesn't correctly handle mode
            if self.ssid and self.ap.GetSSID() != self.ssid:
                if ChannelChange.debug:
                    print 'SetSSID(' + self.ssid + ')'
                self.ap.SetSSID(self.ssid)
            if self.ap.GetMode() != self.mode and self.router != 'rtac68u':
                if ChannelChange.debug:
                    print 'SetMode(' + self.mode + ')'
                self.ap.SetMode(self.mode)
                bChanged = True
            if self.ap.GetChannel() != self.channel:
                if ChannelChange.debug:
                    print 'SetChannel(' + self.channel + ')'
                self.ap.SetChannel(self.channel)
                bChanged = True
            # TBD: There is no GetSecurity() method!
            #if self.ap.GetSecurity() != self.security:
            #    self.ap.SetSecurity(self.security)
            #    bChanged = True
            current = str(self.ap)
            m = re.search('security:\s*(\S+)', current, re.U)
            if m and m.group(1):
                security = str(m.group(1))
                if security != self.security:
                    if ChannelChange.debug:
                        print 'SetSecurity(' + self.security + ')'
                    self.ap.SetSecurity(self.security)
                    bChanged = True
            if self.ap.GetBroadcast() != True:
                if ChannelChange.debug:
                    print 'SetBroadcast(True)'
                self.ap.SetBroadcast(True)
                bChanged = True
            if self.ap.GetChannelWidth() != self.chwidth:
                if ChannelChange.debug:
                    print 'SetChannelWidth(' + self.chwidth + ')'
                self.ap.SetChannelWidth(self.chwidth)
                bChanged = True
            if bChanged:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Commiting Setting Changes')
                if ChannelChange.debug:
                    print 'Post'
                self.ap.Post()
                time.sleep(3)
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router back up')
                channel = self.ap.GetChannel()
                if self.channel != channel:
                    print 'changeProcessIP: requested=' + self.channel + ' != actual=' + channel + '!!!!!!!!!'
                else:
                    print 'changeProcessIP: requested==actual=' + channel
            else:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'No changes')

        self.connect()
        time.sleep(3)
        self.verify(60)


    def changeProcess(self):
        print 'changeProcess:'\
            + ' routcom='  + self.routcom\
            + ' solcom='   + self.solcom\
            + ' channel='  + self.channel\
            + ' chwidth='  + self.chwidth\
            + ' mode='     + self.mode\
            + ' security=' + self.security

        whichrout = self.SendCmd('wl_iocmd ver', 'rout', self.NOPRINT)
        ans = re.search('version', whichrout)
        if ans:
            wlcmd = 'wl_iocmd '
        else:
            wlcmd = 'wl '
        if self.band == '5':
            wlcmd += '-i eth2 '

        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router Down for setting changes')
        self.SendCmd(self.wlcmd + 'down', 'rout', self.PRINT)
        time.sleep(1)

        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Changing Channel Settings')
        cmdsend = self.wlcmd + 'channel ' + self.channel
        routResponse = self.SendCmd(cmdsend, 'rout', self.PRINT)
        if (routResponse.find('Bad Channel') == -1) and  \
           (routResponse.find('Out of Range') == -1) and \
           (routResponse.find('not found') == -1):
            if self.band == '5':
                self.SendCmd('nvram set wl1_channel=' + self.channel, 'rout', self.PRINT)
            else:
                # TBD: document which routers require each of these serial commands
                self.SendCmd('nvram set channel_24g=' + self.channel, 'rout', self.PRINT)
                self.SendCmd('nvram set wl0_channel=' + self.channel, 'rout', self.PRINT)
                self.SendCmd('nvram set wl_channel='  + self.channel, 'rout', self.PRINT)
                self.SendCmd('nvram set wla_channel=' + self.channel, 'rout', self.PRINT)

            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Commiting Setting Changes')
            self.SendCmd('nvram commit','rout',self.PRINT)

        self.SendCmd(self.wlcmd + 'up', 'rout', self.PRINT)
        time.sleep(3)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router back up')

        self.connect()
        self.verify(60)


################################################################
################   ___   __ __  ________  __    ################
################  |__ \ / // / / ____/ / / /___ ################
################  __/ // // /_/ / __/ /_/ /_  / ################
################ / __//__  __/ /_/ / __  / / /_ ################
################/____(_)/_/  \____/_/ /_/ /___/ ################
################                                ################
################################################################
class ChannelChangebg(ChannelChange):

     def __init__(self, lock, parent=None):
        super(ChannelChangebg, self).__init__('2.4', lock, parent)

################################################################
##################    ______________  __     ###################
##################   / ____/ ____/ / / /___  ###################
##################  /___ \/ / __/ /_/ /_  /  ###################
################## ____/ / /_/ / __  / / /_  ###################
##################/_____/\____/_/ /_/ /___/  ###################
##################                           ###################
################################################################

class ChannelChangea(ChannelChange):

    def __init__(self, lock, parent=None):
        super(ChannelChangea, self).__init__('5', lock, parent)
