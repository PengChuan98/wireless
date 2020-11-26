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
import serial
import serial.tools.list_ports
import time
import glob
import subprocess
import hpTCP
#from collections import deque
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest
import channel_change
from numpy import *
#import configobj
#import importlib
from AccessPoints import *
import AP
from numpy.random import rand

__version__ = "1.0.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

from TancCommon import FiveGHzRouters, TwofourOnlyRouters, mapRouter


class AutoNFBase(QThread):
    PRINT = 1
    NOPRINT = 0
    validIpStart = '192.168.'

    def __init__(self, parent=None):
        super(AutoNFBase, self).__init__(parent)
        self.mutex = QMutex()
        self.ap = None
        self.stopped = False
        self.completed = False

    def initialize(self, solcom, lincom, routcom):
        if not isinstance(solcom, str):
            raise TypeError('solcom must be a string')
        if not isinstance(lincom, str):
            raise TypeError('lincom must be a string')
        if not isinstance(routcom, str):
            raise TypeError('routcom must be a string')
        self.solcom     = solcom
        self.lincom     = lincom
        self.routcom    = routcom
        self.stopped    = False
        self.completed  = False

    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
        finally:
            self.mutex.unlock()

    def logUpdate(self, statusUpdate):
        self.emit(SIGNAL("logUpdate(QString)"), statusUpdate)

    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - destination ('sol', 'lin', or 'rout')
            :disp - optional print output to textBrowser
        """
        out = ''
        ser = None
        if dest == 'sol':
            com = self.solcom
        elif dest == 'lin':
            com = self.lincom
        elif dest == 'rout':
            com = self.routcom
        else:
            print 'SendCmd invalid dest: ' + dest
            return 'Error'
        try:
            ser = serial.Serial(com, 115200, timeout=10, writeTimeout=10)
        except(OSError, serial.SerialException):
            print 'Serial Error on port ' + com
            return 'Error'
        if ser.isOpen():
            ser.write(ToSend + '\r\n')
            time.sleep(.5)
            if dest == 'sol':
                # udws command should output "returns" followed by an integer
                for x in range(0, 200):
                    out += ser.read(ser.inWaiting())
                    if 'returns' in out:
                        break
                    time.sleep(.05)

            else:
                while ser.inWaiting() > 0:
                    out += ser.read(1)
        else:
            print 'Serial port ' + com + ' not open'
            return 'Error'
        if out != '' and disp:
            print out
        # form.textBrowser.append(unicode(out))
        return out



######################################################################
####                _        _   _ ______   __  __       _        ####
####     /\        | |      | \ | |  ____| |  \/  |     (_)       ####
####    /  \  _   _| |_ ___ |  \| | |__    | \  / | __ _ _ _ __   ####
####   / /\ \| | | | __/ _ \| . ` |  __|   | |\/| |/ _` | | '_ \  ####
####  / ____ \ |_| | || (_) | |\  | |      | |  | | (_| | | | | | ####
#### /_/    \_\__,_|\__\___/|_| \_|_|      |_|  |_|\__,_|_|_| |_| ####
####                                                              ####
######################################################################

class AutoNF(AutoNFBase):
    debug = True
    noiseFList = pyqtSignal(list)
    rssiList = pyqtSignal(list)

    def __init__(self, parent=None):
        super(AutoNF, self).__init__(parent)

    def initialize(self, solcom, routcom, lincom, channel_list, commands,
                   rundata, iperf, samples, mimo, is5GHz, direct, tcpip, router,
                   security, mode, chwidth):
        super(AutoNF, self).initialize(solcom, lincom, routcom)
        for s in channel_list:
            if not isinstance(s, str):
                raise TypeError('channel_list elements must be strings')
        self.channels   = channel_list
        self.commands   = commands
        self.rundata    = rundata
        self.iperf      = iperf
        self.samples    = samples
        self.mimo       = mimo
        self.is5GHz     = is5GHz
        self.wifiD      = direct
        self.tcpip      = tcpip
        self.router     = mapRouter(router)
        self.security   = security
        self.mode       = mode
        self.chwidth    = chwidth
        if is5GHz:
            self.band = '5'
        else:
            self.band = '2.4'
        self.mantp      = None

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
            try:
                if self.mantp and self.mantp.isRunning():
                    self.mantp.stop()
                    self.mantp.wait()
            except:
                pass
        finally:
            self.mutex.unlock()

    def run(self):
        # TBD: channels should be array of python strings
        for channel in self.channels:
            self.endhptcp()
            if self.stopped:
                break
            if self.tcpip:
                self.changeProcessIP(channel)
            else:
                self.changeProcess(channel)
            self.autosweep(self.samples, channel, self.mimo)
            if self.stopped:
                break
        self.stop()
        if self.rundata:
            if self.iperf:
                self.endiperf()
            else:
                self.endhptcp()
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        self.emit(SIGNAL("auxstatUpdate(QString)"), "0")
        self.emit(SIGNAL("finished(bool)"), self.completed)

    def startiperf(self, ip, iperfTime):
        self.mantp = ManualTP(self)
        self.connect(self.mantp, SIGNAL("logUpdate(QString)"), self.logUpdate)
        try:
            if self.mantp.isRunning():
                self.mantp.stop()
                self.mantp.wait()
            self.mantp.initialize(self.solcom, self.lincom, ip, \
                                  True, True, iperfTime, '#[KMG]', '1', '9101', '1', '1')
            # True = bandwidth testing via iperf program
            # True = Turn on iperf verbosity
            # time for iperf to run
            # unlimited bandwidth
            # 1 second interval between reports
            # port for hptcptest [does not matter here]
            # time for hptcptest [does not matter here]
            # interval for hptcptest [does not matter here]

            self.mantp.start()
        except(ValueError):
            pass

    def endiperf(self):
        self.emit(SIGNAL("auxstatUpdate(QString)"), "terminating iperf server")
        try:
            linux = serial.Serial(self.lincom, 115200, writeTimeout=None)
            linux.write('\x03' + '\r\n')  # send Ctrl-C
            linux.write('kill $(ps | grep iperf[3] | awk \'{print $1}\')' + '\r\n')
            linux.close()
        except(OSError, serial.SerialException):
            pass

    def ipcheck(self):
        IPaddr = None
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Verify connection')
        self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address check")
        for x in range(1, 60):
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'check number: ' + str(x) + '/60')
            ipInfo = self.SendCmd(self.commands['get_config'], 'sol', 1)
            m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', ipInfo, re.U)
            if m:
                if m.group(1):
                    IPaddr = str(m.group(1))
                elif m.group(2):
                    IPaddr = str(m.group(2))
                if IPaddr != "0.0.0.0":
                    print 'IP=' + IPaddr
                    return IPaddr
            else:
                time.sleep(1)
        return None

    def starthptcp(self, ip, tcpTime):
        self.emit(SIGNAL("hptcpIter(int)"), tcpTime)
        self.emit(SIGNAL("hptcptime(int)"), 1)
        self.emit(SIGNAL("starthptcp(QString)"), ip)

    def endhptcp(self):
        self.emit(SIGNAL("stoptcp(bool)"), True)

    def autosweep(self, samples, channel, mimo):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting Autosweep')
        #dtbegin = time.strftime("%b %d %Y %H:%M:%S")
        self.SendCmd(self.commands['stop_log'], 'sol', self.PRINT)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Overhead logging off")
        self.SendCmd(self.commands['no_sleep'], 'sol', self.PRINT)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Sleep off")

        time.sleep(3)
        if self.wifiD:
            IPaddr = '192.168.223.1'
        else:
            IPaddr = self.ipcheck()

        if IPaddr:
            self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address valid")
            self.emit(SIGNAL("IPUpdate(QString)"), IPaddr)
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Check if enable data stream')
            if self.rundata:
                if self.iperf:
                    self.endiperf()
                    time.sleep(4)
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Iperf starting")
                    iperfTime = 1.5 * int(samples)
                    self.startiperf(IPaddr, iperfTime)
                else:
                    time.sleep(1)
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Running hpTCPtest")
                    runTime = 1.5 * int(samples)
                    self.starthptcp(IPaddr, runTime)
            else:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'No Data Stream')
                self.emit(SIGNAL("auxstatUpdate(QString)"), "0")
            time.sleep(6)

            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Running Noise Floor')
            self.emit(SIGNAL("auxstatUpdate(QString)"), "checking if mimo ant")
            x = range(int(samples))
            if mimo:
                ants = (1, 2, 3)
            else:
                ants = (1, 2)

            for ant in ants:
                if self.stopped:
                    break
                if ant == 1:
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 1")
                    self.emit(SIGNAL("antUpdate(QString)"), "1")
                    self.SendCmd(self.commands['antenna_1'], 'sol', self.PRINT)
                elif ant == 2:
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 2")
                    self.emit(SIGNAL("antUpdate(QString)"), "2")
                    self.SendCmd(self.commands['antenna_2'], 'sol', self.PRINT)
                else:
                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna diversity")
                    self.emit(SIGNAL("antUpdate(QString)"), "all")
                    self.SendCmd(self.commands['antenna_all'], 'sol', self.PRINT)
                time.sleep(6)  # wait for ant change
                ii = 0
                NFFarray = []
                RSSIarray = []
                # signal here to change the antenna!!!
                try:
                    ser = serial.Serial(self.solcom, 115200, timeout=10, writeTimeout=10)
                except(OSError, serial.SerialException):
                    self.emit(SIGNAL("mainstatUpdate(QString)"), 'Sirius serial port cannot be reached')
                    print "Serial Error in chan chg"
                self.emit(SIGNAL("time(QString)"), 'begin')
                while ii < int(samples) and not self.stopped:

                    SNRInfo = ''
                    if ser.isOpen():
                        ser.write(self.commands['get_config'] + '\r\n')
                        time.sleep(.5)
                        for x in range(0, 200):
                            SNRInfo += ser.read(ser.inWaiting())
                            if 'returns' in SNRInfo:
                                break
                            time.sleep(.05)

                        noise = re.search('noise:\s*(-\d+)', SNRInfo, re.U)
                        rssi = re.search('signalStrength:\s*(-\d+)', SNRInfo, re.U)
                        if noise and rssi:
                            if noise.group(1):
                                NFFarray.append(int(noise.group(1)))
                                ii += 1
                                self.emit(SIGNAL("auxstatUpdate(QString)"), 'sample: ' + str(ii) + '/' + str(samples))
                            if rssi.group(1):
                                RSSIarray.append(int(rssi.group(1)))
                            if noise.group(1) and rssi.group(1):
                                print 'noise=' + noise.group(1) + ' rssi=' + rssi.group(1)
                            elif noise.group(1):
                                print 'noise=' + noise.group(1)
                            elif rssi.group(1):
                                print 'rssi=' + rssi.group(1)
                        else:
                            pass
                    else:
                        break
                self.emit(SIGNAL("time(QString)"), 'end')
                ser.close()

                #############HOW TO PLOT WITH MATLIBPLOT#####################
                self.emit(SIGNAL("auxstatUpdate(QString)"), 'Plotting Noise Floor')
                self.noiseFList.emit(NFFarray)
                self.rssiList.emit(RSSIarray)
                #       case = int(channel) % 3
                #       if case == 0:
                #           color = 'blue'
                #       elif case == 1:
                #           color = 'green'
                #       elif case == 2:
                #           color = 'red'
                #       if ant == 0:
                #           marker = '-o'
                #       elif ant == 1:
                #           marker = '-x'
                #       #print x
                #       #print NFFarray
                #       linelabel = 'channel '+str(channel)+ ' --- ant '+ str(ant)
                #       plt.ylim(-100, -65)
                #       #plt.plot(x, asarray(NFFarray))
                #       ml = MultipleLocator(1)
                #       #ax = self.fig.add_axes([0.1, 0.1, 0.6, 0.75])
                #       plt.plot(x, asarray(NFFarray), marker, c=color, label=linelabel,
                #               alpha=1)
                #       plt.xlabel('pts', size=22)
                #       plt.ylabel('NF (dBm)', size=22)
                #       plt.axes().yaxis.set_minor_locator(ml)
                #       #ax.yaxis.set_minor_locator(ml)
                #       lgd = plt.legend(loc='center left', bbox_to_anchor=(1, 1))
                #       plt.grid(True)
                #       #draw()
                #       plt.savefig('pltimage',dpi=600, bbox_extra_artists=(lgd,), bbox_inches='tight')
                #       print "matplotlib plt on other thread"
                #############HOW TO PLOT WITH MATLIBPLOT#####################

                if self.rundata and not self.iperf:
                    subprocess.call('taskkill /F /im hptcptest.exe')

                self.completed = True
        else:
            pass  # if no IP skip Noise Floor Collection

    # Open TCP/IP (session to Access Point
    def open(self):
        if not self.ap:
            if (self.router in FiveGHzRouters) or (self.band == '2.4' and self.router in TwofourOnlyRouters):
                ap_factory = AP.AccessPointFactory()
                for retry in range(3):
                    try:
                        self.ap = ap_factory.getAccessPoint(self.router, self.band)
                        break
                    except Exception as e:
                        print 'AutoNF.open exception: ' + str(e.__class__) + ': ' + str(e)
                        traceback.print_exc()
            if not self.ap:
                print 'Could not open router ' + self.router
        return self.ap

    def updateChannel(self, channel):
        if self.band == '5':
            self.emit(SIGNAL("chanaUpdate(QString)"), channel)
        else:
            self.emit(SIGNAL("chanbgUpdate(QString)"), channel)

    # Re-connect to AP
    def associate(self):
        for key in ['connect', 'associate']:
            cmd = self.commands[key]
            if cmd:
                if AutoNF.debug:
                    print 'AutoNF.SendCmd(' + cmd + ')'
                self.SendCmd(cmd, 'sol', self.PRINT)

    # Verify IP address and channel
    # Returns True if IP address and channel verified correct
    def verify(self, timeout):
        print 'verify(' + str(timeout) + ')' # TBD
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Verifying IP and channel')
        self.emit(SIGNAL("IPUpdate(QString)"), "No IP")
        result      = False
        ipInfo      = None
        ip          = None
        channel     = None
        channelSent = None
        count = 0
        t = time.clock()
        while (count < timeout) and not (ip and channel):
            self.emit(SIGNAL("auxstatUpdate(QString)"), str(count) + ' seconds')
            print 'AutoNF.verify: ' + str(count) + ' seconds'
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
                ipInfo = 'AutoNF.verify: AutoIP invalid\n' + ipInfo
                print 'AutoNF.verify: ' + ipInfo
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
                        if ip.startswith(AutoNF.validIpStart):
                            try:
                                if int(self.channel) == int(channel):
                                    break
                                else:
                                    self.emit(SIGNAL("auxstatUpdate(QString)"), "Channel Incorrect!")
                                    self.emit(SIGNAL("logUpdate(QString)"), \
                                    "Incorrect Channel on printer: requested=" + self.channel + " reported=" + channel)
                                    channel = None
                                    self.associate()
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
            result = True
        else:
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Channel change Failure!')
            self.emit(SIGNAL("logUpdate(QString)"), 'Channel ' + self.channel + ' change Failure in ' + str(count) + ' seconds!')
        time.sleep(2)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        self.emit(SIGNAL("auxstatUpdate(QString)"), '0')
        return result

    def changeProcessIP(self, channel):
        if not isinstance(channel, str):
            raise TypeError('channel must be a string')
        self.channel = channel
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
            bChanged = False
            # TBD - AccessPointWl doesn't correctly handle mode
            if self.ap.GetMode() != self.mode and self.router != 'rtac68u':
                if AutoNF.debug:
                    print 'SetMode(' + self.mode + ')'
                self.ap.SetMode(self.mode)
                bChanged = True
            if self.ap.GetChannel() != self.channel:
                if AutoNF.debug:
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
                    if AutoNF.debug:
                        print 'SetSecurity(' + self.security + ')'
                    self.ap.SetSecurity(self.security)
                    bChanged = True
            if self.ap.GetBroadcast() != True:
                if AutoNF.debug:
                    print 'SetBroadcast(True)'
                self.ap.SetBroadcast(True)
                bChanged = True
            if self.ap.GetChannelWidth() != self.chwidth:
                if AutoNF.debug:
                    print 'SetChannelWidth(' + self.chwidth + ')'
                self.ap.SetChannelWidth(self.chwidth)
                bChanged = True
            if bChanged:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Commiting Setting Changes')
                if AutoNF.debug:
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

        self.associate()
        time.sleep(3)
        return self.verify(60)

    def changeProcess(self, channel):
        if not isinstance(channel, str):
            raise TypeError('channel must be a string')
        print 'changeProcess:'\
            + ' routcom='  + self.routcom\
            + ' solcom='   + self.solcom\
            + ' channel='  + self.channel\
            + ' chwidth='  + self.chwidth\
            + ' mode='     + self.mode\
            + ' security=' + self.security
        if self.is5GHz:
            # 5 GHz
            whichrout = self.SendCmd('wl_iocmd ver', 'rout', self.NOPRINT)
            ans = re.search('version', whichrout)
            if ans:
                self.wlcmd = 'wl_iocmd '
            else:
                self.wlcmd = 'wl '
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router Down for setting changes')
            self.SendCmd(self.wlcmd + '-i eth2 down', 'rout', 1)
            time.sleep(1)
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Changing Channel Settings')
            cmdsend = self.wlcmd + '-i eth2 channel ' + str(channel)
            routResponse = self.SendCmd(cmdsend, 'rout', self.PRINT)
            if (routResponse.find('Bad Channel') == -1) and \
                    (routResponse.find('Out of Range') == -1) and \
                    (routResponse.find('not found') == -1):

                self.SendCmd('nvram set wl1_channel=' + str(channel), 'rout', self.PRINT)
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Commiting Setting Changes')
                self.SendCmd('nvram commit', 'rout', self.PRINT)
                self.SendCmd(self.wlcmd + '-i eth2 up', 'rout', self.PRINT)
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router back up')
                time.sleep(3)

                self.SendCmd(self.commands['connect'], 'sol', self.PRINT)

                time.sleep(2)
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
                self.emit(SIGNAL("auxstatUpdate(QString)"), '0')
            else:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Invalid Channel')
                self.SendCmd(self.wlcmd + '-i eth2 up', 'rout', self.PRINT)
                time.sleep(3)
                res = self.SendCmd('nvram show|grep wl1_channel', 'rout', self.PRINT)
                chan = re.search('wl1_channel=(\d+)', res, re.U)
                if chan and chan.group(1):
                    self.emit(SIGNAL("chanaUpdate(QString)"), str(chan.group(1)))
        else:
            # 2.4 GHz
            ipInfo = self.SendCmd(self.commands['get_config'], 'sol', self.PRINT)
            chan = re.search('Channel:\s+(\d{1,3})', ipInfo, re.U)
            whichrout = self.SendCmd('wl_iocmd ver', 'rout', self.NOPRINT)
            ans = re.search('version', whichrout)
            if ans:
                self.wlcmd = 'wl_iocmd '
            else:
                self.wlcmd = 'wl '
            try:
                if int(channel) == int(chan.group(1)):
                    pass
                else:
                    print self.routcom + self.solcom + channel

                    self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router Down for setting changes')
                    self.SendCmd(self.wlcmd + 'down', 'rout', 1)
                    self.emit(SIGNAL("mainstatUpdate(QString)"), 'Changing Channel Settings')
                    cmdsend = self.wlcmd + 'channel ' + str(channel)
                    self.SendCmd(cmdsend, 'rout', self.PRINT)
                    self.SendCmd('nvram set channel_24g=' + str(channel), 'rout', self.PRINT)
                    self.SendCmd('nvram set wl0_channel=' + str(channel), 'rout', self.PRINT)
                    self.SendCmd('nvram set wl_channel=' + str(channel), 'rout', self.PRINT)
                    self.SendCmd('nvram set wla_channel=' + str(channel), 'rout', self.PRINT)

                    self.emit(SIGNAL("mainstatUpdate(QString)"), 'Commiting Setting Changes')

                    self.SendCmd('nvram commit', 'rout', self.PRINT)

                    self.SendCmd(self.wlcmd + 'up', 'rout', self.PRINT)
                    self.emit(SIGNAL("mainstatUpdate(QString)"), 'Router back up')
            except (ValueError, AttributeError):
                pass

        self.associate()
        time.sleep(3)
        return self.verify(60)



################################################################
####  __  __          _ _             __  __         _      ####
#### |  \/  |___ _ _ (_) |_ ___ _ _  |  \/  |___  __| |___  ####
#### | |\/| / _ \ ' \| |  _/ _ \ '_| | |\/| / _ \/ _` / -_) ####
#### |_|  |_\___/_||_|_|\__\___/_|   |_|  |_\___/\__,_\___| ####
####                                                        ####
################################################################

class MonitorNF(AutoNFBase):
    TvsNoiseXY = pyqtSignal(list)

    def __init__(self, parent=None):
        super(MonitorNF, self).__init__(parent)

    def initialize(self, solcom, routcom, lincom, commands, rundata, iperf, speed):
        super(MonitorNF, self).initialize(solcom, lincom, routcom)
        self.commands   = commands
        self.rundata    = rundata
        self.iperf      = iperf
        self.speed      = speed

    def run(self):
        self.collect()
        self.stop()
        if self.rundata:
            if self.iperf:
                self.endiperf()
            else:
                try:
                    os.remove('C:\hptcprun.bat')
                except:
                    pass
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        self.emit(SIGNAL("auxstatUpdate(QString)"), "0")
        self.emit(SIGNAL("finished(bool)"), self.completed)

    def updateSpeed(self, speed):
        self.speed = speed

    def endiperf(self):
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Iperf initializing")
        try:
            linux = serial.Serial(self.lincom, 115200, writeTimeout=None)
            linux.write('\x03' + '\r\n')  # send Ctrl-C
            linux.write('kill $(ps | grep iperf[3] | awk \'{print $1}\')' + '\r\n')
            linux.close()
        except(OSError, serial.SerialException):
            pass

    def collect(self):
        ii = 0
        PlotXY = []
        waitTime = [3, 2, 1, .5, .25, .1]
        xtime = 0
        startTime = time.time()
        # signal here to change the antenna!!!
        try:
            ser = serial.Serial(self.solcom, 115200, writeTimeout=None)

        except(OSError, serial.SerialException):
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Sirius serial port cannot be reached')
            self.stop()

        while not self.stopped:
            SNRInfo = ''
            if ser.isOpen():
                ser.write(self.commands['get_config'] + '\r\n')
                time.sleep(waitTime[self.speed - 1])
                for x in range(0, 200):
                    SNRInfo += ser.read(ser.inWaiting())
                    if 'returns' in SNRInfo:
                        break
                    time.sleep(.02)

                noise = re.search('noise:\s*(-\d+)', SNRInfo, re.U)
                if noise and noise.group(1):
                    ii += 1
                    if xtime == 0:
                        PlotXY = [xtime, float(noise.group(1))]
                        xtime = time.time()
                    else:
                        xtime = time.time() - startTime
                        PlotXY = [xtime, float(noise.group(1))]
                    print noise.group(1)
                    self.TvsNoiseXY.emit(PlotXY)
                    self.emit(SIGNAL("auxstatUpdate(QString)"), 'sample: ' + str(ii))
                    #realxtime=realxtime+toc
                else:
                    pass
            else:
                break
        ser.close()



##########################################################################################
####  __  __                    _   _____ _                      _              _     ####
#### |  \/  |__ _ _ _ _  _ __ _| | |_   _| |_  _ _ ___ _  _ __ _| |_  _ __ _  _| |_   ####
#### | |\/| / _` | ' \ || / _` | |   | | | ' \| '_/ _ \ || / _` | ' \| '_ \ || |  _|  ####
#### |_|  |_\__,_|_||_\_,_\__,_|_|   |_| |_||_|_| \___/\_,_\__, |_||_| .__/\_,_|\__|  ####
####                                                       |___/     |_|              ####
##########################################################################################

class ManualTP(AutoNFBase):
    def __init__(self, parent=None):
        super(ManualTP, self).__init__(parent)

    def initialize(self, solcom, lincom, ip, iperf, iperfverb, iperf_t, iperfbw, iperf_in, hptcpPort, hptcpIter,
                   hptcpRep):
        super(ManualTP, self).initialize(solcom, lincom, '')
        self.ipadr          = ip
        self.iperf          = iperf
        self.verbose        = iperfverb
        self.iperf_time2t   = iperf_t
        self.iperf_bw       = iperfbw
        self.iperf_interval = iperf_in
        self.hptcp_port     = hptcpPort
        self.hptcp_iter     = hptcpIter
        self.hptcp_report   = hptcpRep

    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
            if self.iperf:
                self.endiperf()
            else:
                self.TCP.stop()
        finally:
            self.mutex.unlock()

    def run(self):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Initializing')
        self.endiperf()
        time.sleep(3)
        if self.iperf:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Running Iperf')
            self.runIperf()
        else:
            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Running hpTCP')
            self.runhptcp()
            if self.TCP.isRunning():
                self.TCP.wait()

        self.stop()

        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        self.emit(SIGNAL("auxstatUpdate(QString)"), "0")
        self.emit(SIGNAL("finished(bool)"), self.completed)

    def endiperf(self):
        """ Terminates iPerf server Running on printer

        """
        try:
            linux = serial.Serial(str(self.lincom), 115200, writeTimeout=None)
            time.sleep(.1)
            linux.write('\x04' + '\r\n')  # send Ctrl-D
            time.sleep(.1)
            linux.write('\x03' + '\r\n')  # send Ctrl-C
            time.sleep(.1)
            linux.write('kill $(ps | grep iperf[3] | awk \'{print $1}\')' + '\r\n')
            time.sleep(.1)
            linux.close()
            time.sleep(.5)
        except(OSError, serial.SerialException):
            pass

    def runIperf(self):
        try:
            self.SendCmd("iperf3 -s &", 'lin', self.PRINT)
            time.sleep(4)
            # self.mainstatUpdate('Sending Command')
            iperfcmd = 'c:\iperf\iperf3.exe -c ' + str(self.ipadr)
            if self.verbose:
                iperfcmd += ' -V'
            try:
                iperfcmd += ' -t ' + str(self.iperf_time2t)
            except(ValueError):
                pass
            if bool(re.search('d+[KMG]?', self.iperf_bw)):
                iperfcmd += ' -b ' + str(self.iperf_bw)
            try:
                iperfcmd += ' -i ' + str(self.iperf_interval)
            except(ValueError):
                pass
            filename = os.getcwd() + '\\iperf.log'
            print 'iperfcmd=[' + iperfcmd + '] filename=[' + filename + ']'
            cmd = subprocess.Popen(iperfcmd + ' -f m --logfile ' + filename)  # , creationflags=CREATE_NEW_CONSOLE)
            file = open(filename, 'r')
            file.seek(0, 2)
            count = 0
            while count <= 9:
                where = file.tell()
                line = file.readline()
                if line:
                    if re.search('unable to connect to server', line):
                        cmd = subprocess.Popen(iperfcmd + ' -f m --logfile ' + filename)  # , creationflags=CREATE_NEW_CONSOLE)
                    # print line without newline
                    self.emit(SIGNAL("logUpdate(QString)"), line[:-1])
                    time.sleep(1)
                else:
                    time.sleep(.4)
                    file.seek(where)
                    count += 1
            time.sleep(.5)
        # for line in cmd.stdout:
        #    form.textBrowser.append(unicode(line))

        # self.mainstatUpdate('Idle')
        except(ValueError):
            pass

    # def runhptcp(self):
    #    """
    #        hptcp.exe way of running throughput testing
    #    """
    #    try:
    #        hptcpcmd = 'C:\hptcptest.exe /t '+ str(self.ipadr)
    #        try:
    #            hptcpcmd = hptcpcmd + ' /P ' + str(self.hptcp_port)
    #        except(ValueError):
    #            pass
    #        try:
    #            hptcpcmd = hptcpcmd + ' /N ' + str(self.hptcp_iter)
    #        except(ValueError):
    #            pass
    #        try:
    #            hptcpcmd = hptcpcmd + ' /I ' + str(self.hptcp_report)
    #        except(ValueError):
    #            pass
    #        print hptcpcmd
    #        cmd = subprocess.Popen( hptcpcmd, creationflags=CREATE_NEW_CONSOLE)
    #        #for line in cmd.stdout:
    #        #    form.textBrowser.append(unicode(line))
    #        #self.mainstatUpdate('Idle')
    #    except(ValueError):
    #        pass
    def runhptcp(self):
        try:
            # hpTCP.hpTcpTestTngCmd(['/f', 'MBIT', '/i', '1', '/e', '10', '/t', '192.168.2.2'])
            hptcpcmd = ['/f', 'MBIT']
            try:
                hptcpcmd.append('/p')
                hptcpcmd.append(str(self.hptcp_port))
            except(ValueError):
                pass
            try:
                hptcpcmd.append('/e')
                hptcpcmd.append(str(int(self.hptcp_iter)))
            except(ValueError):
                pass
            try:
                hptcpcmd.append('/i')
                hptcpcmd.append(str(self.hptcp_report))
            except(ValueError):
                pass
            hptcpcmd.append('/l')
            hptcpcmd.append('1')
            hptcpcmd.append('/t')
            hptcpcmd.append(str(self.ipadr))
            print hptcpcmd
            self.TCP = hpTCP.hpTcpTestTngCmd(hptcpcmd)
            self.connect(self.TCP, SIGNAL("logUpdate(QString)"), self.logUpdate)
            if self.TCP.isRunning():
                self.TCP.stop()
                self.TCP.wait()
            self.TCP.start()
        # for line in cmd.stdout:
        #    form.textBrowser.append(unicode(line))
        # self.mainstatUpdate('Idle')
        except(ValueError):
            pass
