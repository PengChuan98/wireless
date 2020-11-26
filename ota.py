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
import visa
import time
import glob
import subprocess
import math
import paramiko

#from collections import deque
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest
import channel_change
from numpy import *

#from devices import Attenuator, GpibDevice, JFW50PA

__version__ = "1.0.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

# ASCII string constants
Cr      = '\r'          # Carriage Return
Lf      = '\n'          # Linefeed
Tab     = '\t'          # Tab
CrLf    = '\r\n'        # Carriage Return and Linefeed
Ctrl_C  = '\x03\r\n'    # Control C
Ctrl_D  = '\x04\r\n'    # Control D

# Default SSH Parameters
ssh_max_rx_bytes= 8192
#ssh_ip          = '192.168.1.249'
ssh_port        = 22
ssh_username    = 'pi'
ssh_password    = 'raspberry'

# Command to send to printer kernel to get WiFi Direct SSID and pass phrase
# ssid_get = 'busctl get-property com.hp.NetCom /com/hp/NetCom/Device/wlan1 com.hp.NetCom.Device Settings' # linux
ssid_get = 'udws "nc_wifi.get_config wlan1"'


# Map channel frequency to channel number
#MHz     Channel
channelMap = {\
2412   :   1,\
2417   :   2,\
2422   :   3,\
2427   :   4,\
2432   :   5,\
2437   :   6,\
2442   :   7,\
2447   :   8,\
2452   :   9,\
2457   :  10,\
2462   :  11,\
2467   :  12,\
2472   :  13,\
2484   :  14,\
5180   :  36,\
5180   :  36,\
5200   :  40,\
5220   :  44,\
5240   :  48,\
5260   :  52,\
5280   :  56,\
5300   :  60,\
5340   :  64,\
5500   : 100,\
5520   : 104,\
5540   : 108,\
5560   : 112,\
5580   : 116,\
5660   : 132,\
5680   : 136,\
5700   : 140}



######################################################
####   ____ _______         __  __       _        ####
####  / __ \__   __|/\     |  \/  |     (_)       ####
#### | |  | | | |  /  \    | \  / | __ _ _ _ __   ####
#### | |  | | | | / /\ \   | |\/| |/ _` | | '_ \  ####
#### | |__| | | |/ ____ \  | |  | | (_| | | | | | ####
####  \____/  |_/_/    \_\ |_|  |_|\__,_|_|_| |_| ####
####                                              ####
######################################################

class Overtheair(QThread):

    PRINT = 1
    NOPRINT = 0
    rssiTPpoint = pyqtSignal(list)
    debug = True

    # Clean up ssh connection to Raspbery Pi when object deallocated
    def __del__(self):
        if Overtheair.debug:
            print 'Overtheair.__del__()'
        self.sshClose()


    def __init__(self, parent=None):
        super(Overtheair, self).__init__(parent)
        self.mutex      = QMutex()
        self.stopped    = False
        self.completed  = False
        self.ssh        = None
        self.shell      = None

        self.direct_ssid        = None
        self.direct_password    = None


    def initialize(self, solcom, routcom, lincom, manual_box, manual_list,
        commands, iperf, samples, fiveGHz, direct, piAddr,
        secsPerAtten=None, channel=None, antenna=None):
        self.solcom     = solcom
        self.routcom    = routcom
        self.lincom     = lincom
        self.manual     = manual_box
        self.commands   = commands
        self.iperf      = iperf
        self.samples    = samples
        self.fiveGHz    = fiveGHz
        self.wifiD      = direct
        self.ssh_ip     = piAddr
        self.secsPerAtten = secsPerAtten
        self.channel    = channel
        self.antenna    = antenna
        if self.channel:
            self.channel = str(self.channel)
        if self.antenna:
            self.antenna = str(self.antenna)
        print 'Overtheair.initialize:'\
            + ' solcom='       + str(self.solcom)\
            + ' routcom='      + str(self.routcom)\
            + ' lincom='       + str(self.lincom)\
            + ' manual='       + str(self.manual)\
            + ' iperf='        + str(self.iperf)\
            + ' samples='      + str(self.samples)\
            + ' fiveGHz='      + str(self.fiveGHz)\
            + ' wifiD='        + str(self.wifiD)\
            + ' secsPerAtten=' + str(self.secsPerAtten)\
            + ' channel='      + str(self.channel)\
            + ' antenna='      + str(self.antenna)

        self.atten = 0
        self.attenlist = []
        if self.manual:
            for item in manual_list:
                self.attenlist.append(int(item.text()))


    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True
            self.cmd.kill()
            self.emit(SIGNAL("logUpdate(QString)"), 'Attenuation stopped at: ' + str(self.atten))
            print "stopping"
        except(AttributeError):
            pass
        finally:
            self.mutex.unlock()


    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()


    def run(self):
        print 'Overtheair.run:'\
            + ' solcom='       + str(self.solcom)\
            + ' routcom='      + str(self.routcom)\
            + ' lincom='       + str(self.lincom)\
            + ' manual='       + str(self.manual)\
            + ' iperf='        + str(self.iperf)\
            + ' samples='      + str(self.samples)\
            + ' fiveGHz='      + str(self.fiveGHz)\
            + ' wifiD='        + str(self.wifiD)\
            + ' secsPerAtten=' + str(self.secsPerAtten)\
            + ' channel='      + str(self.channel)\
            + ' antenna='      + str(self.antenna)
        self.otasweep(self.samples)
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Idle')
        if not self.stopped:
            self.stop()
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Resetting Attenuator to 0")
        self.atten = 0
        self.attenControl(self.atten)
        self.endiperf()
        self.emit(SIGNAL("finished(bool)"), self.completed)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "0")


    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - destination ('sol', 'lin', or 'rout')
            :disp - optional print output to textBrowser
        """
        out = ''
        if dest is 'sol':
            ser = serial.Serial(self.solcom,115200,timeout=10,writeTimeout=10)
        elif dest is 'lin':
            ser = serial.Serial(self.lincom,115200,timeout=10,writeTimeout=10)
        elif dest is 'rout':
            try:
                ser = serial.Serial(self.routcom,115200,timeout=10,writeTimeout=10)
            except(OSError, serial.SerialException):
                print 'Serial Error in chan chg'
                return 'Error'
                pass
        else:
            return -1
        if ser and ser.isOpen():
            ser.write(ToSend + Cr + Lf)
            time.sleep(.5)
            if dest is 'sol':
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
        return out

    def endiperf(self):
        """ Terminates iPerf server Running on printer

        """
        self.emit(SIGNAL("auxstatUpdate(QString)"), 'Terminating iperf')
        try:
            linux = serial.Serial(self.lincom, 115200, writeTimeout=None)
            time.sleep(.1)
            linux.write(Ctrl_D)
            time.sleep(.1)
            linux.write(Ctrl_C)
            time.sleep(.1)
            linux.write('kill $(ps | grep iperf[3] | awk \'{print $1}\')\r\n')
            time.sleep(.1)
            linux.close()
            time.sleep(1)
        except(OSError, serial.SerialException):
            pass

    def hptcpparse(self):
        """ Takes IPaddr and uses hptcptest and parses throughput value from output
            Return Floating number
        """
        #self.emit(SIGNAL("auxstatUpdate(QString)"), "Running hpTCPtest")
        rate = None
        express=' (\d+\.\d+e\+\d+) Bytes Per Second'
        self.cmd = subprocess.Popen('C:\hptcptest.exe /t ' + self.IPaddr + ' /I 1 /N 1', stdout=subprocess.PIPE)
        exitcounter = 0
        while self.cmd.poll() is None:
            exitcounter += 1
            if exitcounter > 50:       #50 second timeout
                self.cmd.kill()
                break
            time.sleep(1)
        for line in self.cmd.stdout:
            find = re.search(express, line)
            if find:
                if find.group(1):
                    rate = (float(find.group(1)) * 8 / 1000000)
                    break
        return rate

    def iperfparse(self):
        """ Takes IPaddr and uses iperf and parses throughput value from output
            Return Floating number
        """
        #self.emit(SIGNAL("auxstatUpdate(QString)"), "Running Iperf")
        rate = None
        express = '(\d+\.\d+)\sMbits/sec\s+receiver|\s(\d+)\sMbits/sec\s+receiver'
        self.cmd = subprocess.Popen('c:\iperf\iperf3.exe -c ' + self.IPaddr + ' -i 1 -t 2 -f m', stdout=subprocess.PIPE)
        exitcounter = 0
        while self.cmd.poll() is None:
            exitcounter += 1
            if exitcounter > 50:       #50 second timeout
                self.cmd.kill()
                break
            time.sleep(1)
        try:
            for line in self.cmd.stdout:
                find = re.search(express, line)
                if find:
                    if find.group(1):
                        rate = float(find.group(1))
                        break
                    elif find.group(2):
                        rate = float(find.group(2))
                        break
        except Exception as e:
            print 'Overtheair.iperfparse: Caught exception: ' + str(e)
            traceback.print_exc()
        return rate

    def wifiDparse(self):
        rate = None
        express = '(\d+\.\d+)\sMbits/sec\s+receiver|\s(\d+)\sMbits/sec\s+receiver'
        # Run iperf client on Pi
        out = self.sshCommand('iperf3 -c 192.168.223.1 -i 1 -t 2 -f m')
        for x in range(0, 20):
            find = re.search(express, out)
            if find:
                if find.group(1):
                    rate = float(find.group(1))
                    break
                elif find.group(2):
                    rate = float(find.group(2))
                    break
            time.sleep(.1)
            out += self.sshReceive()
        return rate

    def ipaddrCheck(self):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Verify connection')
        ipValid = None
        for chk in range(5):
            self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address check #" + str(chk))
            ipInfo = self.SendCmd(self.commands['get_config'], 'sol', self.PRINT)
            m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', ipInfo, re.U)
            if m:
                if m.group(1) is not None:
                    self.IPaddr = str(m.group(1))
                if m.group(2) is not None:
                    self.IPaddr = str(m.group(2))
                self.emit(SIGNAL("auxstatUpdate(QString)"), "IP address valid")
                ipValid = ipInfo
                break
        return ipValid

    def done(self, text):
        self.stopped = True
        if self.channel:
            if self.antenna:
                text = 'Channel ' + self.channel + ' Antenna ' + self.antenna + ' ' + text
            else:
                text = 'Channel ' + self.channel + ' ' + text
        elif self.antenna:
            text = 'Antenna ' + self.antenna + ' ' + text
        print text
        self.emit(SIGNAL("logUpdate(QString)")     , text)
        self.emit(SIGNAL("mainstatUpdate(QString)"), text)
        self.emit(SIGNAL("auxstatUpdate(QString)") , '0')
        if self.ssh or self.shell:
            self.sshClose()

    def otasweep(self, samples):
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting OTA')
        self.SendCmd(self.commands['stop_log'], 'sol', self.PRINT)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Overhead logging off")
        self.SendCmd(self.commands['no_sleep'], 'sol', self.PRINT)
        self.emit(SIGNAL("auxstatUpdate(QString)"), "Sleep off")
        if self.manual:
            if self.attenlist:
                # Note: sweepVarUpdate sets attenuator level
                samples = self.sweepVarUpdate(None, samples)
            else:
                print 'No manual attenuation levels selected!'
                self.endiperf()
                return
        else:
            self.attenControl(self.atten)
        if not self.stopped:
            if self.wifiD:
                self.startDirect()
                config = self.findDirectClient(120)
                if not config:
                    self.done('WiFi Direct test failed!')
            else:
                time.sleep(3)
                config = self.ipaddrCheck()
            if config:
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Initialize attenuator')
                self.ptchange = 0
                i = -2 # Skip first two readings
                if self.iperf or self.wifiD:
                    # Restart iperf server
                    self.endiperf()
                    self.SendCmd("iperf3 -s &", 'lin', self.PRINT)
                    time.sleep(2)
                self.emit(SIGNAL("mainstatUpdate(QString)"), 'Starting Collection')
                self.emit(SIGNAL("auxstatUpdate(QString)"), 'Open ' + self.solcom + ' for communication')
                self.startTime = -1
                self.nextTime  = -1
                while not self.stopped:
                    rateErrors = 0
                    rssiErrors = 0
                    ratearray = []
                    while (i < int(samples) or self.secsPerAtten) and not self.stopped:
                        out = ''
                        rssi = None
                        if i > -1: # Skip first reading
                            if self.secsPerAtten:
                                self.emit(SIGNAL("auxstatUpdate(QString)"), 'Sample Num: ' + str(i + 1))
                            else:
                                self.emit(SIGNAL("auxstatUpdate(QString)"), 'Sample Num: ' + str(i + 1) + '/' + str(samples))

                        if self.secsPerAtten:
                            print 'Sending rate request\t' + str(i + 1) + ' to ' + str(self.IPaddr)
                        else:
                            print 'Sending rate request\t' + str(i + 1) + '/' + str(samples) + ' to ' + str(self.IPaddr)
                        if self.wifiD:
                            # Run iperf client on Pi
                            rate = self.wifiDparse()
                            if rate:
                                # Try to get RSSI from printer.
                                if self.commands['get_sta_rssi'][0:4] != 'udws':
                                    lin = serial.Serial(self.lincom, 115200, timeout=10, writeTimeout=10)
                                    lin.write(self.commands['get_sta_rssi'] + CrLf)
                                    time.sleep(.1)
                                    for x in range(0, 200):
                                        out += lin.read(lin.inWaiting())
                                        list = re.findall('\s+(-*\d+)', out, re.U)
                                        if list and len(list) > 2:
                                            rssi = int(list[2]) # RSSI info data last
                                            break
                                        time.sleep(.01)
                                    try:
                                        lin.close()
                                    except:
                                        pass
                                    print 'Overtheair.otasweep: response:\n' + out # TBD
                                    if not rssi:
                                        # Try to get RSSI from Pi
                                        out = self.sshCommand('mlanutl wlan0 getsignal')
                                        for x in range(0, 200):
                                            list = re.findall('\s+(-*\d+)', out, re.U)
                                            if list and len(list) > 2:
                                                rssi = int(list[2]) # RSSI info data last
                                                break
                                            time.sleep(.01)
                                            out += self.sshReceive()
                                else:
                                    sol = serial.Serial(self.solcom, 115200, timeout=10, writeTimeout=10)
                                    sol.write(self.commands['get_sta_rssi'] + CrLf)
                                    time.sleep(.1)
                                    for x in range(0, 200):
                                        out += sol.read(sol.inWaiting())
                                        if 'returns' in out:
                                            break
                                        time.sleep(.01)
                                    try:
                                        sol.close()
                                    except:
                                        pass
                                    rssi = re.search('"rssi"\s*:\s*(-\d+)', out, re.U)
                                    if rssi and rssi.group(1):
                                        rssi = int(rssi.group(1))
                                    else:
                                        rssi = None
                        else:
                            if self.iperf:
                                rate = self.iperfparse()
                            else:
                                rate = self.hptcpparse()
                            if rate:
                                sol = serial.Serial(self.solcom, 115200, timeout=10, writeTimeout=10)
                                sol.write(self.commands['get_config'] + CrLf)
                                time.sleep(.1)
                                for x in range(0, 200):
                                    out += sol.read(sol.inWaiting())
                                    if 'returns' in out:
                                        break
                                    time.sleep(.01)
                                #Find RSSI
                                rssi = re.search('signalStrength:\s*(-\d+)', out, re.U)
                                if rssi is None:      #backup command to get rssi
                                    time.sleep(.1)
                                    sol.write(self.commands['get_rssi'] + CrLf)
                                    time.sleep(.1)
                                    for x in range(0, 200):
                                        out += sol.read(sol.inWaiting())
                                        if 'returns' in out:
                                            break
                                    time.sleep(.01)
                                    #Find RSSI
                                    rssi = re.search('(-\d{2})', out, re.U)
                                try:
                                    sol.close()
                                except:
                                    pass
                                if rssi and rssi.group(1):
                                    rssi = int(rssi.group(1))
                                else:
                                    rssi = None

                        if rate is None:
                            rateErrors = rateErrors + 1
                        elif i >= 0 and not self.secsPerAtten:
                            ratearray.append(rate)
                        if rate and rssi:
                            i += 1
                            if i > 0: # Skip first reading
                                # rssi, atten = int
                                # rate, time = float
                                if self.secsPerAtten:
                                    now = time.clock()
                                    if self.startTime < 0:
                                        self.startTime = now
                                        self.nextTime = now + self.secsPerAtten
                                    PlotPoint = [rssi, rate, self.atten, now - self.startTime]
                                else:
                                    PlotPoint = [rssi, rate, self.atten]
                                self.rssiTPpoint.emit(PlotPoint)
                                self.emit(SIGNAL("RSSIupdate(QString)"), str(rssi))
                                self.emit(SIGNAL("TPupdate(QString)"), str(rate))
                                self.emit(SIGNAL("Attenlist(QString)" ), str(self.atten))
                                if self.secsPerAtten:
                                    s = str(PlotPoint[0])+Tab+str(PlotPoint[1])+Tab+str(PlotPoint[2])+Tab+str(i)+Tab+str(PlotPoint[3])
                                else:
                                    s = str(self.atten)+Tab+str(rssi)+Tab+str(rate)+Tab+str(i)+'/'+str(samples)
                                    if not self.manual:
                                        s += Tab+'pt:'+str(self.ptchange)
                                print s
                        else:
                            rssiErrors = rssiErrors + 1
                        if rateErrors > 6:
                            self.stopped = True
                            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Throughput not available!')
                            self.emit(SIGNAL("auxstatUpdate(QString)"), "Check cable connection")
                            self.emit(SIGNAL("logUpdate(QString)"), 'Attenuation stopped at: ' + str(self.atten))
                            self.emit(SIGNAL("logUpdate(QString)"), 'Throughput cannot connect anymore')
                            break
                        if (rateErrors > 4 or rssiErrors > 4) and self.ptchange == 2:
                            self.done('Sweep succeeded')
                            break
                        if rssiErrors > 5 and self.ptchange != 2:
                            self.stopped = True
                            self.emit(SIGNAL("mainstatUpdate(QString)"), 'Cannot communicate with printer!')
                            self.emit(SIGNAL("auxstatUpdate(QString)"), "0")
                            break
                        if self.secsPerAtten and not self.stopped and self.nextTime >= 0:
                            if not rate:
                                self.stopped = True
                                break;
                            if self.manual and not self.attenlist:
                                break
                            now = time.clock()
                            if self.nextTime <= now:
                                # Set next attenuator value
                                self.sweepVarUpdate(None, samples)
                                i = 0
                                self.nextTime += self.secsPerAtten
                    if len(ratearray) > 0:
                        sum = 0
                        for r in ratearray:
                            sum += r
                        print 'average=' + str(round(sum / len(ratearray), 2))
                    else:
                        self.done('Sweep succeeded')
                        break
                    if self.manual and not self.attenlist:
                        self.done('Manual Sweep succeeded')
                        break
                    if not self.stopped:
                        samples = self.sweepVarUpdate(median(ratearray), samples)
                        i = 0

    def sweepVarUpdate(self, rate, samples):
        """sweepVarUpdate: takes in the previous point information to determine after a round of sampling, initially specified by the user,
        to whether increase attenuation by what amount and/or decrease amount of samples for better graphing experience.
        """
        newsamp = samples
        if self.manual:
            self.atten = self.attenlist.pop(0)
        elif self.fiveGHz:
            # 5 GHz
            if rate > 40:
                self.atten += 3
            elif rate > 15:
                if self.ptchange == 0:
                    self.ptchange = 1
                    newsamp = int(ceil(int(samples)*.7))
                self.atten += 2
            else:
                if self.ptchange == 1:
                    self.ptchange = 2
                    newsamp = int(ceil(int(samples)*.7))
                self.atten += 1
        else:
            # 2.4 GHz
            if rate > 20:
                self.atten += 5
            elif rate > 15:
                self.atten += 3
            elif rate > 8:
                if self.ptchange == 0:
                    self.ptchange = 1
                    newsamp = int(ceil(int(samples)*.7))
                self.atten += 2
            else:
                if self.ptchange == 1:
                    self.ptchange = 2
                    newsamp = int(ceil(int(samples)/2)+1)
                self.atten += 1
        self.attenControl(self.atten)
        return newsamp

    def attenControl(self, attnint):
        #print 'Overtheair.attenControl(' + str(attnint) + ')' # TBD
        val = int(attnint)
        if val > 79:
            val = 79
        elif val < 0:
            val = 0
        self.emit(SIGNAL("AttenUpdate(QString)"), str(val))
        self.emit(SIGNAL("mainstatUpdate(QString)"), 'Attenuator at ' + str(val))
        time.sleep(1) # TBD - How long should it take attenuator to change level?


################################################################################
#
# WiFi Direct test support
#
################################################################################

    # Close ssh connection to Raspberry Pi
    def sshClose(self):
        if Overtheair.debug:
            print 'Overtheair.sshClose()'
        if self.shell:
            try:
                self.shell.close()
                del self.shell
            except:
                pass
            finally:
                self.shell = None
        if self.ssh:
            try:
                self.ssh.close()
                del self.ssh
            except:
                pass
            finally:
                self.ssh = None


    # Open ssh connection to Raspberry Pi
    def sshOpen(self, ip_address, port, username, password):
        if self.shell and self.shell.closed:
            self.sshClose()
        if not (self.ssh and self.shell):
            if self.ssh or self.shell:
                self.sshClose()
            try:
                self.ssh = paramiko.SSHClient()
                if self.ssh:
                    self.ssh.load_system_host_keys()
                    self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self.ssh.connect(ip_address, port=port, username=username, password=password)
                    self.shell = self.ssh.invoke_shell()
                    if self.shell:
                        self.shell.settimeout(1)
                        if Overtheair.debug:
                            print 'Overtheair.sshOpen(' + ip_address + ',' + str(port) + ',' + username + ',' + password + ') succeeded'
                        self.sshCommand('')
                    else:
                        if Overtheair.debug:
                            print 'Overtheair.sshOpen(' + ip_address + ',' + str(port) + ',' + username + ',' + password + ') invoke_shell failed'
                else:
                    print 'Overtheair.sshOpen(' + ip_address + ',' + str(port) + ',' + username + ',' + password + ') SSHClient failed'
            except Exception as e:
                print 'Overtheair.sshOpen(' + ip_address + ',' + str(port) + ',' + username + ',' + password + ') Caught exception: ' + str(e)
                traceback.print_exc()
                self.sshClose()
        return self.shell


    # Receive response over ssh from Raspberry Pi
    def sshReceive(self):
        response = ''
        if self.shell and not self.shell.closed:
            try:
                # TBD: how do we know when response is complete?
                while self.shell.recv_ready():
                    data = self.shell.recv(ssh_max_rx_bytes)
                    if data:
                        response = response + data
                    time.sleep(0.1)
            except Exception as e:
                print 'Overtheair.sshReceive(' + text + ') recv exception: ' + str(e.__class__) + ': ' + str(e)
                traceback.print_exc()
                self.sshClose()
        else:
            print 'Overtheair.sshReceive(' + text + ') shell not open'
        if Overtheair.debug and response:
            print 'Overtheair.sshReceive: response=[' + response + ']' # TBD
        return response


    # Send command over ssh to Raspberry Pi and return response
    def sshCommand(self, text):
        response = ''
        if self.shell and not self.shell.closed:
            if Overtheair.debug:
                print 'Overtheair.sshCommand(' + text + ')'

            # Flush receive buffer
            if self.shell and not self.shell.closed:
                try:
                    while self.shell.recv_ready():
                        data = self.shell.recv(ssh_max_rx_bytes)
                        print 'Flushing[' + data + ']' # TBD
                except Exception as e:
                    print 'Overtheair.sshCommand(' + text + ') flush exception: ' + str(e.__class__) + ': ' + str(e)
                    traceback.print_exc()
                    self.sshClose()

            # Send command
            cmd = text + Cr
            if self.shell and not self.shell.closed:
                try:
                    self.shell.send(cmd)
                except Exception as e:
                    print 'Overtheair.sshCommand(' + text + ') send exception: ' + str(e.__class__) + ': ' + str(e)
                    traceback.print_exc()
                    self.sshClose()

            # Wait for response
            time.sleep(1) # TBD

            # Receive response
            cmd = text + Cr + Lf
            if self.shell and not self.shell.closed:
                try:
                    # TBD: how do we know when response is complete?
                    while self.shell.recv_ready():
                        data = self.shell.recv(ssh_max_rx_bytes)
                        if data:
                            response = response + data
                        time.sleep(0.1)
                    if cmd in response:
                        response = response.replace(cmd, '', 1)
                    if Overtheair.debug:
                        print 'Overtheair.sshCommand: response:\n' + response # TBD
                except Exception as e:
                    print 'Overtheair.sshCommand(' + text + ') recv exception: ' + str(e.__class__) + ': ' + str(e)
                    traceback.print_exc()
                    self.sshClose()
        else:
            print 'Overtheair.sshCommand(' + text + ') shell not open'
        return response


    def findDirectClient(self, timeout):
        self.IPaddr = None
        if Overtheair.debug:
            print 'Overtheair.findDirectClient(' + str(timeout) + ')'
        if self.sshOpen(self.ssh_ip, ssh_port, ssh_username, ssh_password):
            self.IPaddr = self.waitForDirectIp(120)
        return self.IPaddr


    def waitForDirectIp(self, timeout):
        IPaddr = None
        count = 0
        t = time.clock()
        while True:
            if (count % (timeout / 2)) == 0:
                # Reconnect client to printer WiFi direct AP
                self.sshCommand('sudo wpa_cli -i wlan0 reconfigure')
                self.sshCommand('sudo wpa_cli -i wlan0 reassociate')

            print 'Overtheair.waitForDirectIp(' + str(timeout) + ') ' + str(count)
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'IP Wait ' + str(count))
            response = self.sshCommand('ifconfig wlan0')
            m = re.search('inet addr:(\d+\.\d+\.\d+\.\d+)', response, re.U)
            if m and m.group(1):
                IPaddr = str(m.group(1))
                if '192.168' in IPaddr:
                    self.IPaddr = IPaddr
                    self.emit(SIGNAL("auxstatUpdate(QString)"), 'WiFi Direct client=' + self.IPaddr)
                    break
            count += 1
            if count >= timeout:
                self.emit(SIGNAL("auxstatUpdate(QString)"), 'WiFi Direct client not found!')
                break
            t += 1
            now = time.clock()
            if t > now:
                time.sleep(t - now)
        if self.channel and IPaddr:
            # Final check for correct channel
            response = self.sshCommand('iwconfig wlan0')
            m = re.search('Frequency=(\d+\.\d+) GHz', response, re.U)
            channel = 'UNKNOWN'
            if m and m.group(1):
                ch = None
                try:
                    ghz = float(m.group(1))
                    mhz = int(ghz * 1000)
                    ch = channelMap[mhz]
                except:
                    pass
                if ch:
                    channel = str(ch)
                print 'waitForDirectIp: Channel=' + channel + ' (' + m.group(1) + ' GHz)'
            if self.channel != channel:
                print 'waitForDirectIp: Channel=' + channel + ' != ' + self.channel
                IPaddr = None
        return IPaddr


    # Parse SSID from ssid_get response
    def parseSsid(self, response):
        ssid = ''
        list = None
        try:
            i = response.index('"ssid"')
            j = response.index('[', i)
            k = response.index(']', j)
            s = response[j+1:k]
            s = s.replace(' ', '')
            #print 'parseSsid: [' + s + ']' # TBD
            list = s.split(',')
        except Exception as e:
            print 'Overtheair.parseSsid(' + response + ') exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
        if list:
            for i in range(len(list)):
                try:
                    ssid += chr(int(list[i]))
                except Exception as e:
                    print 'Overtheair.parseSsid(' + response + ') exception: ' + str(e.__class__) + ': ' + str(e)
                    traceback.print_exc()
        print 'parseSsid: ssid=[' + ssid + ']'
        return ssid


    # Parse psk from ssid_get response
    def parsePsk(self, response):
        psk = ''
        try:
            i = response.index('"psk"')
            j = response.index(':', i)
            x = response.index('"', j)
            y = response.index('"', x + 1)
            psk = response[x+1:y]
        except Exception as e:
            print 'Overtheair.parsePsk(' + response + ') exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
        print 'parsePsk: psk=[' +psk + ']'
        return psk


    #sol -> udws "nc_wifi.get_config wlan1"
    #{
    #    "type" : 3,
    #    "config" :
    #    {
    #        "dot_11_ap_config" :
    #        {
    #            "ssid" : [ 68, 73, 82, 69, 67, 84, 45, 69, 66, 45, 72, 80, 32, 69, 78, 86, 89, 32, 55, 49, 48, 48, 32, 115, 101, 114, 105, 101, 115 ],
    #            "ssid_length" : 29,
    #            "psk" : "59457592",
    #            "channel" : 6,
    #            "wfd_config_mode" : 1,
    #            "regulatory_domain" : 1,
    #            "broadcast_ssid" : 1
    #        }
    #   },
    #    "power" :
    #    {
    #       "regulatory_ok" : 1,
    #        "power_when_enabled" : 1,
    #        "enabled" : 1
    #    }
    # Get WiFi Direct SSID and password from printer
    def getDirectAuth(self):
        response = self.SendCmd(ssid_get, 'sol', self.PRINT)
        if response:
            ssid     = self.parseSsid(response)
            password = self.parsePsk(response)
            if ssid and password:
                self.direct_ssid     = ssid
                self.direct_password = password
                return True
        return False


    # Get list of WiFi Direct channels from printer
    def getDirectChannelList(self):
        response = self.SendCmd('wl channels', 'lin', self.PRINT)
        #if Overtheair.debug:
        #    print 'getDirectChannelList: response="' + str(response) + '"'
        if response:
            # Create list discarding non-integers
            list = response.split()
            response = []
            for ch in list:
                try:
                    i = int(ch)
                    response.append(str(i))
                except:
                    pass
            if Overtheair.debug:
                print 'getDirectChannelList: ' + str(response)
            return response
        else:
            return None


    # Get current WiFi Direct channel on printer
    def getDirectChannel(self):
        response = self.SendCmd('wl channel', 'lin', self.PRINT)
        if 'No scan in progress' in response:
            chan1 = re.search('current mac channel\s*(\d{1,3})', response, re.U)
            chan2 = re.search('target channel\s*(\d{1,3})', response, re.U)
            if chan1 and chan2 and chan1.group(1) and chan2.group(1):
                chan1 = str(chan1.group(1))
                chan2 = str(chan2.group(1))
                if chan1 == chan2:
                    return chan1;
        return None


    # Set WiFi Direct channel on printer
    def setDirectChannel(self, channel, timeout):
        count = 0
        t = time.clock()
        while True:
            if (count % (timeout / 4)) == 0:
                response = self.SendCmd('wl down'              , 'lin', self.PRINT)
                time.sleep(1)
                response = self.SendCmd('wl channel ' + channel, 'lin', self.PRINT)
                time.sleep(1)
                response = self.SendCmd('wl up'                , 'lin', self.PRINT)
                time.sleep(1)
                t += 3
            print 'setDirectChannel(' + channel + ',' + str(timeout) + ') ' + str(count)
            self.emit(SIGNAL("auxstatUpdate(QString)"), 'Set Direct ' + channel + ' ' + str(count))
            ch = self.getDirectChannel()
            if ch == channel:
                return channel
            count += 1
            if count >= timeout:
                print 'setDirectChannel(' + channel + ',' + str(timeout) + ') failed!'
                self.emit(SIGNAL("auxstatUpdate(QString)"), 'Direct ' + channel + ' not set!')
                return None;
            t += 1
            now = time.clock()
            if t > now:
                time.sleep(t - now)


    # Start iperf server on Raspberry Pi
    def startDirect(self):
        if self.getDirectAuth():
            if Overtheair.debug:
                print 'Overtheair.startDirect: ssid="' + self.direct_ssid + '" password="' + self.direct_password + '"'
            if self.sshOpen(self.ssh_ip, ssh_port, ssh_username, ssh_password):
                # Modify /tmp/wpa_supplicant/wpa_supplicant and reconnect
                response = self.sshCommand('sudo cat /etc/wpa_supplicant/wpa_supplicant.conf')
                if not (self.direct_ssid in response and self.direct_password in response):
                    self.sshCommand("echo 'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev' > /tmp/wpa_supplicant.conf")
                    self.sshCommand("echo 'network={'                            >> /tmp/wpa_supplicant.conf")
                    self.sshCommand("echo 'ssid=\"" + self.direct_ssid + "\"'    >> /tmp/wpa_supplicant.conf")
                    self.sshCommand("echo 'psk=\"" + self.direct_password + "\"' >> /tmp/wpa_supplicant.conf")
                    self.sshCommand("echo '}'                                    >> /tmp/wpa_supplicant.conf")
                    self.sshCommand('sudo cp /tmp/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf')
