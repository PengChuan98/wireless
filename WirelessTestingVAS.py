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
#
###################################################################################
#                   ____      _     _
#                    L|able  (()f  ((ontents
#
#   Wireless Testing Class:                       Line Numbers
#  1. init                                        116 - 226
#  2. Printer Control Btns Click Definitions      229 - 355
#  3. UI update and Send Command                  356 - 451
#  4. Printer Communication Widget Definitions    452 - 553
#  5. Attenuator Control                          557 - 790
#  6. Router Control Widget Definitions           795 - 1106
#  7. STATUS UPDATES Definitions                  1110 - 1185
#  8. Power Strip Control Widget Definitions      1190 - 1229
#  9. Throughput control IPERF and HPTCP tabs     1234 - 1343
# 10. AutoNF Tab Main GUI definitions             1349 - 1508
# 11. OTA Tab Main GUI definitions                1512 - 1896
# 12. Timing Tab Main GUI definitions             1901 - 1968
# 13. Antenna Tab Main GUI definitions            1973 - 2073
#
#   Graphing Class and Thread interface
#  1. GraphWToolbar                               2793 - 2826
#  2. AutoNFGraph                                 2839 - 3090
#  3. OTAGraph                                    3186 - 3557
#  4. NFmonitorGraph                              3571 - 3668
#


import os
import platform
import sys
import re
import serial
import serial.tools.list_ports
import visa
import time
import datetime
import glob
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import GUIWiFiTest
import subprocess
from socket import timeout, error
import json
import tempfile
import ntpath
import exceptions
import traceback

import channel_change
import autoNF
import ota
import hpTCP
import timing
import AntPattern
import threadwatcher as cc
from devices import Attenuator, GpibDevice, JFW50PA, apcpdu
import AP
from AccessPoints import AccessPoint

# Matplotlib imports
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.offsetbox import TextArea, AnnotationBbox
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from matplotlib.backends.backend_qt4agg \
    import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg \
    import NavigationToolbar2QT as NavigationToolbar
import numpy as np
import pandas as pd

import importlib
import external
import time

__version__ = "1.2.0"

MAC = True
try:
    from PyQt4.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False

data = {}  # Saketh savedata
Odata = {}
SSS_data={}

# PrinterType constants
PrinterTypeSoC = 0
PrinterTypeSoL = 1
PrinterTypeStyx = 2
PrinterTypeStingray = 3
PrinterTypePi = 4

# Plot marker iterators
coloriter = ['red', 'green', 'blue', 'magenta', 'cyan', 'yellow', 'brown']
shapeiter = ['o', '^', 'v', 's', 'p', 'h', '*']

# udws commands (defaults are for SoL)
udws_commands = { \
    'associate': 'udws "nc_wifi.associate"', \
    'connect': 'udws "nca.set_dot11_cfg wlan0 eeac6800_24g"', \
    'get_config': 'udws "nca.get_wireless_config"', \
    'no_sleep': 'udws "ds2.set 65990 100000"', \
    'stop_log': 'udws "lib_hw.stop_el"', \
    'get_version': 'udws "udw.get_verbose_fw_rev"', \
    'reset': 'udws "nca.reset_adaptors"', \
    'get_rssi': 'udws "nc_wifi.broadcom.get_rssi"', \
    'get_sta_rssi': 'udws "nc_wifi.broadcom.get_connected_sta_rssi"', \
    'antenna_1': 'udws "nc_wifi.broadcom.set_antdiv 0"', \
    'antenna_2': 'udws "nc_wifi.broadcom.set_antdiv 1"', \
    'antenna_all': 'udws "nc_wifi.broadcom.set_antdiv 3"', \
    'get_serial': 'udws "ds2.get_rec_array_str_by_name DSID_SERIAL_NUMBER"', \
    'defaults': 'udws "nca.restore_network_defaults"', \
    'quiet': 'udws "health_check.devchat_off"'
}


class WirelessTesting(QMainWindow, GUIWiFiTest.Ui_WirelessTesting):
    PRINT = 1
    NOPRINT = 0

    FiveGHzRouters = ['rtac68u', 'r7000', 'f9k1102v1', 'rtn66u', 'ea6300', 'sbg6580', 'rtac87u']
    TwofourOnlyRouters = ['tlwr841v72', 'tlwr841nv11', 'wnr2000v2', 'wnr3500v1', 'e1200v2']

    # Note toString() returns QString, not python str!
    def getString(self, name):
        val = self.settings.value(name).toString()
        if val:
            return str(val)
        else:
            return ''

    def getList(self, name):
        val = self.getString(name)
        if val:
            return val.split(',')
        else:
            return []

    def setList(self, name, list):
        val = ''
        if list is None:
            return
        for item in list:
            if len(val) == 0:
                val = item
            else:
                val += ',' + item
        self.settings.setValue(name, val)

    # Caveat: "if val" is False if val==0, so use "if val is not None" instead!
    def getInt(self, name):
        val = self.getString(name)
        if val:
            return int(val)
        else:
            return None

    def restore(self):
        self.settings.beginGroup('MainWindow')
        # print 'restore size=' + str(self.settings.value('size').toSize()) + ' pos=' + str(self.settings.value('pos' ).toPoint())
        val = self.settings.value('windowState').toByteArray()
        if val:
            self.restoreState(val)
        val = self.settings.value('size').toSize()
        if val:
            self.resize(val)
        val = self.settings.value('pos').toPoint()
        if val:
            self.move(val)
        val = self.getInt('attenuator')
        if val is not None:
            self.AttenSelCombo.setCurrentIndex(val)
            self.on_AttenSelCombo_activated()
        val = self.settings.value('attenPresent').toBool()
        if self.AttenPresentCheckbox.isChecked() != val:
            self.AttenPresentCheckbox.setChecked(val)
        val = self.settings.value('direct').toBool()
        if self.WifiDirectCheckbox.isChecked() != val:
            self.WifiDirectCheckbox.setChecked(val)
        val = self.getInt('printerType')
        if val is not None:
            self.PrinterTypeCombo.setCurrentIndex(val)
            self.on_PrinterTypeCombo_currentIndexChanged()
        val = self.settings.value('iperf').toBool()
        if self.Iperf3checkBox.isChecked() != val:
            self.Iperf3checkBox.setChecked(val)
        val = self.settings.value('tcpip').toBool()

        # TODO: Make this control and other controls unavailable
        self.RouterSelTCPIPCheck.setEnabled(False)
        self.ChWidthCombo.setEnabled(False)
        self.ModeCombo.setEnabled(False)
        self.RouterSelCombo.setEnabled(False)
        self.RouterTypeCombo.setEnabled(False)
        self.SecuritySelCombo.setEnabled(False)
        self.NF_StartBtn.setEnabled(False)  # TBD - why wait for SSID to change?
        self.NF_PrnChans.setEnabled(False)  # TBD - why wait for SSID to change?
        self.RouterSelTCPIPCheck.setChecked(False)
        self.radio5GHz.setEnabled(False)
        self.radio2_4GHz.setEnabled(False)

        self.OTA_24SelList.clear()
        self.OTA_5SelList.clear()

        self.OTA_24SelList.setEnabled(False)
        self.OTA_5SelList.setEnabled(False)

        if self.RouterSelTCPIPCheck.isChecked() != val:
            self.RouterSelTCPIPCheck.setChecked(val)
            # self.on_RouterSelTCPIPCheck_clicked()
        val = self.getInt('router')
        if val is not None:
            self.RouterTypeCombo.setCurrentIndex(0)
        val = self.getString('bandwidth')
        if val:
            self.updateChannelWidths(None, val)
        val = self.getString('mode')
        if val:
            self.updateModes(None, val)
        val = self.settings.value('5GHz').toBool()
        if self.radio5GHz.isChecked() != val:
            if val:
                self.radio5GHz.click()
            else:
                self.radio2_4GHz.click()
        val = self.settings.value('connect').toString()
        if val:
            self.ConnCmd.setText(val)
            udws_commands['connect'] = str(val)
        val = self.settings.value('get_config').toString()
        if val:
            self.WifiConfCmd.setText(val)
            udws_commands['get_config'] = str(val)
        val = self.settings.value('no_sleep').toString()
        if val:
            self.NoSleepCmd.setText(val)
            udws_commands['no_sleep'] = str(val)
        val = self.settings.value('stop_log').toString()
        if val:
            self.OHCmd.setText(val)
            udws_commands['stop_log'] = str(val)
        val = self.settings.value('get_version').toString()
        if val:
            self.FWCheckCmd.setText(val)
            udws_commands['get_version'] = str(val)
        val = self.settings.value('reset').toString()
        if val:
            self.ResetWifiCmd.setText(val)
            udws_commands['reset'] = str(val)
        val = self.settings.value('userSend').toString()
        if val:
            self.UserSendCmd.setText(val)

        # OTA tab
        val = self.settings.value('points').toString()
        if val:
            self.OTA_PtsText.setText(val)
        val = self.settings.value('group_pts').toBool()
        if self.OTA_AttenGrouping.isChecked() != val:
            self.OTA_AttenGrouping.setChecked(val)
        self.setSelectedOtaChannels(self.getList('achannels'), '5')
        self.setSelectedOtaChannels(self.getList('bchannels'), '2.4')
        self.setSelectedOtaAntennas(self.getList('antennas'))

        self.settings.endGroup()

    def save(self):
        # print 'save   size=' + str(self.size()) + ' pos=' + str(self.pos())
        self.settings.beginGroup('MainWindow')
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        self.settings.setValue('attenuator', self.AttenSelCombo.currentIndex())
        self.settings.setValue('attenPresent', self.AttenPresentCheckbox.isChecked())
        self.settings.setValue('direct', self.WifiDirectCheckbox.isChecked())
        self.settings.setValue('printerType', str(self.PrinterTypeCombo.currentIndex()))
        self.settings.setValue('iperf', self.Iperf3checkBox.isChecked())
        self.settings.setValue('tcpip', self.RouterSelTCPIPCheck.isChecked())
        self.settings.setValue('router', self.RouterTypeCombo.currentIndex())
        self.settings.setValue('bandwidth', self.ChWidthCombo.currentText())
        self.settings.setValue('mode', self.ModeCombo.currentText())
        self.settings.setValue('5GHz', self.radio5GHz.isChecked())
        self.settings.setValue('connect', self.ConnCmd.text())
        self.settings.setValue('get_config', self.WifiConfCmd.text())
        self.settings.setValue('no_sleep', self.NoSleepCmd.text())
        self.settings.setValue('stop_log', self.OHCmd.text())
        self.settings.setValue('get_version', self.FWCheckCmd.text())
        self.settings.setValue('reset', self.ResetWifiCmd.text())
        self.settings.setValue('userSend', self.UserSendCmd.text())

        # OTA tab
        self.settings.setValue('points', self.OTA_PtsText.text())
        self.settings.setValue('group_pts', self.OTA_AttenGrouping.isChecked())
        self.setList('achannels', self.getSelectedOtaChannels('5'))
        self.setList('bchannels', self.getSelectedOtaChannels('2.4'))
        self.setList('antennas', self.getSelectedOtaAntennas())

        self.settings.endGroup()

    def closeEvent(self, event):
        self.save()
        super(WirelessTesting, self).closeEvent(event)

    def __init__(self, parent=None):
        super(WirelessTesting, self).__init__(parent)
        # TODO: Modify the temporary variables
        self.__RouterTypeCombo = ""
        self.__SecuritySelCombo = ""

        self.__index = 0
        self.dispRouterDone = False
        self.attenuator = None
        self.ssid = None
        self.security = None
        self.mode = None
        self.channel = None
        self.channel_width = None
        self.supported_securities = None
        self.supported_modes = None
        self.supported_channels = None
        self.supported_channel_widths = None
        self.direct_channels = None
        self.setupUi(self)
        self.NF_StartBtn.setEnabled(False)
        self.NF_StartBtn.setToolTip('To enable button, Select Router COM port')
        self.NF_PrnChans.setToolTip('Select Router Type/COM#')
        validator = QtGui.QIntValidator(0, 600)
        self.OTA_SecsPerAtten.setValidator(validator)
        self.OTA_Start.setToolTip('To enable button, Attenuator Must be Present')
        self.time_StartBtn.setToolTip(
            'To enable button, APC IP must be set\n and correct outlet corresponding to printer')
        self.WifiDirectCheckbox.setToolTip('OTA only: need android tablet with iperf')
        self.initPrevSettings()
        self.settings = QSettings('HP', 'tanc')
        self.restore()

        self.AttenInit()
        self.getAttenLvl()
        self.serial_ports()
        self.updateUi()
        self.lock = QReadWriteLock()
        mpl.rcParams['savefig.dpi'] = 600
        self.channelch24 = channel_change.ChannelChangebg(self.lock, self)
        self.channelch5 = channel_change.ChannelChangea(self.lock, self)
        self.ota = ota.Overtheair(self)
        # Start up hardcode selecting router COM 7
        ##self.RouterSelCombo.setCurrentIndex(6)
        ##self.on_RouterSelCombo_activated()
        # Hardcode set to COM 7 End
        # Start using 1st router in list
        # self.RouterSelTCPIPCheck.click()
        # End
        self.mantp = autoNF.ManualTP(self)
        self.timing = timing.Timing(self)
        self.apattern = AntPattern.AntPattern(self)
        self.clip = QtGui.QApplication.clipboard()
        self.tpVertBar = self.OTA_TPList.verticalScrollBar()
        self.rssiVertBar = self.OTA_RSSIList.verticalScrollBar()
        self.attenDispVertBar = self.OTA_AttenlvlDisp.verticalScrollBar()

        ## channel_changebg connect declarations ##
        self.connect(self.channelch24, SIGNAL("mainstatUpdate(QString)"),
                     self.mainstatUpdate)
        self.connect(self.channelch24, SIGNAL("auxstatUpdate(QString)"),
                     self.auxstatUpdate)
        self.connect(self.channelch24, SIGNAL("IPUpdate(QString)"),
                     self.IPUpdate)
        self.connect(self.channelch24, SIGNAL("chanbgUpdate(QString)"),
                     self.chanbgUpdate)
        self.connect(self.channelch24, SIGNAL("finished(bool)"),
                     self.finished)
        self.connect(self.channelch24, SIGNAL("logUpdate(QString)"),
                     self.logUpdate)
        ########################################################################
        ########################################################################
        ## channel_changea connect declarations ##
        self.connect(self.channelch5, SIGNAL("mainstatUpdate(QString)"),
                     self.mainstatUpdate)
        self.connect(self.channelch5, SIGNAL("auxstatUpdate(QString)"),
                     self.auxstatUpdate)
        self.connect(self.channelch5, SIGNAL("IPUpdate(QString)"),
                     self.IPUpdate)
        self.connect(self.channelch5, SIGNAL("chanaUpdate(QString)"),
                     self.chanaUpdate)
        self.connect(self.channelch5, SIGNAL("finished(bool)"),
                     self.finished)
        self.connect(self.channelch5, SIGNAL("logUpdate(QString)"),
                     self.logUpdate)
        ########################################################################
        ########################################################################
        ## ota connect declarations ##

        # QObject.connect(self.tpVertBar, SIGNAL(QAbstractSlider.valueChanged(int)), self.rssiVertBar, SLOT(QAbstractSlider.setValue(int)));
        # QObject.connect(self.rssiVertBar, SIGNAL(QAbstractSlider.valueChanged(int)), self.tpVertBar, SLOT(QAbstractSlider.setValue(int)));

        QObject.connect(self.tpVertBar, SIGNAL("actionTriggered(int)"),
                        self.RSSISyncScroll)
        QObject.connect(self.rssiVertBar, SIGNAL("actionTriggered(int)"),
                        self.TPSyncScroll)
        QObject.connect(self.attenDispVertBar, SIGNAL("actionTriggered(int)"),
                        self.AttenSyncScroll)
        QObject.connect(self.tpVertBar, SIGNAL("valueChanged(int)"),
                        self.RSSISyncScroll)
        QObject.connect(self.rssiVertBar, SIGNAL("valueChanged(int)"),
                        self.TPSyncScroll)
        QObject.connect(self.attenDispVertBar, SIGNAL("valueChanged(int)"),
                        self.AttenSyncScroll)
        self.connect(self.channelch24, SIGNAL("otaloop(int)"),
                     self.otainit)
        self.connect(self.channelch5, SIGNAL("otaloop(int)"),
                     self.otainit)
        # self.connect(self.autoNF, SIGNAL("finished(bool)"),
        #             self.on_Testplotbtn_clicked)
        ########################################################################
        ########################################################################
        ## autoNF connect declarations ##
        self.connect(self.mantp, SIGNAL("mainstatUpdate(QString)"),
                     self.mainstatUpdate)
        self.connect(self.mantp, SIGNAL("auxstatUpdate(QString)"),
                     self.auxstatUpdate)
        self.connect(self.mantp, SIGNAL("finished(bool)"),
                     self.finished)
        self.connect(self.mantp, SIGNAL("logUpdate(QString)"),
                     self.logUpdate)

        ########################################################################
        ########################################################################
        ## timing connect declarations ##
        self.connect(self.timing, SIGNAL("mainstatUpdate(QString)"),
                     self.mainstatUpdate)
        self.connect(self.timing, SIGNAL("auxstatUpdate(QString)"),
                     self.auxstatUpdate)
        self.connect(self.timing, SIGNAL("finished(bool)"),
                     self.finished)
        self.connect(self.timing, SIGNAL("logUpdate(QString)"),
                     self.logUpdate)
        self.connect(self.timing, SIGNAL("AttenUpdate(QString)"),
                     self.AttenUpdate)
        self.timing.rssi_timepoint.connect(self.populateTable, Qt.AutoConnection)

        ########################################################################

    def initPrevSettings(self):
        try:
            with open("tanc.ini") as datfile:
                self.savedJsonDat = json.load(datfile)
                datfile.close()
            # router settings reload
            if self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterSelTCPIPCheck']:
                self.RouterSelTCPIPCheck.click()
                self.on_RouterSelTCPIPCheck_clicked()
                # Bad idea when tanc.ini gets copied between systems!
                # self.RouterTypeCombo.setCurrentIndex(self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterTypeCombo'])
                # self.on_RouterTypeCombo_activated()
            else:
                self.RouterSelCombo.setCurrentIndex(
                    self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterSelCombo'])
            self.ssid = self.savedJsonDat['leftpanel']['RouterSelConfigTab']['SSIDText']
            self.ProgramSel.setCurrentIndex(self.savedJsonDat['rightpanel']['ProgramSel'])

            # attenuator reload
            self.AttenSelCombo.setCurrentIndex(self.savedJsonDat['leftpanel']['AttenuatorBox']['AttenSelCombo'])
            # APC settings reload
            self.APCCmdCombo.setCurrentIndex(self.savedJsonDat['rightpanel']['groupBox_5']['APCCmdCombo'])
            if self.savedJsonDat['rightpanel']['groupBox_5']['APCComText'] is not None:
                self.APCComText.setText(self.savedJsonDat['rightpanel']['groupBox_5']['APCComText'])
            self.OutletSelCombo.setCurrentIndex(self.savedJsonDat['rightpanel']['groupBox_5']['OutletSelCombo'])
            # printer settings reload
            if self.savedJsonDat['leftpanel']['PrinterComBox']['IPaddrText'] is not None:
                self.IPaddrText.setText(self.savedJsonDat['leftpanel']['PrinterComBox']['IPaddrText'])
            self.Iperf3checkBox.setChecked(self.savedJsonDat['leftpanel']['PrinterComBox']['Iperf3checkBox'])
            self.MIMOCheckbox.setChecked(self.savedJsonDat['leftpanel']['PrinterComBox']['MIMOCheckbox'])
            self.WifiDirectCheckbox.setChecked(self.savedJsonDat['leftpanel']['PrinterComBox']['WifiDirectCheckbox'])
            self.PrinterTypeCombo.setCurrentIndex(self.savedJsonDat['leftpanel']['PrinterComBox']['PrinterTypeCombo'])

        except(ValueError, IOError):
            self.savedJsonDat = {u'leftpanel': {u'AttenuatorBox': {u'AttenSelCombo': 0}, u'RouterSelConfigTab': \
                {u'RouterSelTCPIPCheck': False, u'ChWidthText': None, u'ModeCombo': 0, u'radio5GHz': False,
                 u'radio2_4GHz': True, \
                 u'RouterSelCombo': 0, u'SecuritySelCombo': 0, u'Router2_4Combo': 0, u'RouterPassText': None,
                 u'RouterTypeCombo': 0, \
                 u'Router5Combo': 0, u'SSIDText': None}, u'PrinterComBox': {u'IPaddrText': None, u'SOLComText': None, \
                                                                            u'LinuxComText': None,
                                                                            u'Iperf3checkBox': True,
                                                                            u'MIMOCheckbox': False,
                                                                            u'PrinterTypeCombo': 1,
                                                                            u'WifiDirectCheckbox': False}}, \
                                 u'Main': u'TANC', u'rightpanel': {
                    u'groupBox_5': {u'APCComText': None, u'APCCmdCombo': 0, u'OutletSelCombo': 0}, u'ProgramSel': 0}}

    def saveSettings(self):
        with open("tanc.ini", "w") as jsonFile:
            jsonFile.write(json.dumps(self.savedJsonDat, sort_keys=True, \
                                      indent=4, separators=(',', ': ')))
            jsonFile.close()

    @pyqtSlot(int)
    def on_ProgramSel_currentChanged(self):
        self.savedJsonDat['rightpanel']['ProgramSel'] = self.ProgramSel.currentIndex()
        self.saveSettings()

    ###########################################################
    ###Printer Control Btns Click Definitions  <==Begin==>  ###

    @pyqtSlot()
    def waitForIpAddress(self, timeout):
        self.IPaddrText.setText('No IP')
        ipAddr = ''
        count = 0
        t = time.clock()
        while ((count < timeout) and not ipAddr):
            self.Status2Text.setText('IP wait ' + str(count) + ' seconds')
            QApplication.processEvents()
            response = self.SendCmd(udws_commands['get_config'], 'sol', self.NOPRINT)
            if response:
                print 'waitForIpAddress: ' + str(count) + ' seconds\n' + response
                # Find IP address update Text, Channel and Select if SOL/std
                chan = re.search('Channel:\s+(\d{1,3})', response, re.U)
                if chan and chan.group(1):
                    try:
                        n = int(chan.group(1))
                        if n <= 14:
                            self.chanbgUpdate(str(n))
                        else:
                            self.chanaUpdate(str(n))
                    except (ValueError, AttributeError):
                        pass
                m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', response, re.U)
                if m:
                    if m.group(1) is not None:
                        ipAddr = str(m.group(1))
                    elif m.group(2) is not None:
                        ipAddr = str(m.group(2))
            if ipAddr:
                self.IPaddrText.setText(ipAddr)
                self.textBrowser.append('[IP wait succeeded in ' + str(count) + ' seconds]\n')
                # Caveat: ASCII to unicode conversion throws exception for invalid 7-bit ASCII characters
                # self.textBrowser.append(unicode(response))
                self.textBrowser.append(response)
                break
            else:
                count += 1
                t += 1
                now = time.clock()
                if t > now:
                    time.sleep(t - now)
        if not ipAddr:
            self.textBrowser.append('[IP wait failed in ' + str(count) + ' seconds!]')
        self.updateUi()
        return ipAddr

    @pyqtSlot()
    def on_ConnectBtn_clicked(self):
        self.StatusText.setText("Connecting to AP (Wait)")
        self.Status2Text.setText("Sending Command to Printer")
        self.SendCmd(str(self.ConnCmd.text()), 'sol', self.PRINT)
        time.sleep(1)
        self.waitForIpAddress(60)
        self.StatusText.setText("Idle")
        self.Status2Text.setText("0")

    @pyqtSlot()
    def on_WifiConfigBtn_clicked(self):
        ipInfo = self.SendCmd(udws_commands['get_config'], 'sol', self.PRINT)
        # Find IP address update Text, Channel and Select if SOL/std
        if ipInfo is not -1:
            m = re.search('ip address:\s*(\d+\.\d+\.\d+\.\d+)|IP Addr:\s*(\d+\.\d+\.\d+\.\d+)', ipInfo, re.U)
            if m:
                if m.group(1) is not None:
                    self.IPaddrText.setText(str(m.group(1)))
                if m.group(2) is not None:
                    self.IPaddrText.setText(str(m.group(2)))
                chan = re.search('Channel:\s+(\d{1,3})', ipInfo, re.U)
                try:
                    n = int(chan.group(1))
                    if n <= 14:
                        self.chanbgUpdate(str(n))
                    else:
                        self.chanaUpdate(str(n))
                except (ValueError, AttributeError):
                    pass
            else:
                self.IPaddrText.setText('No IP')
            self.updateUi()

    @pyqtSlot()
    def on_NoSleepBtn_clicked(self):
        cmdsend = str(self.NoSleepCmd.text())
        self.SendCmd(cmdsend, 'sol', self.PRINT)

    @pyqtSlot()
    def on_OHBtn_clicked(self):
        cmdsend = str(self.OHCmd.text())
        self.SendCmd(cmdsend, 'sol', self.PRINT)

    @pyqtSlot()
    def on_SetAntBtn_clicked(self):
        print self.AntSelCombo.currentText()
        cmdsend = str(self.AntSelCombo.currentText())
        self.SendCmd(cmdsend, 'sol', self.PRINT)

    @pyqtSlot()
    def on_FWBtn_clicked(self):
        cmdsend = str(self.FWCheckCmd.text())
        self.SendCmd(cmdsend, 'sol', self.PRINT)

    @pyqtSlot()
    def on_ResetWifiBtn_clicked(self):
        cmdsend = str(self.ResetWifiCmd.text())
        self.SendCmd(cmdsend, 'sol', self.PRINT)

    @pyqtSlot()
    def on_SOLSendBtn_clicked(self):
        cmdsend = str(self.UserSendCmd.text())
        self.StatusText.setText("Communicating with printer")
        self.updateUi()
        self.SendCmd(cmdsend, 'sol', self.PRINT)
        self.StatusText.setText("Idle")

    @pyqtSlot()
    def on_LinuxSendBtn_clicked(self):
        cmdsend = str(self.UserSendCmd.text())
        self.SendCmd(cmdsend, 'lin', self.PRINT)

    def createTitle(self, tab):
        # Disable HP health check traffic
        self.SendCmd(udws_commands['quiet'], 'sol', self.PRINT)

        title = ''
        cmdsend = str(self.FWCheckCmd.text())
        fwVer = self.SendCmd(cmdsend, 'sol', self.PRINT)
        if fwVer:
            # Retrieve Printer Name
            prnName = re.search('([^\s]+) Built:', fwVer, re.U)
            fwrev = re.search('\{([^\s]+),', fwVer, re.U)
            serialNum = self.SendCmd(udws_commands['get_serial'], 'sol', self.PRINT)
            serNum = re.search('([\S]{3});udws\(', serialNum, re.U)
            if prnName and prnName.group(1) and fwrev and fwrev.group(1):
                title = prnName.group(1) + '_' + fwrev.group(1)
            else:
                for s in fwVer.split('\n'):
                    if not cmdsend in s and not '[' in s:
                        title = s.split()[0]
                        break
        if serNum:
            if tab == 'NF':
                title = 'NF_' + title
            elif tab == 'OTA':
                title = 'OTA_' + self.PrinterTypeCombo.currentText() + '_' + title
            title += '_' + serNum.group(1)
        if self.WifiDirectCheckbox.isChecked():
            title += '_Direct'
        else:
            if (tab == 'NF' or tab == 'OTA'):
                if self.NFDataCheckBox.isChecked():
                    if self.Iperf3checkBox.isChecked():
                        title += '_iperf3'
                    else:
                        title += '_hpTCP'
                else:
                    title = title + '_noDataStream'
            if self.radio2_4GHz.isChecked():
                title += '_2.4GHz'
            elif self.radio5GHz.isChecked():
                title += '_5GHz'
        if tab == 'NF':
            self.NF_TitleText.setText(title)
        elif tab == 'OTA':
            self.OTA_Title.setText(title)
        elif 'time' in tab:
            self.time_infoline.setText(title)

    ###---End Printer Control Btns Click Definitions     ####
    #########################################################

    def updateUi(self):
        if sys.platform.startswith('win'):
            enable = re.search('COM([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])$', self.SOLComText.text())
            enableUix = re.search('COM([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])$', self.LinuxComText.text())
            if enable is not None:
                enable = 1
                self.savedJsonDat['leftpanel']['PrinterComBox']['SOLComText'] = str(self.SOLComText.text())
            else:
                enable = 0
            if enableUix is not None:
                enableUix = 1
                self.savedJsonDat['leftpanel']['PrinterComBox']['LinuxComText'] = str(self.LinuxComText.text())
            else:
                enableUix = 0
        else:
            enable = re.search('/dev/tty.*$', self.SOLComText.text())
            enableUix = re.search('/dev/tty.*$', self.LinuxComText.text())
            if enable is not None:
                enable = 1
                self.savedJsonDat['leftpanel']['PrinterComBox']['SOLComText'] = str(self.SOLComText.text())
            else:
                enable = 0
            if enableUix is not None:
                enableUix = 1
                self.savedJsonDat['leftpanel']['PrinterComBox']['LinuxComText'] = str(self.LinuxComText.text())
            else:
                enableUix = 0
        self.ConnectBtn.setEnabled(enable)
        self.WifiConfigBtn.setEnabled(enable)
        self.NoSleepBtn.setEnabled(enable)
        self.OHBtn.setEnabled(enable)
        self.SetAntBtn.setEnabled(enable)
        self.FWBtn.setEnabled(enable)
        self.ResetWifiBtn.setEnabled(enable)
        self.SOLSendBtn.setEnabled(enable)
        self.LinuxSendBtn.setEnabled(enableUix)
        self.checkvalidIP()
        self.saveSettings()

    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - destination ('sol', 'lin', 'apc', or 'rout')
            :disp - optional print output to textBrowser
        """
        try:
            if dest == 'sol':
                ser = serial.Serial(str(self.SOLComText.text()), 115200, timeout=20, writeTimeout=10)
            elif dest == 'lin':
                ser = serial.Serial(str(self.LinuxComText.text()), 115200, timeout=10, writeTimeout=10)
            elif dest == 'apc':
                ser = serial.Serial(str(self.APCComText.text()), 115200, timeout=10, writeTimeout=10)
            elif dest == 'rout':
                ser = serial.Serial(str(self.RouterSelCombo.currentText()), 115200, timeout=10, writeTimeout=10)
        except(OSError, serial.SerialException):
            self.StatusText.setText("Serial Error")
            self.Status2Text.setText("Router COM invalid/inuse")
            QApplication.processEvents()
            time.sleep(2)
            return 'Error'
            pass

        # print self.SOLComText.text()
        ser.isOpen()
        out = ''
        ser.write('\r\n')
        ser.write('\r\n')
        time.sleep(.1)
        ser.read(ser.inWaiting())
        ser.flushInput()
        time.sleep(.1)
        ser.write(ToSend + '\r\n')

        if dest == 'sol':
            time.sleep(.3)
        else:
            time.sleep(1)
        if dest == 'sol':
            # print ser.inWaiting()
            for x in range(0, 200):
                out += ser.read(ser.inWaiting())
                if 'returns' in out:
                    break
                time.sleep(.075)
                QApplication.processEvents()
        else:
            while ser.inWaiting() > 0:
                out += ser.read(1)
        if out != '' and disp:
            try:
                self.textBrowser.append(unicode(out))
            except Exception as e:
                print out
                print 'WirelessTesting.SendCmd: unicode exception: ' + str(e)
                traceback.print_exc()
        ser.close()
        self.StatusText.setText("Idle")
        self.Status2Text.setText("0")
        return out

    #############################################################
    ###Printer Communication Widget Definitions  <==Begin==>  ###

    @pyqtSlot(QString)
    def on_SOLComText_textEdited(self):
        self.updateUi()

    @pyqtSlot(QString)
    def on_LinuxComText_textEdited(self):
        self.updateUi()

    @pyqtSlot()
    def on_Iperf3checkBox_clicked(self):
        if self.Iperf3checkBox.isChecked():
            self.PrinterTypeCombo.setCurrentIndex(PrinterTypeSoL)
        self.savedJsonDat['leftpanel']['PrinterComBox']['Iperf3checkBox'] = self.Iperf3checkBox.isChecked()
        self.saveSettings()

    @pyqtSlot()
    def on_MIMOCheckbox_clicked(self):
        self.savedJsonDat['leftpanel']['PrinterComBox']['MIMOCheckbox'] = self.MIMOCheckbox.isChecked()
        self.saveSettings()

    @pyqtSlot()
    def on_WifiDirectCheckbox_clicked(self):
        self.direct = self.WifiDirectCheckbox.isChecked()
        if self.direct:
            self.IPaddrText.setText("192.168.223.1")
            self.piAddr.setEnabled(True)
            self.piAddr.setText('192.168.1.249')
            # self.StatusText.setText("Connect To Printer SSID Direct AP")
            self.ota.initialize(
                str(self.SOLComText.text()),
                str(self.RouterSelCombo.currentText()),
                str(self.LinuxComText.text()),
                self.OTAManTestCheckBox.isChecked(),
                [],
                udws_commands, \
                self.Iperf3checkBox.isChecked(),
                str(self.OTA_PtsText.text()),
                self.radio5GHz.isChecked(),
                self.direct,
                self.piAddr)
            direct_channels = self.ota.getDirectChannelList()
        else:
            self.IPaddrText.setText("IP address")
            self.piAddr.setEnabled(False)
        self.savedJsonDat['leftpanel']['PrinterComBox']['WifiDirectCheckbox'] = self.WifiDirectCheckbox.isChecked()
        self.saveSettings()

    @pyqtSlot(int)
    def on_PrinterTypeCombo_currentIndexChanged(self):
        self.AntSelCombo.clear()
        if self.PrinterTypeCombo.currentIndex() == PrinterTypeSoC:
            print 'on_PrinterTypeCombo_currentIndexChanged: SoC'  # TBD
            self.Iperf3checkBox.setChecked(0)
            # TBD: 'antenna_all'?
            udws_commands['antenna_1'] = 'udws "ultra_spectra.set_wifi_ant 0"'
            udws_commands['antenna_2'] = 'udws "ultra_spectra.set_wifi_ant 1"'
            udws_commands['antenna_all'] = 'udws "ultra_spectra.set_wifi_ant 3"'
            self.AntSelCombo.addItems([ \
                udws_commands['antenna_1'], \
                udws_commands['antenna_2'], \
                udws_commands['antenna_all']])
            self.ResetWifiCmd.setText('udws "nca.reset_adaptors"')
            udws_commands['get_sta_rssi'] = 'udws "nc_wifi.broadcom.get_connected_sta_rssi"'
        elif self.PrinterTypeCombo.currentIndex() == PrinterTypeSoL:
            print 'on_PrinterTypeCombo_currentIndexChanged: SoL'  # TBD
            udws_commands['antenna_1'] = 'udws "nc_wifi.broadcom.set_antdiv 0"'
            udws_commands['antenna_2'] = 'udws "nc_wifi.broadcom.set_antdiv 1"'
            udws_commands['antenna_all'] = 'udws "nc_wifi.broadcom.set_antdiv 3"'
            self.AntSelCombo.addItems([ \
                udws_commands['antenna_1'], \
                udws_commands['antenna_2'], \
                udws_commands['antenna_all']])
            self.ResetWifiCmd.setText('udws "nca.restore_network_defaults"')
            udws_commands['get_sta_rssi'] = 'udws "nc_wifi.broadcom.get_connected_sta_rssi"'
        elif self.PrinterTypeCombo.currentIndex() == PrinterTypeStyx:
            print 'on_PrinterTypeCombo_currentIndexChanged: Styx'  # TBD
            # TBD: reset?
            udws_commands['antenna_1'] = 'udws "supd.marvell.set_antdiv 1"'
            udws_commands['antenna_2'] = 'udws "supd.marvell.set_antdiv 2"'
            udws_commands['antenna_all'] = 'udws "supd.marvell.set_antdiv 3"'
            self.AntSelCombo.addItems([ \
                udws_commands['antenna_1'], \
                udws_commands['antenna_2'], \
                udws_commands['antenna_all']])
            self.ResetWifiCmd.setText('udws "nca.restore_network_defaults"')  # TBD
            udws_commands['get_sta_rssi'] = 'mlanutl wlan1 getsignal'
        elif self.PrinterTypeCombo.currentIndex() == PrinterTypeStingray:
            print 'on_PrinterTypeCombo_currentIndexChanged: Stingray'  # TBD
            # TBD: reset?
            udws_commands['antenna_1'] = 'udws "supd.set_antdiv 1"'
            udws_commands['antenna_2'] = 'udws "supd.set_antdiv 2"'
            udws_commands['antenna_all'] = 'udws "supd.set_antdiv 3"'
            self.AntSelCombo.addItems([ \
                udws_commands['antenna_1'], \
                udws_commands['antenna_2'], \
                udws_commands['antenna_all']])
            self.ResetWifiCmd.setText('udws "nca.restore_network_defaults"')  # TBD
            udws_commands['get_sta_rssi'] = 'udws "supd.realtek.get_connected_sta_rssi"'

        elif self.PrinterTypeCombo.currentIndex() == PrinterTypePi:
            print 'on_PrinterTypeCombo_currentIndexChanged: Pi'  # TBD
            # TBD
        else:
            print 'on_PrinterTypeCombo_currentIndexChanged: invalid printer type ' + str(
                self.PrinterTypeCombo.currentIndex())
        self.updateConnCmd()
        udws_commands['reset'] = str(self.ResetWifiCmd.text())
        self.savedJsonDat['leftpanel']['PrinterComBox']['PrinterTypeCombo'] = self.PrinterTypeCombo.currentIndex()
        self.saveSettings()

    def serial_ports(self):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            print p
            # self.textBrowser.append(unicode(p))
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port, 115200)
                time.sleep(.1)
                out = ''
                s.write('\x04\r\n')
                time.sleep(.1)
                s.write('\r\n')
                time.sleep(.1)
                s.write('\x03\r\n')
                time.sleep(.1)
                s.write('udws\r\n')
                time.sleep(.25)
                while s.inWaiting() > 0:
                    out += s.read(1)
                udws = re.search('udws\(\) returns -1', out)
                linux = re.search('root@HP[0-9A-F]{6}', out)
                s.close()
                if udws:
                    result.append(port)
                    self.SOLComText.setText(str(port))
                if linux:
                    result.append(port)
                    self.LinuxComText.setText(str(port))
            except (OSError, serial.SerialException):
                pass
        return result

    ###---End Printer Communication Widget Definitions   ####
    #########################################################

    ##########################################################
    ### Attenuator Control                    <==Begin==>  ###

    def AttenInit(self):
        if self.AttenPresentCheckbox.isChecked():
            try:
                if str(self.AttenSelCombo.currentText()) in ['keysight11713c', 'aeroflex8310', 'agilent11713a']:
                    self.rm = visa.ResourceManager()
                    device = GpibDevice.get_devices()
                    if 'keysight11713c' in device:
                        # print 'keysight11713c initialized'
                        dev = device['keysight11713c'][1]
                        bd = device['keysight11713c'][0]
                        self.attenuator = Attenuator.connect('keysight11713c', board=bd, device=dev)
                        self.attenType = '11713c'
                    if 'aeroflex8310' in device:
                        # print 'aeroflex8310 initialized'
                        dev = device['aeroflex8310'][1]
                        bd = device['aeroflex8310'][0]
                        self.attenuator = Attenuator.connect('aeroflex8310', board=bd, device=dev)
                        self.attenType = '8310'
                    if 'agilent11713a' in device:
                        # print 'agilent11713a initialized'
                        dev = device['agilent11713a'][1]
                        bd = device['agilent11713a'][0]
                        self.attenuator = Attenuator.connect('agilent11713a', board=bd, device=dev)
                        self.attenType = '11713a'
                elif str(self.AttenSelCombo.currentText()) in 'JFW50PA':
                    # print 'jfw50pa initialized'
                    self.attenuator = Attenuator.connect('jfw50pa', ip=str(self.AttenCommInfoText.text()))
                    self.attenType = 'jfw50pa'
                elif str(self.AttenSelCombo.currentText()) in 'agilentj7211':
                    # print 'agilentj7211 initialized'
                    self.attenuator = Attenuator.connect('agilentj7211', ip=str(self.AttenCommInfoText.text()))
                    self.attenType = 'j7211'
                elif str(self.AttenSelCombo.currentText()) in 'rc4dat':
                    # print 'rc4dat initialized'
                    self.attenuator = Attenuator.connect('rc4dat')
                    self.attenType = 'rc4dat'
                self.AttenPresentCheckbox.setChecked(True)
                self.StatusText.setText("Connected")
                self.Status2Text.setText("Attenuator Ready")
                QApplication.processEvents()
            except(OSError):
                self.StatusText.setText("GPIB Error")
                self.Status2Text.setText("GPIB not Present")
                self.AttenPresentCheckbox.setChecked(False)
                QApplication.processEvents()
                time.sleep(2)
                pass
            except(error, timeout):
                self.StatusText.setText("Socket Error")
                self.Status2Text.setText("Check Network Connection")
                self.AttenPresentCheckbox.setChecked(False)
                QApplication.processEvents()
                time.sleep(2)

    @pyqtSlot(QString)
    def on_AttenCommInfoText_textEdited(self):
        if str(self.AttenSelCombo.currentText()) in ['JFW50PA', 'agilentj7211']:
            enable = re.search('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', self.AttenCommInfoText.text())
            if enable is not None:
                enable = 1
            else:
                enable = 0
            self.AttenSetBtn.setEnabled(enable)

    @pyqtSlot(int)
    def on_AttenSelCombo_activated(self):
        AttenDev = str(self.AttenSelCombo.currentText())
        if AttenDev == 'rc4dat':
            self.AttenCommInfoText.setText("192.168.1.76")
            self.AttenCommInfoText.setEnabled(True)
            self.GetRSSIBtn.setEnabled(True)
            self.OTA_Max.setText('95')
        if AttenDev == 'JFW50PA':
            self.AttenCommInfoText.setText("192.168.1.250")
            self.AttenCommInfoText.setEnabled(True)
            self.GetRSSIBtn.setEnabled(False)
            self.OTA_Max.setText('63')
        if AttenDev == 'agilentj7211':
            self.AttenCommInfoText.setText("192.168.0.12")
            self.AttenCommInfoText.setEnabled(True)
            self.GetRSSIBtn.setEnabled(False)
        if AttenDev == 'keysight11713c':
            self.AttenCommInfoText.setText("IP or Serial")
            self.AttenCommInfoText.setEnabled(False)
            self.GetRSSIBtn.setEnabled(True)
            self.getAttenLvl()
            self.OTA_Max.setText('79')
        if AttenDev == 'aeroflex8310':
            self.AttenCommInfoText.setText("IP or Serial")
            self.AttenCommInfoText.setEnabled(False)
            self.GetRSSIBtn.setEnabled(False)
        if AttenDev == 'agilent11713a':
            self.AttenCommInfoText.setText("IP or Serial")
            self.AttenCommInfoText.setEnabled(False)
            self.GetRSSIBtn.setEnabled(False)
        self.savedJsonDat['leftpanel']['AttenuatorBox']['AttenSelCombo'] = self.AttenSelCombo.currentIndex()
        self.saveSettings()
        self.AttenInit()

    @pyqtSlot()
    def on_AttenPresentCheckbox_released(self):
        self.AttenInit()

    #    def AttenControlGPIB(self,attnstr):
    #        GPIBaddress='3'
    #        addstr='GPIB0::'+GPIBaddress+'::INSTR'
    #        inst=self.rm.open_resource(addstr)
    #        attnint=int(attnstr)
    #
    #        if -1 <attnint < 80:
    #
    #            if len(attnstr)==1:
    #                xval=attnstr[0]
    #                yval='0'
    #
    #            if len(attnstr)==2:
    #                xval=attnstr[1]
    #                yvalnum=attnint-int(xval)
    #                yval=str(yvalnum)
    #
    #            inst.write('ATT:BANK1:X %s' % xval)
    #            inst.write('ATT:BANK1:Y %s' % yval)
    #
    #            inst.write('ATT:BANK2:X %s' % xval)
    #            inst.write('ATT:BANK2:Y %s' % yval)
    #            inst.close()
    #        else:
    #            self.StatusText.setText("Error")
    #            self.Status2Text.setText("Enter level between 0-79")
    #            QApplication.processEvents()
    #            time.sleep(2)
    #
    #    def AttenControlJFW(self,attnstr):
    #        attenuator = JFW50PA(ip_addr=str(self.AttenCommInfoText.text()))
    #        attenuator.Open()
    #        attenuator.setAttenuator(1, int(attnstr))
    #        attenuator.Send()
    #        attenuator.Close()

    # Close attenuator IP connection in preparation for AP reboot
    def preChange(self):
        if self.attenuator:
            # Note: JFW50PA connects over Ethernet through the AP
            if self.attenType == 'jfw50pa':
                print 'preChange: closing ' + self.attenType + ' attenuator.'
                try:
                    self.attenuator.Close()
                except Exception as e:
                    print 'preChange recovering from exception: ' + str(e)
                    traceback.print_exc()
                finally:
                    self.attenuator = None

    # Open attenuator connection if closed
    def AttenCheck(self):
        if not self.attenuator:
            print 'AttenCheck: opening ' + self.attenType + ' attenuator.'
            self.AttenInit()
            if not self.attenuator:
                print 'AttenCheck: open of ' + self.attenType + ' attenuator failed!!!'

    def getAttenLvl(self):
        if str(self.AttenSelCombo.currentText()) == 'keysight11713c':
            GPIBaddress = '3'
            addstr = 'GPIB0::' + GPIBaddress + '::INSTR'
            try:
                inst = self.rm.open_resource(addstr)
                bank1 = int(inst.ask('ATT:BANK1:X?')) + int(inst.ask('ATT:BANK1:Y?'))
                bank2 = int(inst.ask('ATT:BANK2:X?')) + int(inst.ask('ATT:BANK2:Y?'))
                if bank2 >= bank1:
                    self.attenlvlUpdate(bank2)
                else:
                    self.attenlvlUpdate(bank1)
            except:
                self.AttenPresentCheckbox.setChecked(False)
                pass

    @pyqtSlot()
    def on_AttenSetBtn_clicked(self):
        time.sleep(1)
        self.AttenUpdate(str(self.LvlSetText.text()))
        try:
            timeleft = 7
            self.StatusText.setText("Changing Attenuator (Wait)")
            for x in range(0, 30):
                QApplication.processEvents()
                time.sleep(.2)
                if not (x % 5):
                    timeleft -= 1
                    string = str(timeleft) + " sec left"
                    self.Status2Text.setText(string)
                    QApplication.processEvents()

            self.on_GetRSSIBtn_clicked()
            self.on_WifiConfigBtn_clicked()
        except:
            self.StatusText.setText("Error")
            self.Status2Text.setText("Attenuator Error")
            QApplication.processEvents()
            time.sleep(2)

        self.StatusText.setText("Idle")
        self.Status2Text.setText("0")

    @pyqtSlot()
    def on_GetRSSIBtn_clicked(self):
        SNRInfo = self.SendCmd(udws_commands['get_config'], 'sol', self.NOPRINT)
        # Find RSSI and Noise
        rssi = re.search('signalStrength:\s*(-\d+)', SNRInfo, re.U)
        noise = re.search('noise:\s*(-\d+)', SNRInfo, re.U)
        if rssi:
            if rssi.group(1) is not None:
                self.RSSIText.setText(rssi.group(1))
        else:
            self.RSSIText.setText('---')
        if noise:
            if noise.group(1) is not None:
                self.NoiseText.setText(noise.group(1))
        else:
            self.NoiseText.setText('---')
        self.getAttenLvl()

    @pyqtSlot(QString)
    def on_LvlSetText_textChanged(self):
        enable = re.search('^([0-9]|[1-9][0-9])$', self.LvlSetText.text())
        if enable is not None:
            enable = 1
        else:
            enable = 0
        self.AttenSetBtn.setEnabled(enable)

    @pyqtSlot(QString)
    def on_RSSIText_textChanged(self):
        enable = re.search('^(0|-0?[0-9]|-0?[1-9][0-9])$', self.RSSIText.text())
        if enable is not None:
            enable = 1
        else:
            enable = 0
        self.SetRSSIBtn.setEnabled(enable)

    # Update only the attenuation level text box
    def attenlvlUpdate(self, attenlvl):
        self.LvlSetText.setText(str(attenlvl))

    @pyqtSlot()
    def on_SetRSSIBtn_clicked(self):
        if self.timing.isRunning():
            self.StatusText.setText("Timing Tests Currently running")
        else:
            if int(self.RSSIText.text()) < -20 and int(self.RSSIText.text()) > -90:
                self.timing.onlyRSSIset(int(self.RSSIText.text()), str(self.SOLComText.text()))
                self.timing.start()
            else:
                self.StatusText.setText("Invalid RSSI Range set between -20 <> -90")

    ###---End      Attenuator Control ------------------ ####
    #########################################################

    #############################################################
    ###     Router Control Widget Definitions  <==Begin==>    ###

    @pyqtSlot(QString)
    def on_SSIDText_textEdited(self, text):
        # print 'on_SSIDText_textEdited(' + str(text) + ')'
        self.ssid = str(self.SSIDText.text())
        self.updateConnCmd()

    @pyqtSlot(QString)
    def on_RouterPassText_textEdited(self, text):
        # print 'on_RouterPassText_textEdited(' + str(text) + ')'
        self.updateConnCmd()

    @pyqtSlot()
    def on_RouterSelTCPIPCheck_clicked(self):
        # Function to handle GUI buttons when TCPIPCheck
        tcp = self.RouterSelTCPIPCheck.isChecked()
        com = not tcp
        self.ChWidthCombo.setEnabled(tcp)
        self.ModeCombo.setEnabled(tcp)
        self.RouterSelCombo.setEnabled(com)
        self.RouterTypeCombo.setEnabled(tcp)
        self.SecuritySelCombo.setEnabled(tcp)
        self.NF_StartBtn.setEnabled(False)  # TBD - why wait for SSID to change?
        self.NF_PrnChans.setEnabled(False)  # TBD - why wait for SSID to change?
        # TBD - why select arbitrary router and security?
        # if tcp:
        #   self.RouterTypeCombo.setCurrentIndex(1)
        #   self.SecuritySelCombo.setCurrentIndex(1)

        # TODO:keep value is True
        self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterSelTCPIPCheck'] = True
        self.saveSettings()

    @pyqtSlot()
    def on_radio2_4GHz_clicked(self):
        # if self.radio2_4GHz.isChecked():
        #     self.NF_5SelList.setEnabled(False)
        #     self.NF_24SelList.setEnabled(True)
        #     self.OTA_5SelList.setEnabled(False)
        #     self.OTA_24SelList.setEnabled(True)
        # else:
        #     self.NF_5SelList.setEnabled(True)
        #     self.NF_24SelList.setEnabled(False)
        #     self.OTA_5SelList.setEnabled(True)
        #     self.OTA_24SelList.setEnabled(False)
        # QApplication.processEvents()
        # if self.RouterSelTCPIPCheck.isChecked():
        #     if self.radio2_4GHz.isChecked():
        #         if not self.ModeCombo.currentIndex() < 0:
        #             self.ModeCombo.setCurrentIndex(0)
        #         if self.ChWidthCombo.currentIndex() < 0:
        #             self.ChWidthCombo.setCurrentIndex(0)
        #     self.on_RouterTypeCombo_activated()
        # else:
        #     self.on_RouterSelCombo_activated()
        # self.savedJsonDat['leftpanel']['RouterSelConfigTab']['radio2_4GHz'] = self.radio2_4GHz.isChecked()
        # self.savedJsonDat['leftpanel']['RouterSelConfigTab']['radio5GHz'] = self.radio5GHz.isChecked()
        # self.saveSettings()
        pass

    @pyqtSlot()
    def on_radio5GHz_clicked(self):
        # if self.radio5GHz.isChecked():
        #     self.NF_5SelList.setEnabled(True)
        #     self.NF_24SelList.setEnabled(False)
        #     self.OTA_5SelList.setEnabled(True)
        #     self.OTA_24SelList.setEnabled(False)
        # else:
        #     self.NF_5SelList.setEnabled(False)
        #     self.NF_24SelList.setEnabled(True)
        #     self.OTA_5SelList.setEnabled(False)
        #     self.OTA_24SelList.setEnabled(True)
        # QApplication.processEvents()
        # if self.RouterSelTCPIPCheck.isChecked():
        #     if self.radio5GHz.isChecked():
        #         if not self.ModeCombo.currentIndex() < 0:
        #             self.ModeCombo.setCurrentIndex(0)
        #         if self.ChWidthCombo.currentIndex() < 0:
        #             self.ChWidthCombo.setCurrentIndex(0)
        #     self.on_RouterTypeCombo_activated()
        # else:
        #     self.on_RouterSelCombo_activated()
        # self.savedJsonDat['leftpanel']['RouterSelConfigTab']['radio2_4GHz'] = self.radio2_4GHz.isChecked()
        # self.savedJsonDat['leftpanel']['RouterSelConfigTab']['radio5GHz'] = self.radio5GHz.isChecked()
        # self.saveSettings()
        pass

    def getRouter(self):
        router = str(self.__RouterTypeCombo)
        if 'AC68U' in router:
            router = 'rtac68u'
        elif 'R7000' in router:
            router = 'r7000'
        elif 'SBG6580' in router:
            router = 'sbg6580'
        elif 'WR841Nv72' in router:
            router = 'tlwr841v72'
        elif 'WR841Nv11' in router:
            router = 'tlwr841nv11'
        elif 'f9k1102v1' in router:
            router = 'f9k1102v1'
        elif 'WNR2000v2' in router:
            router = 'wnr2000v2'
        elif 'WNR3500v1' in router:
            router = 'wnr3500v1'
        elif 'E1200' in router:
            router = 'e1200v2'
        elif 'RTN66U' in router:
            router = 'rtn66u'
        elif 'RTAC87U' in router:
            router = 'rtn66u'
            # router = 'rtac87u'
            # router = 'rtac68u'
        elif 'EA6300' in router:
            router = 'ea6300'
        else:
            print "Select a router"
        return router

    def dispRouter(self, router, band):
        ap_factory = AP.AccessPointFactory()
        ap = ap_factory.getAccessPoint(router, band)
        print "disprouter %s" % band
        if ap:
            print "ap not null"
            try:
                ssid = None
                security = None
                mode = None
                channel = None
                channel_width = None
                current = str(ap)
                print current
                m = re.search('SSID:\s*(\S+)', current, re.U)
                if m and m.group(1):
                    ssid = str(m.group(1))
                m = re.search('channel:\s*(\S+)', current, re.U)
                if m and m.group(1):
                    channel = str(m.group(1))
                    print "channel = %s" % channel
                m = re.search('mode:\s*(\S+)', current, re.U)
                if m and m.group(1):
                    mode = str(m.group(1))
                m = re.search('width:\s*(\S+)', current, re.U)
                if m and m.group(1):
                    channel_width = str(m.group(1))
                    print "got from group ch width = %s" % channel_width
                m = re.search('security:\s*(\S+)', current, re.U)
                if m and m.group(1):
                    security = str(m.group(1))
                # print 'current'\
                #    + ' ssid='          + ssid\
                #    + ' channel='       + channel\
                #    + ' mode='          + mode\
                #    + ' channel_width=' + channel_width\
                #    + ' security='      + security

                # Convert tabs to spaces at 8 character tabstops and output
                # (Qt text browser does tabstops in pixels, not characters.)
                if '\t' in current:
                    lines = current.split('\n')
                    current = ''
                    for line in lines:
                        while True:
                            i = line.find('\t')
                            if i < 0:
                                break
                            spaces = ' ' * (8 - (i % 8))
                            line = line.replace('\t', spaces, 1)
                        if len(current) == 0:
                            current = line
                        else:
                            current += '\n' + line
                self.logUpdate(current)

                if not ssid:
                    ssid = str(ap.GetSSID())
                if not channel:
                    channel = str(ap.GetChannel())
                if not mode:
                    mode = str(ap.GetMode())
                if not channel_width:
                    channel_width = str(ap.GetChannelWidth())
                print "chan width is %s" % channel_width
                if not security:
                    security = 'Open'  # TBD - no GetSecurity() method!

                supported_channels = ap.supported_channels
                supported_modes = ap.supported_modes
                supported_channel_widths = ap.supported_channel_widths
                print "supp chan width is %s" % supported_channel_widths
                print "HACK support channel!!!!!!!!"
                supported_channel_widths = ['20', '20/40', '40', '80']
                supported_securities = ap.supported_securities
                self.savedJsonDat['leftpanel']['RouterSelConfigTab']['SSIDText'] = ssid
                self.savedJsonDat['leftpanel']['RouterSelConfigTab']['ChWidthText'] = channel_width
                self.savedJsonDat['leftpanel']['RouterSelConfigTab']['ModeText'] = mode
                print '\n Present settings:\n'
                print '\t' + current + '\n\n'
                print '\n =======================================\n ' + band + 'GHz router properties\n ===================================\n'
                print '\tSSID=' + ssid
                print '\tAvailable Channels {}' + str(supported_channels) + ' (' + channel + '}'
                print '\tAvailable Modes {}' + str(supported_modes) + ' (' + mode + '}'
                print '\tAvailable Channel Widths ' + str(supported_channel_widths) + ' (' + channel_width + '}'
                print '\tAvailable Securities ' + str(supported_securities) + ' (' + security + '}'
                self.updateSSID(ssid, channel)
                self.updateSecurities(supported_securities, security)
                self.updateModes(supported_modes, mode)
                self.updateChannels(supported_channels, channel)
                self.updateChannelWidths(supported_channel_widths, channel_width)
                self.saveSettings()
                self.dispRouterDone = True
                return True
            except Exception as e:
                print 'dispRouter caught exception: ' + str(e)
                traceback.print_exc()
        return False

    def dispRouterProp(self):
        router = self.getRouter()
        print "Getting router settings for %s" % router
        band = None
        if self.radio2_4GHz.isChecked():
            if (router in WirelessTesting.TwofourOnlyRouters) or (router in WirelessTesting.FiveGHzRouters):
                band = '2.4'
        elif self.radio5GHz.isChecked():
            if router in WirelessTesting.FiveGHzRouters:
                band = '5'
        if band:
            for retry in range(3):
                try:
                    if self.dispRouter(router, band):
                        break
                except Exception as e:
                    print 'dispRouterProp caught exception: ' + str(e)
                    traceback.print_exc()

    # Update SSID in connect command
    def updateConnCmd(self, channel=None):
        ssid = str(self.SSIDText.text())
        if not ssid:
            ssid = 'r0_tmz'  # TBD - default SSID?
        password = str(self.RouterPassText.text())
        if self.PrinterTypeCombo.currentIndex() == PrinterTypeSoC:
            self.ConnCmd.setText(
                'udws "nca.swc poe=t&mode=i&ssLen=' + str(len(ssid)) + '&ssid=' + ssid + '&auth=o&encrypt=n"')
        else:
            text = str(self.ConnCmd.text()).split(' ')
            if len(text) == 5:
                if password:
                    text = text[0] + ' ' + text[1] + ' ' + text[2] + ' ' + ssid + ' ' + password + '"'
                else:
                    text = text[0] + ' ' + text[1] + ' ' + text[2] + ' ' + ssid + ' ' + text[4]
            elif password:
                text = 'udws "nca.set_dot11_cfg wlan0 ' + ssid + ' ' + password + '"'
            else:
                text = 'udws "nca.set_dot11_cfg wlan0 ' + ssid + '"'
            self.ConnCmd.setText(text)
        udws_commands['connect'] = str(self.ConnCmd.text())

    # Update SSID and channel
    def updateSSID(self, ssid, channel):
        return
        if not ssid or not channel:
            # Get SSID and channel from router
            if self.RouterSelTCPIPCheck.isChecked():
                ap = None
                band = None
                router = self.getRouter()
                if self.radio2_4GHz.isChecked():
                    if (router in WirelessTesting.TwofourOnlyRouters) or (router in WirelessTesting.FiveGHzRouters):
                        band = '2.4'
                elif self.radio5GHz.isChecked():
                    if router in WirelessTesting.FiveGHzRouters:
                        band = '5'
                if band:
                    ap_factory = AP.AccessPointFactory()
                    ap = ap_factory.getAccessPoint(router, band)
                if ap:
                    ssid = str(ap.GetSSID())
                    channel = str(ap.GetChannel())
                if ssid:
                    print 'updateSSID: ' + band + ' GHz SSID    for ' + router + ' is ' + ssid
                else:
                    print 'updateSSID: Could not get SSID for ' + router
                    self.StatusText.setText(router + ' is not a valid router')
                if channel:
                    print 'updateSSID: ' + band + ' GHz channel for ' + router + ' is ' + channel
                else:
                    print 'updateSSID: Could not get channel for ' + router
                    self.StatusText.setText(router + ' is not a valid router')
            else:
                if self.radio2_4GHz.isChecked():
                    res1 = self.SendCmd('nvram show|grep wl0_ssid', 'rout', self.PRINT)
                    res1 = self.SendCmd('nvram show|grep wl0_chanspec', 'rout', self.PRINT)
                    ssid = re.search('wl0_ssid=(\S+)', res, re.U)
                    channel = re.search('wl0_chanspec=(\d+)', res, re.U)
                elif self.radio5GHz.isChecked():
                    res = self.SendCmd('nvram show|grep wl1_ssid', 'rout', self.PRINT)
                    res1 = self.SendCmd('nvram show|grep wl1_chanspec', 'rout', self.PRINT)
                    ssid = re.search('wl1_ssid=(\S+)', res, re.U)
                    channel = re.search('wl1_chanspec=(\d+)', res, re.U)
                if ssid and ssid.group(1):
                    ssid = ssid.group(1)
                else:
                    ssid = None
                    print 'updateSSID: Could not get SSID for ' + self.RouterSelCombo.currentText()
                    self.StatusText.setText(
                        'COM port "' + self.RouterSelCombo.currentText() + '" is not a valid router')
                if channel and channel.group(1):
                    channel = channel.group(1)
                else:
                    channel = None
                    print 'updateSSID: Could not get channel for ' + self.RouterSelCombo.currentText()
                    self.StatusText.setText(
                        'COM port "' + self.RouterSelCombo.currentText() + '" is not a valid router')
        if ssid:
            if channel and ('Ch' in ssid):
                i = ssid.find('Ch')
                if i >= 0:
                    ssid = ssid[:i + 2] + channel
                    print 'updateSSID: ssid=' + ssid  # TBD
            self.ssid = ssid
            self.SSIDText.setText(self.ssid)
            self.updateConnCmd()
            self.NF_StartBtn.setEnabled(True)
            self.NF_PrnChans.setEnabled(True)
            self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterSelCombo'] = self.RouterSelCombo.currentIndex()
            self.saveSettings()
            if self.radio5GHz.isChecked():
                self.Router2_4Combo.setEnabled(False)
                self.Router5Combo.setEnabled(True)
            elif self.radio2_4GHz.isChecked():
                self.Router2_4Combo.setEnabled(True)
                self.Router5Combo.setEnabled(False)
        else:
            self.SSIDText.setText("SSID")
            self.NF_StartBtn.setEnabled(False)
            self.NF_PrnChans.setEnabled(False)
            self.Router2_4Combo.setEnabled(False)
            self.Router5Combo.setEnabled(False)
        if channel:
            if self.radio2_4GHz.isChecked():
                self.chanbgUpdate(channel)
            elif self.radio5GHz.isChecked():
                self.chanaUpdate(channel)

    # Return list of currently selected OTA channels for currently selected band
    def getSelectedOtaChannels(self, band=''):
        # channels = []
        # if band == '5':
        #     is5GHz = True
        # elif band == '2.4':
        #     is5GHz = False
        # else:
        #     is5GHz = self.radio5GHz.isChecked()
        # if is5GHz:
        #     for item in self.OTA_5SelList.selectedItems():
        #         channels.append(str(item.text()))
        # else:
        #     for item in self.OTA_24SelList.selectedItems():
        #         channels.append(str(item.text()))
        # return channels # Caveat: May be empty list!
        pass

    # Select OTA channels for currently selected band from list
    def setSelectedOtaChannels(self, channels, band=''):
        # if band == '5':
        #     is5GHz = True
        # elif band == '2.4':
        #     is5GHz = False
        # else:
        #     is5GHz = self.radio5GHz.isChecked()
        # if is5GHz:
        #     for i in range(self.OTA_5SelList.count()):
        #         item = self.OTA_5SelList.item(i)
        #         if channels:
        #             item.setSelected(str(item.text()) in channels)
        #         else:
        #             item.setSelected(False)
        # else:
        #     for i  in range(self.OTA_24SelList.count()):
        #         item = self.OTA_24SelList.item(i)
        #         if channels:
        #             item.setSelected(str(item.text()) in channels)
        #         else:
        #             item.setSelected(False)
        pass

    # Return list of currently selected OTA antennas
    # Valid list elements are '1', '2', 'All'
    def getSelectedOtaAntennas(self):
        antennas = []
        for item in self.OTA_AntSelList.selectedItems():
            antennas.append(str(item.text()))
        return antennas

    # Select OTA antennas from list
    # Valid list elements are '1', '2', 'All'
    def setSelectedOtaAntennas(self, antennas):
        for i in range(self.OTA_AntSelList.count()):
            item = self.OTA_AntSelList.item(i)
            if antennas:
                item.setSelected(str(item.text()) in antennas)
            else:
                item.setSelected(False)

    def updateChannels(self, supported_channels, channel):
        # print 'updateChannels(' + str(supported_channels) + ', ' + str(channel) + ')'
        #
        # # Work-around for R700 returning 'Auto' and '0' in supported channel list:
        # list = []
        # for x in supported_channels:
        #     if x != 'Auto' and x != '0':
        #         list.append(x)
        # supported_channels = list
        #
        # if supported_channels and self.supported_channels != supported_channels:
        #     self.supported_channels = supported_channels
        #
        #     # Save selected channel list
        #     selected_channels = self.getSelectedOtaChannels()
        #
        #     if self.radio5GHz.isChecked():
        #         # Rebuild channel combo box
        #         while self.Router5Combo.count() > 0:
        #             self.Router5Combo.removeItem(0)
        #         self.Router5Combo.addItems(supported_channels)
        #
        #        # Rebuild OTA channel list box
        #         self.OTA_5SelList.clear()
        #         self.OTA_5SelList.addItems(supported_channels)
        #     else:
        #         # Rebuild channel combo box
        #         while self.Router2_4Combo.count() > 0:
        #             self.Router2_4Combo.removeItem(0)
        #         self.Router2_4Combo.addItems(supported_channels)
        #
        #         # Rebuild OTA channel list box
        #         self.OTA_24SelList.clear()
        #         self.OTA_24SelList.addItems(supported_channels)
        #
        #     # Reselect previously selected channels
        #     self.setSelectedOtaChannels(selected_channels)
        #
        #     self.channel = None
        # if channel and self.channel != channel:
        #     if self.radio5GHz.isChecked():
        #         self.chanaUpdate(channel)
        #     else:
        #         self.chanbgUpdate(channel)
        pass

    def updateModes(self, supported_modes, mode):
        print 'updateModes(' + str(supported_modes) + ', ' + str(mode) + ')'
        if supported_modes and self.supported_modes != supported_modes:
            self.supported_modes = supported_modes
            while self.ModeCombo.count() > 0:
                self.ModeCombo.removeItem(0)
            self.ModeCombo.addItems(supported_modes)
            self.mode = None
        if mode and self.mode != mode:
            try:
                for i in range(self.ModeCombo.count()):
                    if str(self.ModeCombo.itemText(i)) == mode:
                        self.ModeCombo.setCurrentIndex(i)
                        self.mode = mode
                        break
            except (ValueError, AttributeError):
                pass
        if self.ModeCombo.currentIndex() < 0:
            self.ModeCombo.setCurrentIndex(0)

    def updateChannelWidths(self, supported_channel_widths, channel_width):
        print 'updateChannelWidths(' + str(supported_channel_widths) + ', ' + str(channel_width) + ')'
        if supported_channel_widths and self.supported_channel_widths != supported_channel_widths:
            self.supported_channel_widths = supported_channel_widths
            while self.ChWidthCombo.count() > 0:
                self.ChWidthCombo.removeItem(0)
            self.ChWidthCombo.addItems(supported_channel_widths)
            self.channel_width = None
        if channel_width and self.channel_width != channel_width:
            try:
                for i in range(self.ChWidthCombo.count()):
                    if str(self.ChWidthCombo.itemText(i)) == channel_width:
                        self.ChWidthCombo.setCurrentIndex(i)
                        self.channel_width = channel_width
                        break
            except (ValueError, AttributeError):
                pass
        if self.ChWidthCombo.currentIndex() < 0:
            self.ChWidthCombo.setCurrentIndex(0)

    def updateSecurities(self, supported_securities, security):
        print 'updateSecurities(' + str(supported_securities) + ', ' + str(security) + ')'
        if supported_securities and self.supported_securities != supported_securities:
            self.supported_securities = supported_securities
            while self.SecuritySelCombo.count() > 0:
                self.SecuritySelCombo.removeItem(0)
            self.SecuritySelCombo.addItems(supported_securities)
            self.security = None
        if security and self.security != security:
            try:
                for i in range(self.SecuritySelCombo.count()):
                    if str(self.SecuritySelCombo.itemText(i)) == security:
                        self.SecuritySelCombo.setCurrentIndex(i)
                        self.security = security
                        break
            except (ValueError, AttributeError):
                pass
        if self.SecuritySelCombo.currentIndex() < 0:
            self.SecuritySelCombo.setCurrentIndex(0)

    @pyqtSlot(int)
    def on_RouterTypeCombo_activated(self):
        if self.ssid is not None:
            self.savedJsonDat['leftpanel']['RouterSelConfigTab']['SSIDText'] = self.ssid
            self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterTypeCombo'] = self.__RouterTypeCombo
            self.saveSettings()
        self.dispRouterProp()

    @pyqtSlot(int)
    def on_RouterSelCombo_activated(self):
        self.updateSSID(None, None)
        if self.ssid is not None:
            self.savedJsonDat['leftpanel']['RouterSelConfigTab']['SSIDText'] = self.ssid
            self.savedJsonDat['leftpanel']['RouterSelConfigTab']['RouterSelCombo'] = self.RouterSelCombo.currentIndex()
            self.saveSettings()

    @pyqtSlot(int)
    def on_Router2_4Combo_activated(self):
        router = self.getRouter()
        otacheck = False
        if self.ModeCombo.currentIndex() < 0:
            self.ModeCombo.setCurrentIndex(0)
        if self.ChWidthCombo.currentIndex() < 0:
            self.ChWidthCombo.setCurrentIndex(0)
        if self.channelch24.isRunning():
            self.channelch24.stop()
            self.channelch24.wait()
        self.channelch24.initialize( \
            str(self.SOLComText.text()), \
            str(self.RouterSelCombo.currentText()), \
            str(self.Router2_4Combo.currentText()), \
            udws_commands, \
            self.RouterSelTCPIPCheck.isChecked(), \
            router, \
            str(self.__SecuritySelCombo), \
            str(self.ModeCombo.currentText()), \
            str(self.ChWidthCombo.currentText()), \
            otacheck)
        self.preChange()
        self.channelch24.start()

    @pyqtSlot(int)
    def on_Router5Combo_activated(self):
        router = self.getRouter()
        if router in WirelessTesting.FiveGHzRouters:
            otacheck = False
            if self.ModeCombo.currentIndex() < 0:
                self.ModeCombo.setCurrentIndex(0)
            if self.ChWidthCombo.currentIndex() < 0:
                self.ChWidthCombo.setCurrentIndex(0)
            if self.channelch5.isRunning():
                self.channelch5.stop()
                self.channelch5.wait()
            self.channelch5.initialize( \
                str(self.SOLComText.text()), \
                str(self.RouterSelCombo.currentText()), \
                str(self.Router5Combo.currentText()), \
                udws_commands, \
                self.RouterSelTCPIPCheck.isChecked(), \
                router, \
                str(self.__SecuritySelCombo), \
                str(self.ModeCombo.currentText()), \
                str(self.ChWidthCombo.currentText()), \
                otacheck)
            self.preChange()
            self.channelch5.start()
        else:
            print "%s does not support dual band" % router

    ###---End      Router Control Widget Definitions     ####
    #########################################################

    #############################################################
    ###            STATUS UPDATES Definitions  <==Begin==>    ###

    @pyqtSlot(bool)
    def finished(self, completed):
        self.StatusText.setText("Idle")
        self.Status2Text.setText("0")

    @pyqtSlot(QString)
    def mainstatUpdate(self, statusUpdate):
        self.StatusText.setText(statusUpdate)

    @pyqtSlot(QString)
    def auxstatUpdate(self, statusUpdate):
        self.Status2Text.setText(statusUpdate)

    @pyqtSlot(QString)
    def logUpdate(self, statusUpdate):
        datenow = datetime.datetime.strftime(datetime.datetime.now(), "%a %H:%M:%S: ")
        self.textBrowser.append(datenow + statusUpdate)

    @pyqtSlot(QString)
    def IPUpdate(self, statusUpdate):
        self.IPaddrText.setText(statusUpdate)

    # Update attenuation level and attenuation level text box
    @pyqtSlot(QString)
    def AttenUpdate(self, statusUpdate):
        print 'AttenUpdate(' + str(statusUpdate) + ')'  # TBD

        # Clip attenuation to attenuator min/max values
        max = 79
        if self.attenType == 'jfw50pa':
            max = 63
        level = int(statusUpdate)
        if level < 0:
            level = 0
        elif level > max:
            level = max

        self.LvlSetText.setText(str(level))
        self.AttenCheck()
        if self.attenuator:
            try:
                if self.attenType == '8310' or self.attenType == '11713c':
                    self.attenuator.set(channel=1, value=level)
                    try:
                        self.attenuator.set(channel=2, value=level)
                    except:
                        pass
                elif self.attenType == '11713a' or self.attenType == 'j7211':
                    self.attenuator.set(level)
                elif self.attenType == 'jfw50pa':
                    self.attenuator.set(channel=1, value=level)
                    self.attenuator.set(channel=2, value=level)
                    self.attenuator.set(channel=3, value=level)
                    self.attenuator.set(channel=4, value=level)
                elif self.attenType == 'rc4dat':
                    self.attenuator.set(1, level)
                    self.attenuator.set(2, level)
                    self.attenuator.set(3, level)
                    self.attenuator.set(4, level)
                    self.attenuator.Flush()
            except Exception as e:
                print 'AttenUpdate: Caught exception: ' + str(e.__class__) + ': ' + str(e)
                traceback.print_exc()

                # Close attenuator connection
                try:
                    self.attenuator.Close()
                except Exception as e:
                    print 'AttenUpdate: error closing attenuator connection: ' + str(e)
                    traceback.print_exc()
                finally:
                    self.attenuator = None
        else:
            print 'AttenUpdate: No attenuator connection!!!'

    @pyqtSlot(QString)
    def antUpdate(self, statusUpdate):
        try:
            self.AntSelCombo.setCurrentIndex(int(statusUpdate))
        except (ValueError, AttributeError):
            pass

    @pyqtSlot(QString)
    def chanbgUpdate(self, statusUpdate):
        try:
            searchfor = str(statusUpdate)
            for i in range(self.Router2_4Combo.count()):
                itemtext = str(self.Router2_4Combo.itemText(i))
                if itemtext.find(searchfor) is not -1:
                    self.Router2_4Combo.setCurrentIndex(i)
                    self.channel = searchfor
                    break
        except (ValueError, AttributeError):
            pass

    @pyqtSlot(QString)
    def chanaUpdate(self, statusUpdate):
        try:
            searchfor = str(statusUpdate)
            for i in range(self.Router5Combo.count()):
                itemtext = str(self.Router5Combo.itemText(i))
                if itemtext.find(searchfor) is not -1:
                    self.Router5Combo.setCurrentIndex(i)
                    self.channel = searchfor
                    break
        except (ValueError, AttributeError):
            pass

    @pyqtSlot()
    def on_StopBtn_clicked(self):
        try:
            self.StatusText.setText("Stopping Testing")
            self.Status2Text.setText("0")
            self.aw.qmc.stopThread()
            self.StatusText.setText("Idle")
            self.Status2Text.setText("0")
        except:
            pass
        try:
            if self.mantp.isRunning():
                self.mantp.stop()
                self.mantp.wait()
                self.StatusText.setText("Idle")
                self.Status2Text.setText("0")
        except:
            pass
        try:
            self.StatusText.setText("Stopping Testing")
            if self.timing.isRunning():
                self.timing.terminate()
                self.timing.wait()
            self.StatusText.setText("Idle")
            self.Status2Text.setText("0")
        except:
            pass

    ###---End      STATUS UPDATES Definitions            ####
    #########################################################

    #############################################################
    ###Power Strip Control Widget Definitions  <==Begin==>    ###

    @pyqtSlot(QString)
    def on_APCComText_textChanged(self):
        enable = re.search('COM([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])$', self.APCComText.text())
        if enable is not None:
            enable = 1
        else:
            enable = re.search('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', self.APCComText.text())
            if enable is not None:
                enable = 1
            else:
                enable = 0
        if enable == 1:
            self.savedJsonDat['rightpanel']['groupBox_5']['APCCmdCombo'] = self.APCCmdCombo.currentIndex()
            self.savedJsonDat['rightpanel']['groupBox_5']['APCComText'] = self.APCComText.text()
            self.savedJsonDat['rightpanel']['groupBox_5']['OutletSelCombo'] = self.OutletSelCombo.currentIndex()
            self.saveSettings()
        self.OutletExeBtn.setEnabled(enable)
        self.time_StartBtn.setEnabled(enable)

    @pyqtSlot()
    def on_OutletExeBtn_clicked(self):
        address = str(self.APCComText.text())
        pdu = apcpdu('snmp', address)
        actualPorts = pdu.snmp().sPDUOutletConfigTableSize() + 1
        try:
            if (self.OutletSelCombo.currentIndex() + 1) > actualPorts:
                pass
            index = self.APCCmdCombo.currentIndex()
            if index == 0:
                pdu.snmp().sPDUOutletCtl(self.OutletSelCombo.currentIndex() + 1, 3)  # Reset
            elif index == 1:
                pdu.snmp().sPDUOutletCtl(self.OutletSelCombo.currentIndex() + 1, 7)  # Reset delayed
            elif index == 2:
                pdu.snmp().sPDUOutletCtl(self.OutletSelCombo.currentIndex() + 1, 2)  # Turn Port Off
            elif index == 3:
                pdu.snmp().sPDUOutletCtl(self.OutletSelCombo.currentIndex() + 1, 1)  # Turn Port On
        except:
            pass

    ###---End Power Strip Control Widget Definitions     ####
    #########################################################

    ######################################################################
    ###       Throughput control IPERF and HPTCP tabs  <==Begin==>      ###

    @pyqtSlot()
    def on_iperf_testBtn_clicked(self):
        try:
            if self.checkvalidIP():
                self.SendCmd("iperf3 -s &", 'lin', self.PRINT)
                time.sleep(.5)
                self.mainstatUpdate('Sending Command')
                QApplication.processEvents()
                cmd = subprocess.Popen('c:\iperf\iperf3.exe -c ' + str(self.IPaddrText.text()) + ' -i 1 -t 1 -f \'m\'' \
                                       , stdout=subprocess.PIPE)  # , creationflags=CREATE_NEW_CONSOLE)
                try:
                    for line in cmd.stdout:
                        form.textBrowser.append(unicode(line))
                except Exception as e:
                    print line
                    print 'WirelessTesting.on_iperf_testBtn_clicked: unicode exception: ' + str(e)
                    traceback.print_exc()
                self.mainstatUpdate('Idle')
        except:
            pass

    @pyqtSlot()
    def on_hptcp_testBtn_clicked(self):
        try:
            if self.checkvalidIP():
                self.mainstatUpdate('Sending Command')
                QApplication.processEvents()
                hpTCP.hpTcpTestTngCmd(['/f', 'MBIT', '/i', '1', '/e', '10', '/t', '192.168.2.2'])

                # cmd = subprocess.Popen('C:\hptcptest.exe /t '+ str(self.IPaddrText.text()) +' /I 1 /N 1' \
                # ,stdout=subprocess.PIPE)#, creationflags=CREATE_NEW_CONSOLE)
                # for line in cmd.stdout:
                #    form.textBrowser.append(unicode(line))
                # self.mainstatUpdate('Idle')
        except:
            pass

    @pyqtSlot()
    def on_runIperf_clicked(self):
        try:
            if self.checkvalidIP():
                if self.mantp.isRunning():
                    self.mantp.stop()
                    self.mantp.wait()
                self.mantp.initialize( \
                    str(self.SOLComText.text()), \
                    str(self.LinuxComText.text()), \
                    str(self.IPaddrText.text()), \
                    True, \
                    self.checkBox.isChecked(), \
                    str(self.iperf_time2t.text()), \
                    str(self.iperf_bw.text()), \
                    str(self.iperf_interval.text()), \
                    str(self.hptcp_port.text()), \
                    str(self.hptcp_iter.text()), \
                    str(self.hptcp_report.text()))
                self.mantp.start()
        except(ValueError):
            pass

    @pyqtSlot()
    def on_runhptcp_clicked(self):
        try:
            if self.checkvalidIP():
                if self.mantp.isRunning():
                    self.mantp.stop()
                    self.mantp.wait()
                self.mantp.initialize( \
                    str(self.SOLComText.text()), \
                    str(self.LinuxComText.text()), \
                    str(self.IPaddrText.text()), \
                    False, \
                    self.checkBox.isChecked(), \
                    str(self.iperf_time2t.text()), \
                    str(self.iperf_bw.text()), \
                    str(self.iperf_interval.text()), \
                    str(self.hptcp_port.text()), \
                    str(self.hptcp_iter.text()), \
                    str(self.hptcp_report.text()))

                self.mantp.start()
        except(ValueError):
            pass

    def stophptcp(self, end):
        if end:
            try:
                if self.mantp.isRunning():
                    self.mantp.stop()
                    self.mantp.wait()
            except:
                pass

    def hptcpIterupdate(self, Iterations):
        self.hptcp_iter.setText(str(Iterations))

    def hptcptimeupdate(self, sampTime):
        self.hptcp_report.setText(str(sampTime))

    def checkvalidIP(self):
        ip = str(self.IPaddrText.text())
        valid = re.search('\d+\.\d+\.\d+\.\d+', ip)
        if valid:
            self.savedJsonDat['leftpanel']['PrinterComBox']['IPaddrText'] = ip
            return True
        else:
            self.mainstatUpdate('Invalid IP')
            return False

    ###---   End Throughput control IPERF and HPTCP tabs               ####
    #######################################################################

    #############################################################
    ### AutoNF Tab Main GUI definitions        <==Begin==>    ###

    def getSelectedNfChannels(self):
        selected_channels = []
        if self.radio5GHz.isChecked():
            for item in self.NF_5SelList.selectedItems():
                selected_channels.append(str(item.text()))
            # If no channel selected, default to first channel
            if len(selected_channels) == 0:
                selected_channels = [str(self.NF_5SelList.item(0).text())]
        else:
            for item in self.NF_24SelList.selectedItems():
                selected_channels.append(str(item.text()))
            # If no channel selected, default to first channel
            if len(selected_channels) == 0:
                selected_channels = [str(self.NF_24SelList.item(0).text())]
        return selected_channels

    @pyqtSlot()
    def on_NF_StartBtn_clicked(self):
        if self.Iperf3checkBox.isChecked():
            filename = os.getcwd() + "\\iperf.log"
        else:
            filename = os.getcwd() + "\\hpTcp.log"
        print filename
        open(filename, 'w').close()
        chanlist = self.getSelectedNfChannels()
        if self.ModeCombo.currentIndex() < 0:
            self.ModeCombo.setCurrentIndex(0)
        if self.ChWidthCombo.currentIndex() < 0:
            self.ChWidthCombo.setCurrentIndex(0)

        # Initiate AutoNFGraph object to collect and graph data
        # AutoNFGraph takes 16 parameters
        parameters = [ \
            str(self.SOLComText.text()), \
            str(self.RouterSelCombo.currentText()), \
            str(self.LinuxComText.text()), \
            chanlist, \
            udws_commands, \
            self.NFDataCheckBox.isChecked(), \
            self.Iperf3checkBox.isChecked(), \
            str(self.NF_NumSampText.text()), \
            self.MIMOCheckbox.isChecked(), \
            self.radio5GHz.isChecked(), \
            self.WifiDirectCheckbox.isChecked(), \
            self.RouterSelTCPIPCheck.isChecked(), \
            str(self.__RouterTypeCombo), \
            str(self.__SecuritySelCombo), \
            str(self.ModeCombo.currentText()), \
            str(self.ChWidthCombo.currentText())]
        self.aw = GraphWToolbar('autoNF', parameters)
        self.aw.show()

    @pyqtSlot()
    def on_NF_createTitleBtn_clicked(self):
        self.createTitle('NF')

    @pyqtSlot()
    def on_NF_LoadBtn_clicked(self):
        fname = QFileDialog.getOpenFileName(self, 'Open File')
        try:
            with open(fname) as datfile:
                data = json.load(datfile)
                avg = {}
                std = {}
                for key in data:
                    tempa = np.mean(data[key])
                    tempa = "{0:.2f}".format(tempa)
                    temp = {key: tempa}
                    avg.update(temp)
                    temps = np.std(data[key])
                    temps = "{0:.2f}".format(temps)
                    temp = {key: temps}
                    std.update(temp)
                for key in data:
                    plt.plot(data[key],
                             label="Avg:  " + str(avg[key]) + "  Std:  " + str(std[key]) + "  " + str(key)[6:])
                    plt.plot(data[key], 'b^')
                    plt.legend(loc=1)

                plt.ylim(-100, -65)
                plt.grid(True)
                plt.xlabel('pts', size=22)
                plt.ylabel('Noise (dBm)', size=22)
                plt.title("AutoNF from saved file", size=28)
                plt.show()
        except(IOError, UnboundLocalError):
            pass

    @pyqtSlot()
    def on_NF_PrnChans_clicked(self):
        if self.RouterSelTCPIPCheck.isChecked():
            print 'on_NF_PrnChans_clicked()'  # TBD
            self.dispRouterProp()
        else:
            whichrout = self.SendCmd('wl_iocmd ver', 'rout', self.NOPRINT)
            ans = re.search('version', whichrout)
            if ans:
                cmd24 = 'wl_iocmd -i eth1 channels'
                self.SendCmd(cmd24, 'rout', self.PRINT)
                cmd5 = 'wl_iocmd -i eth2 channels'
                self.SendCmd(cmd5, 'rout', self.PRINT)
            else:
                cmd24 = 'wl channels'
                self.SendCmd(cmd24, 'rout', self.PRINT)
                cmd5 = 'wl -i eth2 channels'
                self.SendCmd(cmd5, 'rout', self.PRINT)

    @pyqtSlot()
    def on_NF_MonitorBtn_clicked(self):
        self.StatusText.setText("Monitoring Noise")
        parameters = [ \
            str(self.SOLComText.text()), \
            str(self.RouterSelCombo.currentText()), \
            str(self.LinuxComText.text()), \
            udws_commands, \
            self.NFDataCheckBox.isChecked(), \
            self.Iperf3checkBox.isChecked(), \
            self.NF_SpeedSpin.value()]
        # initiate class to collect and graph data
        self.aw = GraphWToolbar('NFmonitor', parameters)
        self.aw.show()

    @pyqtSlot(int)
    def on_NF_SpeedSpin_valueChanged(self):
        try:
            self.aw.qmc.speedUpdate(self.NF_SpeedSpin.value())
        except:
            pass

    #    def NFfinished(self, completed):
    #        #plt.ion()
    #        #self.autoNF.stop()
    #        #self.autoNF.wait()
    #        #self.autoNF.quit()
    #        #self.autoNF.wait()
    #        #self.autoNF.terminate()
    #        #time.sleep(4)
    #        print "Finished!!!"

    ###---End AutoNF Tab Main GUI definitions            ####
    #########################################################

    #############################################################
    ###    OTA Tab Main GUI definitions        <==Begin==>    ###

    @pyqtSlot()
    def on_OTA_Start_clicked(self):
        if not self.dispRouterDone:
            self.dispRouterProp()
        self.OTA_RSSIList.clear()
        self.OTA_TPList.clear()
        self.OTA_AttenlvlDisp.clear()
        self.NoiseText.setText('---')
        self.RSSIText.setText('---')

        # initiate class to collect and graph data for each channel
        self.direct = self.WifiDirectCheckbox.isChecked()
        self.chanlist = self.getSelectedOtaChannels()
        self.antlist = self.getSelectedOtaAntennas()
        if self.ModeCombo.currentIndex() < 0:
            self.ModeCombo.setCurrentIndex(0)
        if self.ChWidthCombo.currentIndex() < 0:
            self.ChWidthCombo.setCurrentIndex(0)

        # Create unique directory to save data and graph
        self.title = str(form.OTA_Title.text())
        if not self.title:
            self.title = 'OTA'
        self.logDir = tempfile.mkdtemp(suffix='', prefix=self.title + '_', dir=os.getcwd())
        print 'on_OTA_Start_clicked: logDir=[' + self.logDir + ']'

        antenna = None
        if self.antlist:
            self.antindex = 0
            while self.antindex < len(self.antlist):
                antenna = self.antlist[self.antindex]
                if self.changeAntenna(antenna) == antenna:
                    break
                print 'on_OTA_Start_clicked: changeAntenna(' + antenna + ') failed!'
                self.antindex += 1
                if self.antindex >= len(self.antlist):
                    print 'ERROR: Could not switch antennas!'
                    return

        if self.chanlist:
            solcom = str(self.SOLComText.text())
            routcom = str(self.RouterSelCombo.currentText())
            tcpip = self.RouterSelTCPIPCheck.isChecked()
            router = str(self.__RouterTypeCombo)
            security = str(self.__SecuritySelCombo)
            mode = str(self.ModeCombo.currentText())
            chwidth = str(self.ChWidthCombo.currentText())
            self.chindex = 0
            while self.chindex < len(self.chanlist):
                channel = self.chanlist[self.chindex]
                if self.changeChannel(solcom, routcom, channel, udws_commands, tcpip, router, security, mode, chwidth):
                    break
                print 'on_OTA_Start_clicked: changeChannel(' + channel + ') failed!'
                self.chindex += 1
        else:
            self.otainit(None)

    def chanloop(self):
        try:
            antenna = None
            if self.antlist:
                # Switch to next antenna.
                # Switch to next channel when switching from last back to first antenna.
                antindex_save = self.antindex
                while True:
                    self.antindex = (self.antindex + 1) % len(self.antlist)
                    antenna = self.antlist[self.antindex]
                    if self.changeAntenna(antenna) == antenna:
                        break
                    print 'chanloop: changeAntenna(' + antenna + ') failed!'
                    if self.antindex == antindex_save:
                        break;
                if self.antindex > 0:
                    if self.chanlist:
                        channel = self.chanlist[self.chindex]
                    else:
                        channel = None
                    self.otainit(channel)
                    return

            if self.chanlist and (self.chindex + 1) < len(self.chanlist):
                # Switch to next channel.
                print 'Old channel[' + str(self.chindex) + ']=' + self.chanlist[self.chindex]
                self.chindex += 1
                channel = self.chanlist[self.chindex]
                print 'New channel[' + str(self.chindex) + ']=' + channel
                solcom = str(self.SOLComText.text())
                routcom = str(self.RouterSelCombo.currentText())
                tcpip = self.RouterSelTCPIPCheck.isChecked()
                router = str(self.__RouterTypeCombo)
                security = str(self.__SecuritySelCombo)
                mode = str(self.ModeCombo.currentText())
                chwidth = str(self.ChWidthCombo.currentText())
                time.sleep(5)
                self.changeChannel(solcom, routcom, channel, udws_commands, tcpip, router, security, mode, chwidth)
            else:
                print "Finished OTA"
        except:
            self.antlist = []
            self.chanlist = []

    @pyqtSlot(int)
    def otainit(self, channel):
        # Don't do OTAGraph if channel change failed!
        if channel and self.chanlist and int(self.chanlist[self.chindex]) != int(channel):
            print 'otainit: channel change failed. Channel ' + channel + '!=' + self.chanlist[self.chindex]
            return

        antenna = None
        if self.antlist:
            print 'otainit: channel=' + str(channel) + ' antindex=' + str(self.antindex)  # TBD
            antenna = self.antlist[self.antindex]

        attenlist = []
        if self.OTAManTestCheckBox.isChecked():
            for index in range(self.OTA_AttenList.count()):
                attenlist.append(self.OTA_AttenList.item(index))
        self.AttenCheck()

        secsPerAtten = None
        s = str(self.OTA_SecsPerAtten.text())
        if s:
            secsPerAtten = int(s)
        if secsPerAtten == 0:
            secsPerAtten = None

        # OTAGraph takes 18 parameters
        parameters = [
            str(self.SOLComText.text()),
            str(self.RouterSelCombo.currentText()),
            str(self.LinuxComText.text()),
            self.OTAManTestCheckBox.isChecked(),
            attenlist,
            udws_commands,
            self.Iperf3checkBox.isChecked(),
            str(self.OTA_PtsText.text()),
            self.radio5GHz.isChecked(),
            self.WifiDirectCheckbox.isChecked(),
            self.OTA_AttenGrouping.isChecked(),
            channel,
            antenna,
            self.title,
            self.logDir,
            str(self.piAddr.text()),
            secsPerAtten,
            str(self.windowTitle())]
        self.aw = GraphWToolbar('OTA', parameters)
        self.aw.show()

    def changeChannel(self, solcom, routcom, channel, commands, tcpip,
                      router, security, mode, chwidth, otacheck=True):
        result = None
        print 'changeChannel: channel=' + channel
        if self.direct:
            self.ota.initialize(
                str(self.SOLComText.text()),
                str(self.RouterSelCombo.currentText()),
                str(self.LinuxComText.text()),
                self.OTAManTestCheckBox.isChecked(),
                [],
                udws_commands,
                self.Iperf3checkBox.isChecked(),
                str(self.OTA_PtsText.text()),
                self.radio5GHz.isChecked(),
                self.direct,
                self.piAddr)
            ch = self.ota.getDirectChannel()
            if ch != channel:
                ch = self.ota.setDirectChannel(channel, 120)
            if ch == channel:
                self.otainit(channel)
                result = channel
        else:
            ssid = str(self.SSIDText.text())
            if 0 < int(channel) < 15:
                router = self.getRouter()
                if self.channelch24.isRunning():
                    self.channelch24.stop()
                    self.channelch24.wait()
                if 'Ch' in ssid:
                    self.updateSSID(ssid, channel)
                    ssid = str(self.SSIDText.text())
                    print 'changeChannel: ssid=' + ssid  # TBD
                else:
                    ssid = None
                self.channelch24.initialize( \
                    solcom, \
                    routcom, \
                    channel, \
                    commands, \
                    tcpip, \
                    router, \
                    security, \
                    mode, \
                    chwidth, \
                    otacheck, \
                    ssid)
                self.preChange()
                self.channelch24.start()
                result = channel
            elif int(channel) in [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140,
                                  149, 153, 157, 161, 184, 188, 192, 196, 200, 204, 208, 212, 216]:
                router = self.getRouter()
                if router in WirelessTesting.FiveGHzRouters:
                    if self.ModeCombo.currentIndex() < 0:
                        self.ModeCombo.setCurrentIndex(0)
                    if self.ChWidthCombo.currentIndex() < 0:
                        self.ChWidthCombo.setCurrentIndex(0)
                    if self.channelch5.isRunning():
                        self.channelch5.stop()
                        self.channelch5.wait()
                    if 'Ch' in ssid:
                        self.updateSSID(ssid, channel)
                        ssid = str(self.SSIDText.text())
                        print 'changeChannel: ssid=' + ssid  # TBD
                    else:
                        ssid = None
                    self.channelch5.initialize( \
                        solcom, \
                        routcom, \
                        channel, \
                        udws_commands, \
                        tcpip, \
                        router, \
                        security, \
                        mode, \
                        chwidth, \
                        otacheck, \
                        ssid)
                    self.preChange()
                    self.channelch5.start()
                    result = channel
                else:
                    print "%s does not support dual band" % router
            else:
                print "Invalid channel %s" % channel
        return result

    def changeAntenna(self, antenna):
        cmd = None
        result = None
        print 'changeAntenna(' + antenna + ')'
        self.emit(SIGNAL("antUpdate(QString)"), antenna)
        if antenna == '1':
            self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 1")
            cmd = udws_commands['antenna_1']
        elif antenna == '2':
            self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 2")
            cmd = udws_commands['antenna_2']
        else:  # antenna == 'All'
            self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna diversity")
            cmd = udws_commands['antenna_all']
        if cmd:
            # Select antenna
            self.SendCmd(cmd, 'sol', self.PRINT)
            time.sleep(0.5)
            if self.PrinterTypeCombo.currentIndex() == PrinterTypeStingray:
                self.SendCmd("echo trxpath 0 > /proc/net/rtl8821ds/wlan0/odm/cmd", 'lin', self.PRINT)
            time.sleep(1)  # wait for antenna change

            # Verify that correct antenna was selected
            expected = cmd[-2]
            cmd = cmd[:-3] + cmd[-1]
            cmd = cmd.replace('set', 'get')
            response = self.SendCmd(cmd, 'sol', self.PRINT)
            if 'marvell' in cmd:
                if expected == '3':
                    expected = '65535'
                ant = re.search('Mode of Tx/Rx path:\s*(\d+)', response, re.U)
            elif 'ultra_spectra' in cmd:
                ant = re.search('Wi-Fi antdiv setting:\s*(\d)', response, re.U)
            else:
                ant = re.search('(\d)', response, re.U)
            if ant and ant.group(1):
                ant = str(ant.group(1))
                if ant == expected:
                    result = antenna
                else:
                    print 'changeAntenna: expected=[' + expected + '] got=[' + ant + ']'
            else:
                print 'changeAntenna: bad response: [' + cmd + '] -> [' + response + ']'
        return result

    @pyqtSlot()
    def on_OTA_LoadBtn_clicked(self):
        fname = QFileDialog.getOpenFileName(self, 'Open File')
        try:
            with open(fname) as datfile:
                data = json.load(datfile)
                print "Processing the file... Generating legend stats and normalized plots\n"
                for key in data:
                    rssi = data[key][0]
                    print "Channel %s\n\n" % key
                    # print "RSSI:\n\n"
                    # print rssi
                    tp = data[key][1]
                    # print "TP:\n\n"
                    # print tp

                    # pts
                    tempp = len(tp)
                    temp = {key: tempp}
                    # pts.update(temp)

                    # St Deviation
                    temps = np.std(tp)
                    temps = "{0:.2f}".format(temps)
                    temp = {key: temps}
                    # std.update(temp)

                    # Mean
                    tempa = np.mean(tp)
                    tempa = "{0:.2f}".format(tempa)
                    temp = {key: tempa}
                    # avg.update(temp)

                    # max TP
                    tempm = max(tp)
                    temp = {key: tempm}
                    # maxTP.update(temp)

                    # Rearrage points so RSSI is in order
                    print "Sorting RSSI\n\n"
                    new_rssi = np.array(rssi)
                    index = new_rssi.argsort()
                    trssi = []
                    ttp = []
                    for i in index:
                        trssi.append(rssi[i])
                        ttp.append(tp[i])

                    rssi = trssi
                    tp = ttp

                    # Normalizing throuput for a particular rssi
                    print "Normalizing\n\n"
                    ntp = []
                    nrssi = []
                    atp = tp[0]
                    for i in range(len(rssi) - 1):
                        if rssi[i] == rssi[i + 1]:
                            atp += (tp[i] + tp[i + 1]) / 3.00
                        else:
                            atp = tp[i]
                            ntp.append(atp)
                            nrssi.append(rssi[i])
                            atp = tp[i + 1]

                    tp = ntp
                    rssi = nrssi

                    # Update TP and RSSI array with 1st and last point
                    # last point
                    rssi = [min(rssi)] + rssi
                    tp = [0] + tp

                    # first point
                    # rssi.append(-20)
                    # tp.append(max(tp))

                    plt.plot(rssi, tp, label="\n Channel " + str(key) + "\n Max TP:"
                                             + str(tempm) + " Mbps" + "\n Cutoff: " + str(min(rssi)) + " dBm"
                                             + "\n Pts: " + str(tempp) + "\n Avg:  " + str(tempa) + " Mbps"
                                             + "\n std:  " + str(temps))
                    plt.legend(loc=1)

                # plt.ylim(-100, -65)
                plt.grid(True)
                plt.xlabel('RSSI (dBm)', size=22)
                plt.ylabel('TP (Mbps)', size=22)
                plt.title("Normalized OTA from saved file", size=28)
                plt.gca().invert_xaxis()
                plt.show()
        except(IOError, UnboundLocalError):
            pass

    @pyqtSlot()
    def on_AttenPresentCheckbox_clicked(self):
        if self.AttenPresentCheckbox.isChecked():
            self.OTA_Start.setEnabled(True)
        else:
            self.OTA_Start.setEnabled(False)

    @pyqtSlot(QString)
    def RSSIupdate(self, rssi):
        self.OTA_RSSIList.insertItem(0, rssi)

    @pyqtSlot(QString)
    def TPupdate(self, rate):
        self.OTA_TPList.insertItem(0, rate)

    @pyqtSlot(QString)
    def AttenListUpdate(self, atten):
        self.OTA_AttenlvlDisp.insertItem(0, atten)

    def RSSISyncScroll(self):
        sliderValue = self.tpVertBar.value()
        self.rssiVertBar.setValue(sliderValue)
        self.attenDispVertBar.setValue(sliderValue)

    def TPSyncScroll(self):
        sliderValue = self.rssiVertBar.value()
        self.tpVertBar.setValue(sliderValue)
        self.attenDispVertBar.setValue(sliderValue)

    def AttenSyncScroll(self):
        sliderValue = self.attenDispVertBar.value()
        self.tpVertBar.setValue(sliderValue)
        self.rssiVertBar.setValue(sliderValue)

    @pyqtSlot(QString)
    def on_OTA_Min_textChanged(self):
        enable = re.search('^([0-9]|[1-7][0-9])$', self.OTA_Min.text())
        if enable is not None:
            enable = 1
        else:
            enable = 0
        self.OTA_ManualFillBtn.setEnabled(enable)

    @pyqtSlot(QString)
    def on_OTA_Max_textChanged(self):
        enable = re.search('^([0-9]|[1-7][0-9])$', self.OTA_Max.text())
        if enable is not None:
            enable = 1
        else:
            enable = 0
        self.OTA_ManualFillBtn.setEnabled(enable)

    @pyqtSlot()
    def on_OTA_ManualFillBtn_clicked(self):
        self.OTA_AttenList.clear()
        mult = int(self.OTA_StepIncrCombo.currentText())
        Min = int(self.OTA_Min.text())
        Max = int(self.OTA_Max.text())
        item = QListWidgetItem(str(Min))
        item.setFlags(QtCore.Qt.ItemIsSelectable \
                      | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled \
                      | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.OTA_AttenList.addItem(item)
        while Min + mult < Max:
            Min = Min + mult
            item = QListWidgetItem(str(Min))
            item.setFlags(QtCore.Qt.ItemIsSelectable \
                          | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled \
                          | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            self.OTA_AttenList.addItem(item)
        item = QListWidgetItem(str(Max))
        item.setFlags(QtCore.Qt.ItemIsSelectable \
                      | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled \
                      | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.OTA_AttenList.addItem(item)

    @pyqtSlot()
    def on_OTA_AddBtn_clicked(self):
        row = self.OTA_AttenList.currentRow() + 1
        item = QListWidgetItem(self.OTA_Add.text())
        item.setFlags(QtCore.Qt.ItemIsSelectable | \
                      QtCore.Qt.ItemIsEditable | \
                      QtCore.Qt.ItemIsDragEnabled | \
                      QtCore.Qt.ItemIsUserCheckable | \
                      QtCore.Qt.ItemIsEnabled)
        self.OTA_AttenList.insertItem(row, item)
        self.OTA_AttenList.setCurrentRow(row)
        val = int(self.OTA_Add.text())
        inc = int(self.OTA_StepIncrCombo.currentText())
        self.OTA_Add.setText(str(val + inc))

    @pyqtSlot()
    def on_OTA_RemoveBtn_clicked(self):
        self.OTA_AttenList.takeItem(self.OTA_AttenList.currentRow())

    @pyqtSlot()
    def on_OTA_SaveBtn_clicked(self):
        saveDiag = QFileDialog.getSaveFileName(self, 'Save File')
        text = 'RSSI\tTP (Mbps)\n'
        for i in range(self.OTA_RSSIList.count()):
            text = text + str(self.OTA_RSSIList.item(i).text()) + '\t' + str(self.OTA_TPList.item(i).text()) + '\n'
        try:
            file = open(saveDiag, 'w')
            file.write(text)
            file.close()
        except(IOError, UnboundLocalError):
            pass

    @pyqtSlot()
    def on_OTA_createTitleBtn_clicked(self):
        self.createTitle('OTA')

    ###---End    OTA Tab Main GUI definitions            ####
    #########################################################

    #############################################################
    ###   Timing Tab Main GUI definitions      <==Begin==>    ###

    @pyqtSlot()
    def on_time_StartBtn_clicked(self):
        self.createTitle('time')
        self.time_Table.clearContents()
        if self.timing.isRunning():
            self.timing.stop()
            self.timing.wait()
        self.AttenCheck()
        self.timing.initialize(str(self.SOLComText.text()), \
                               str(self.RouterSelCombo.currentText()), \
                               str(self.LinuxComText.text()), \
                               udws_commands, \
                               self.time_50chk.isChecked(), \
                               self.time_80chk.isChecked(), \
                               self.time_findAPchk.isChecked(), \
                               self.time_connAPchk.isChecked(), \
                               self.time_connAfterIntrchk.isChecked(), \
                               self.time_connFromBootchk.isChecked(), \
                               self.radio5GHz.isChecked(), \
                               self.WifiDirectCheckbox.isChecked(), \
                               str(self.APCComText.text()), \
                               self.OutletSelCombo.currentIndex() + 1, \
                               str(self.SSIDText.text()), \
                               str(self.time_sampNum.text()), \
                               int(self.LvlSetText.text()))
        self.timing.start()

    def keyPressEvent(self, e):
        """Enable copying of timing table multiple values"""
        if (e.modifiers() & QtCore.Qt.ControlModifier):
            selected = self.time_Table.selectedRanges()

            if e.key() == QtCore.Qt.Key_C:  # copy
                s = ""
                # s = '\t'+"\t".join([str(self.time_Table.horizontalHeaderItem(i).text()) for i in xrange(selected[0].leftColumn(), selected[0].rightColumn()+1)])
                # s = s + '\n'

                for r in xrange(selected[0].topRow(), selected[0].bottomRow() + 1):
                    # s += str(self.time_Table.verticalHeaderItem(r).text()) + '\t'
                    for c in xrange(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        try:
                            s += str(self.time_Table.item(r, c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n"  # eliminate last '\t'
                self.clip.setText(s)

    def populateTable(self, timeinfo):
        # print timeinfo
        if self.time_Table.item(0, 1) is not None:
            secndpass = True
        else:
            secndpass = False
        for row, test in enumerate(timeinfo):
            for column, info in enumerate(test):
                if len(test) == 4:
                    column += 1
                item = QtGui.QTableWidgetItem(str('{:.2f}'.format(info)))
                if secndpass:
                    self.time_Table.setItem(row * 2 + 1, column, item)
                else:
                    self.time_Table.setItem(row * 2, column, item)

    ###---End    Timing Tab Main GUI definitions         ####
    #########################################################

    ##############################################################
    ###   Antenna Tab Main GUI definitions      <==Begin==>    ###

    @pyqtSlot()
    def on_ANT_connectTTbtn_clicked(self):
        try:
            self.rm = visa.ResourceManager()
            device = GpibDevice.get_devices()
            dev = device['emco1060'][1]
            bd = device['emco1060'][0]
            self.tt = Attenuator.connect('Emco1060', board=bd, device=dev)
            self.ANT_TurntableStatus.setStyleSheet("background-color: rgb(0, 255, 0);")
            self.ANT_TurntableStatus.setText("0")
        except(OSError):
            self.ANT_TurntableStatus.setStyleSheet("background-color: rgb(255, 0, 0);")
            self.ANT_TurntableStatus.setText("Status")
            self.StatusText.setText("GPIB Error")
            self.Status2Text.setText("GPIB not Present")
            self.AttenPresentCheckbox.setChecked(False)
            QApplication.processEvents()
            time.sleep(2)
            pass
        # if str(self.ANT_TurntableStatus.text()) in 'Status':
        #    self.ANT_TurntableStatus.setStyleSheet("background-color: rgb(0, 255, 0);")
        #    self.ANT_TurntableStatus.setText("0")
        # else:
        #    self.ANT_TurntableStatus.setStyleSheet("background-color: rgb(255, 0, 0);")
        #    self.ANT_TurntableStatus.setText("Status")

    @pyqtSlot()
    def on_ANT_manGoBtn_clicked(self):
        if self.ANT_mansingleSet.isChecked():
            try:
                degree = int(self.ANT_mandegree.text())
                self.tt.set(degree)
            except:
                self.StatusText.setText("Could not set turntable")
                time.sleep(2)
        elif self.ANT_manSweep.isChecked():
            if self.apattern.isRunning():
                self.apattern.stop()
                self.apattern.wait()
            self.apattern.initialize( \
                solcom=str(self.SOLComText.text()), \
                routcom=str(self.RouterSelCombo.currentText()), \
                lincom=str(self.LinuxComText.text()), \
                commands=udws_commands, \
                iperf=self.Iperf3checkBox.isChecked(), \
                fiveGHz=self.radio5GHz.isChecked(), \
                direct=self.WifiDirectCheckbox.isChecked(), \
                tTable=self.tt, \
                autorun=False,
                manStart=int(self.ANT_manSweepStart.text()), \
                manStop=int(self.ANT_manSweepEnd.text()), \
                manSweepStep=int(self.ANT_manSweepStep.text()), \
                manSweepTime=int(self.ANT_manSweepTime.text()))
            self.apattern.start()

        # ANT_manSweepStart
        # ANT_manSweepEnd
        # ANT_manSweepStep
        # ANT_manSweepTime

    @pyqtSlot()
    def on_ANT_StartBtn_clicked(self):
        if self.apattern.isRunning():
            self.apattern.stop()
            self.apattern.wait()
        self.AttenCheck()
        self.apattern.initialize( \
            solcom=str(self.SOLComText.text()), \
            routcom=str(self.RouterSelCombo.currentText()), \
            lincom=str(self.LinuxComText.text()), \
            commands=udws_commands, \
            iperf=self.Iperf3checkBox.isChecked(), \
            fiveGHz=self.radio5GHz.isChecked(), \
            direct=self.WifiDirectCheckbox.isChecked(), \
            tTable=self.tt, \
            autorun=True, \
            autoStartdeg=int(self.ANT_autoDegStart.text()), \
            autoStopdeg=int(self.ANT_autoDegEnd.text()), \
            autoStepdeg=int(self.ANT_autoDegStep.text()), \
            autoStartAtt=int(self.ANT_autoAttStart.text()), \
            autoStopAtt=int(self.ANT_autoAttEnd.text()), \
            autoStepAtt=int(self.ANT_autoAttStep.text()))
        self.apattern.start()
        # ANT_autoDegStart
        # ANT_autoDegEnd
        # ANT_autoDegStep
        # ANT_autoAttStart
        # ANT_autoAttEnd
        # ANT_autoAttStep


###---End    Antenna Tab Main GUI definitions         ####
##########################################################


###############################################################################################
#   _     _     _     _     _     _     _     _       _     _     _     _     _     _     _   #
#  / \   / \   / \   / \   / \   / \   / \   / \     / \   / \   / \   / \   / \   / \   / \  #
# ( G ) ( r ) ( a ) ( p ) ( h ) ( i ) ( n ) ( g )   ( C ) ( l ) ( a ) ( s ) ( s ) ( e ) ( s ) #
#  \_/   \_/   \_/   \_/   \_/   \_/   \_/   \_/     \_/   \_/   \_/   \_/   \_/   \_/   \_/  #
###############################################################################################

class GraphWToolbar(QMainWindow):
    """Example main window"""

    def __init__(self, select, parameters):
        # initialization of Qt MainWindow widget
        QMainWindow.__init__(self)
        # set window title
        if select == 'autoNF':
            self.setWindowTitle("AutoNF Plot")
        elif select == 'NFmonitor':
            self.setWindowTitle("AutoNF Monitor Live Plot")
        elif select == 'OTA':
            self.setWindowTitle("Throughput Versus Attenuation Graph")
        # instantiate a widget, it will be the main one
        self.main_widget = QWidget(self)
        # create a vertical box layout widget
        vbl = QVBoxLayout(self.main_widget)
        # instantiate our Matplotlib canvas widget and the navigation toolbar
        if select == 'autoNF':
            self.qmc = AutoNFGraph(self.main_widget, parameters)
            ntb = NavigationToolbar(self.qmc, self.main_widget)
        elif select == 'NFmonitor':
            self.qmc = NFmonitorGraph(self.main_widget, parameters)
            ntb = NavigationToolbar(self.qmc, self.main_widget)
        elif select == 'OTA':
            self.qmc = OTAGraph(self.main_widget, parameters)
            ntb = NavigationToolbar(self.qmc, self.main_widget)
        # pack these widget into the vertical box
        vbl.addWidget(self.qmc)
        vbl.addWidget(ntb)

        # set the focus on the main widget
        self.main_widget.setFocus()
        # set the central widget of MainWindow to main_widget
        self.setCentralWidget(self.main_widget)

        #######################################
        #      ___       __       _  ______   #
        #     / _ |__ __/ /____  / |/ / __/   #
        #    / __ / // / __/ _ \/    / _/     #
        #   /_/ |_\_,_/\__/\___/_/|_/_/       #     Begin


###########################################################


class AutoNFGraph(FigureCanvas):
    """Matplotlib Figure widget to display CPU utilization"""

    def __init__(self, parent, parameters):
        # first image setup
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        # initialization of the canvas
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        # notify the system of updated policy
        FigureCanvas.updateGeometry(self)
        self.autoNF = autoNF.AutoNF(self)

        ########################################################################
        ## autoNF connect declarations ##
        self.connect(self.autoNF, SIGNAL("mainstatUpdate(QString)"),
                     form.mainstatUpdate)
        self.connect(self.autoNF, SIGNAL("auxstatUpdate(QString)"),
                     form.auxstatUpdate)
        self.connect(self.autoNF, SIGNAL("logUpdate(QString)"),
                     form.logUpdate)
        self.connect(self.autoNF, SIGNAL("IPUpdate(QString)"),
                     form.IPUpdate)
        self.connect(self.autoNF, SIGNAL("chanbgUpdate(QString)"),
                     form.chanbgUpdate)
        self.connect(self.autoNF, SIGNAL("antUpdate(QString)"),
                     form.antUpdate)
        self.connect(self.autoNF, SIGNAL("starthptcp(QString)"),
                     form.on_runhptcp_clicked)
        self.connect(self.autoNF, SIGNAL("hptcpIter(int)"),
                     form.hptcpIterupdate)
        self.connect(self.autoNF, SIGNAL("hptcptime(int)"),
                     form.hptcptimeupdate)
        self.connect(self.autoNF, SIGNAL("stoptcp(bool)"),
                     form.stophptcp)
        self.connect(self.autoNF, SIGNAL("finished(bool)"),
                     self.finished_NF, Qt.AutoConnection)
        self.connect(self.autoNF, SIGNAL("time(QString)"),
                     self.pointTime_NF)
        self.autoNF.noiseFList.connect(self.graphNF, Qt.AutoConnection)
        self.autoNF.rssiList.connect(self.updateRSSI, Qt.AutoConnection)
        # self.connect(self.autoNF, SIGNAL("finished(bool)"),
        #             self.NFfinished, Qt.AutoConnection)
        # self.connect(self.autoNF, SIGNAL("finished(bool)"),
        #             self.on_Testplotbtn_clicked)
        ########################################################################
        # set specific limits for X and Y axes
        # self.ax.set_xlim(0, 30)
        if len(parameters) != 18:
            raise ValueError('AutoNFGraph parameters list must have 16 parameters')
        self.solcom = parameters[0]
        self.routcom = parameters[1]
        self.lincom = parameters[2]
        self.channel_list = parameters[3]
        self.commands = parameters[4]
        self.rundata = parameters[5]
        self.iperf = parameters[6]
        self.samples = parameters[7]
        self.mimo = parameters[8]
        self.fiveGHz = parameters[9]
        self.wifiD = parameters[10]
        self.tcpip = parameters[11]
        self.router = parameters[12]
        self.security = parameters[13]
        self.mode = parameters[14]
        self.chwidth = parameters[15]
        self.chanplot = self.channel_list[:]

        ml = MultipleLocator(1)
        self.ax.set_xlabel('pts', size=22)
        self.ax.set_ylabel('NF (dBm)', size=22)
        self.ax.yaxis.set_minor_locator(ml)
        self.ax.set_xlim(0, int(self.samples))
        self.ax.set_ylim(-100, -65)
        self.ax.grid(True)
        # and disable figure-wide autoscale
        self.ax.set_autoscale_on(False)
        self.ax.set_title(str(form.NF_TitleText.text()), size=24)
        # generates first "empty" plots
        self.dtbegin = time.strftime("%b %d %Y %H:%M:%S")
        self.tpp = 0
        self.startTime = 0
        self.plots = []
        self.rssilist = []
        self.chPltIndex = range(len(self.chanplot))
        self.ant = 0
        for channel in self.channel_list:
            self.plots.append(channelplotinfo(channel, self.mimo, self.ax))

        # add legend to plot
        self.ax.legend(loc='center left', bbox_to_anchor=(1, .8), fontsize='small', borderaxespad=2)
        if self.autoNF.isRunning():
            self.autoNF.stop()
            self.autoNF.wait()
        self.autoNF.initialize(self.solcom, \
                               self.routcom, \
                               self.lincom, \
                               self.channel_list, \
                               self.commands, \
                               self.rundata, \
                               self.iperf, \
                               self.samples, \
                               self.mimo, \
                               self.fiveGHz, \
                               self.wifiD, \
                               self.tcpip, \
                               self.router, \
                               self.security, \
                               self.mode, \
                               self.chwidth)
        self.autoNF.start()

    #
    #        # force a redraw of the Figure
    #        self.fig.canvas.draw()
    #
    def pointTime_NF(self, state):
        # print '!!!!!!!!!executed!!!!!!'
        if state == 'begin':
            self.startTime = time.time()

        if state == 'end':
            self.tpp = self.tpp + (time.time() - self.startTime)

    def updateRSSI(self, rssilist):
        self.rssilist = self.rssilist + rssilist

    def graphNF(self, noiselist):
        """Matplotlib AutoNF Plot handling and calculations"""
        print "Graphing plot of antenna !!!"
        # print noiselist
        for item in self.chPltIndex:
            self.plots[item].updatedata(noiselist)
            self.ant = self.ant + 1

            if self.mimo:
                if (self.ant % 3) == 0:
                    self.chPltIndex.pop(0)
            else:
                if (self.ant % 2) == 0:
                    self.chPltIndex.pop(0)
            break

        # update lines data using the lists with new data
        self.fig.canvas.draw()

    def finished_NF(self, completed):
        """AutoNF annotate calculated results on graph and end thread"""
        self.dtend = time.strftime("%b %d %Y %H:%M:%S")
        statFormat = '{0:>20} {1:>12}\n'.format('A0', 'A1')
        time_outTotal = ""
        totalave = 0
        try:
            for item in range(len(self.chanplot)):
                totalave = totalave + self.plots[item].getNoiseAve()
                statFormat = statFormat + self.plots[item].createLegendstr()

            if self.mimo:
                totalave = totalave / (3 * len(self.channel_list))
                tpp = self.tpp / (self.samples * 3 * len(self.channel_list))
            else:
                totalave = totalave / (2 * len(self.channel_list))
                tpp = self.tpp / (int(self.samples) * 2 * len(self.channel_list))
            totalAveStr = '\n{0:>20} {1:.1f}\n'.format('Average: ', totalave)
            statFormat = statFormat + totalAveStr

            time_outTotal = 'Begin: ' + str(self.dtbegin) + '\nEnd: ' + str(self.dtend) + \
                            '\nTotal Time: ' + time.strftime("%H:%M:%S", time.gmtime(
                self.tpp)) + '\nTime Per Point: ' + '{0:.3f} sec'.format(tpp)
            # Shrink current axis by 20%

            if (len(self.rssilist) is not 0):
                time_outTotal = time_outTotal + ('\n-----------\n'
                                                 'RSSI summary\nMax: {0} dB Min: {1} dB\nAve: {2:.2f} dB  Std: {3:.2f} dB').format( \
                    max(self.rssilist), min(self.rssilist), np.mean(np.array(self.rssilist)),
                    np.std(np.array(self.rssilist)))

            if self.iperf:
                try:
                    aray = []
                    filename = os.getcwd() + '\\iperf.log'
                    with open(filename, "r") as text:
                        for line in text:
                            # print line
                            rate = re.search('(\S+)\s+Mbits/sec', line)
                            if rate:
                                if rate.group(1) is not None:
                                    aray.append(float(rate.group(1)))

                    text.close()
                    time_outTotal = time_outTotal + ('\n-----------\n'
                                                     'Iperf3.0 summary\nMax: {0:.2f} Mb/s Min: {1:.2f} Mb/s\nAve: {2:.2f} Mb/s  Std: {3:.2f} Mb/s').format( \
                        max(aray), min(aray), np.mean(np.array(aray)), np.std(np.array(aray)))

                except:
                    pass
            else:
                try:
                    aray = []
                    filename = os.getcwd() + '\\hpTcp.log'
                    with open(filename, "r") as text:
                        for line in text:
                            # print line
                            rate = re.search('(\S+)\s+MBIT/S', line)
                            if rate:
                                if rate.group(1) is not None:
                                    aray.append(float(rate.group(1)))

                    text.close()
                    time_outTotal = time_outTotal + ('\n-----------\n'
                                                     'hpTCP summary\nMax: {0:.2f} Mb/s Min: {1:.2f} Mb/s\nAve: {2:.2f} Mb/s  Std: {3:.2f} Mb/s').format( \
                        max(aray), min(aray), np.mean(np.array(aray)), np.std(np.array(aray)))

                except:
                    pass

        except(AttributeError):
            pass
        statsText = TextArea(statFormat, minimumdescent=False)
        timeText = TextArea(time_outTotal, minimumdescent=False)
        xy = (0, -95)

        timebox = AnnotationBbox(timeText, xy,
                                 xybox=(1.02, .60),
                                 xycoords='data',
                                 boxcoords=("axes fraction", "axes fraction"),
                                 box_alignment=(0., 0.5))
        # arrowprops=dict(arrowstyle="->")

        statbox = AnnotationBbox(statsText, xy,
                                 xybox=(1.02, .35),
                                 xycoords='data',
                                 boxcoords=("axes fraction", "axes fraction"),
                                 box_alignment=(0., 0.5))
        # arrowprops=dict(arrowstyle="->")
        self.ax.add_artist(timebox)
        self.ax.add_artist(statbox)
        box = self.ax.get_position()
        self.ax.set_position([box.x0 * .5, box.y0, box.width, box.height])
        ml = MultipleLocator(1)
        self.ax.yaxis.set_minor_locator(ml)
        self.fig.canvas.draw()
        self.autoNF.wait()
        self.autoNF.stop()
        # self.disconnect(self.autoNF)
        print "Finished NF!!!"

    def stopThread(self):
        self.autoNF.stop()


class channelplotinfo:
    """Class info for every channel selected by user"""

    def __init__(self, channel, mimo, axes):
        self.channel = channel.text()
        print self.channel
        self.mimo = mimo
        self.ax = axes
        self.ch_ant0_NF = []
        self.ch_ant1_NF = []
        # set color of channel
        self.chNum = int(re.sub("[^0-9]", "", str(self.channel)))
        print self.chNum
        colours = ['mediumaquamarine', 'blue', 'darkgoldenrod', 'darkorchid', 'darksalmon', 'darkorange', 'red',
                   'deepskyblue', 'crimson', 'orchid', 'darkturquoise', 'green', 'lawngreen', 'darkslategray',
                   'deeppink']
        c = colours[self.chNum % 14]

        self.chanAnt0, = self.ax.plot([], self.ch_ant0_NF, '-x', color=c, label=self.channel + '  --- ant 0')
        self.chanAnt1, = self.ax.plot([], self.ch_ant1_NF, '--o', color=c, label=self.channel + '  --- ant 1')

        if self.mimo is True:
            self.ch_ant3_NF = []
            self.chanAnt3, = self.ax.plot([], self.ch_ant3_NF, ':+', color=c, label=self.channel + '  --- ant 3')

    def savedata(self, record, gdata):
        data.update(record)
        with open('NFdata.json', 'wb') as outfile:
            json.dump(gdata, outfile)

    def updatedata(self, noiselist):
        global data
        if (len(self.ch_ant0_NF) == 0):
            self.ch_ant0_NF.extend(noiselist)
            self.chanAnt0.set_data(range(len(self.ch_ant0_NF)), self.ch_ant0_NF)
            # Saketh edits   Saving Data
            newRecord = {str(self.chanAnt0): self.ch_ant0_NF}
            self.savedata(newRecord, data)

            ##-------------------##

            self.A0chStd = np.std(self.ch_ant0_NF)
            self.A0chAve = np.mean(self.ch_ant0_NF)
            # print '#########\n#########\nChannel 1 ant0\n Graph\n#########\n#########\n'
        elif (len(self.ch_ant1_NF) == 0):
            self.ch_ant1_NF.extend(noiselist)
            self.chanAnt1.set_data(range(len(self.ch_ant1_NF)), self.ch_ant1_NF)

            # Saketh edits  Saving Data
            newRecord = {str(self.chanAnt1): self.ch_ant1_NF}
            self.savedata(newRecord, data)
            ##-------------------##
            self.A1chStd = np.std(self.ch_ant1_NF)
            self.A1chAve = np.mean(self.ch_ant1_NF)
            # if self.mimo is False:
            # self.chanplot.pop(0)
            # print '#########\n#########\nChannel 1 ant1\n Graph\n#########\n#########\n'
        elif self.mimo is True and (len(self.ch_ant3_NF) == 0):
            self.ch_ant3_NF.extend(noiselist)
            self.chanAnt3.set_data(range(len(self.ch_ant3_NF)), self.ch_ant3_NF)

            # Saketh edits   Saving Data
            newRecord = {str(self.chanAnt3): self.ch_ant3_NF}
            self.savedata(newRecord, data)
            ##-------------------##
            self.A3chStd = np.std(self.ch_ant3_NF)
            self.A3chAve = np.mean(self.ch_ant3_NF)
            # self.chanplot.pop(0)

    def createLegendstr(self):
        """Return string with statistic info of run"""
        # chStat = '{0} {1:>12.1f} {2:>12.1f}\n{3:>14}({4:.2f}){5:>8}({6:.2f})\n'.format('ch'+str(self.chNum) ,self.A0chAve,\
        # self.A1chAve,'',self.A0chStd,'',self.A1chStd)

        chStat = '{0} {1:>{2}.1f} {3:>12.1f}\n{4:>14}({5:.2f}){6:>8}({7:.2f})\n'.format('ch' + str(self.chNum),
                                                                                        self.A0chAve, \
                                                                                        13 - len(str(self.chNum)),
                                                                                        self.A1chAve, '', self.A0chStd,
                                                                                        '', self.A1chStd)
        return chStat

    def getNoiseAve(self):
        if self.mimo:
            sumNoise = self.A0chAve + self.A1chAve + self.A3chAve
        else:
            sumNoise = self.A0chAve + self.A1chAve
        return sumNoise


########################################################### END AutoNFGraph

###############################
#       ____  _________       #
#      / __ \/_  __/ _ |      #
#     / /_/ / / / / __ |      #
#     \____/ /_/ /_/ |_|      #
#                             #            Begin
###########################################################

class OTAGraph(FigureCanvas):
    """Matplotlib Figure widget to display CPU utilization"""

    def __init__(self, parent, parameters):
        # first image setup
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        # initialization of the canvas
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        # notify the system of updated policy
        FigureCanvas.updateGeometry(self)

        self.ota = ota.Overtheair(self)
        ########################################################################
        ########################################################################
        ## ota connect declarations ##
        self.connect(self.ota, SIGNAL("mainstatUpdate(QString)"), form.mainstatUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("auxstatUpdate(QString)"), form.auxstatUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("logUpdate(QString)"), form.logUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("IPUpdate(QString)"), form.IPUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("chanbgUpdate(QString)"), form.chanbgUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("RSSIupdate(QString)"), form.RSSIupdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("TPupdate(QString)"), form.TPupdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("Attenlist(QString)"), form.AttenListUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("AttenUpdate(QString)"), form.AttenUpdate, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("finished(bool)"), self.otafinished, Qt.UniqueConnection)
        self.connect(self.ota, SIGNAL("finished(bool)"), form.chanloop, Qt.UniqueConnection)
        self.ota.rssiTPpoint.connect(self.graphOTA, Qt.UniqueConnection)
        ########################################################################
        ########################################################################

        # self.cc = cc.Clockcheck(self)

        ########################################################################
        ## Clock check connect declarations ##
        # self.connect(self.cc, SIGNAL("mainstatUpdate(QString)"),
        #             form.mainstatUpdate)
        # self.connect(self.cc, SIGNAL("clockTag(int)"),
        #             self.checkHang)
        # self.connect(self.cc, SIGNAL("clockRemain(float)"),
        #             self.clockUpdate)

        ########################################################################
        ########################################################################

        # set specific limits for X and Y axes
        # self.ax.set_xlim(0, 30)
        if len(parameters) != 18:
            raise ValueError('OTAGraph parameters list must have 18 parameters')
        self.solcom = parameters[0]
        self.routcom = parameters[1]
        self.lincom = parameters[2]
        self.manual = parameters[3]
        self.attenlist = parameters[4]
        self.commands = parameters[5]
        self.iperf = parameters[6]
        self.samples = parameters[7]
        self.fiveGHz = parameters[8]
        self.wifiD = parameters[9]
        self.ptsGrouping = parameters[10]
        self.channel = parameters[11]
        self.antenna = parameters[12]
        self.title = parameters[13]
        self.logDir = parameters[14]
        self.piAddr = parameters[15]
        self.secsPerAtten = parameters[16]
        self.windowTitle = parameters[17]
        if self.channel:
            self.title += '_CH' + str(self.channel)
        if self.antenna:
            if self.antenna == 'All':
                self.title += '_' + str(self.antenna)
            else:
                self.title += '_ANTDIV' + str(self.antenna)

        self.TParray = []
        self.RSSIary = []
        self.Attengrp = []
        self.TimeArray = []
        self.SSS_time=[]
        
        if self.secsPerAtten:
            self.ax.set_xlabel('Time (seconds)', size=22)
            if self.attenlist:
                self.ax.set_xlim(0, self.secsPerAtten * len(self.attenlist) + self.secsPerAtten)
            else:
                self.ax.set_xlim(0, self.secsPerAtten * 70)
        else:
            self.ax.set_xlabel('RSSI', size=22)
            self.ax.set_xlim(-100, -20)
            self.ax.invert_xaxis()
        self.ax.set_ylabel('Throughput (Mbits/s)', size=22)
        # self.ax.set_ylim(0, )     Set relative to the MAX TP
        self.ax.grid(True)
        self.ax.set_title(self.title, size=24)
        # and disable figure-wide autoscale
        self.ax.set_autoscale_on(False)
        self.dtbegin = time.strftime("%b %d %Y %H:%M:%S")

        if self.ota.isRunning():
            print 'stopping OTA'
            self.ota.stop()
            self.ota.wait()
            print 'OTA stopped'
        self.throughputMax = 0.0
        self.rssiMax = -999
        self.rssiMin = 999
        self.throughputMin = 0.0
        self.ota.initialize(
            self.solcom,
            self.routcom,
            self.lincom,
            self.manual,
            self.attenlist,
            self.commands,
            self.iperf,
            self.samples,
            self.fiveGHz,
            self.wifiD,
            self.piAddr,
            self.secsPerAtten,
            self.channel,
            self.antenna)
        self.ota.start()

    def clockUpdate(self, rtime):
        print "Timer still running, remaining time: %s seconds " % rtime

    def checkHang(self, tag):
        if tag == self.channel or tag == self.degree:
            if not self.ota.isStopped():
                self.ota.stop()

    def antLoop(self, mimo):
        # TODO: loop over diversity for every channel, check MIMO
        if mimo:
            ants = ('1', '2', '3')
        else:
            ants = ('1', '2')

        for ant in ants:
            if ant == '1':
                self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 1")
                self.emit(SIGNAL("antUpdate(QString)"), "1")
                self.SendCmd(self.commands['antenna_1'], 'sol', self.PRINT)
                # hkw add 20200311
                if self.PrinterTypeCombo.currentIndex() == PrinterTypeStingray:
                    self.SendCmd("echo trxpath 0 > /proc/net/rtl8821ds/wlan0/odm/cmd", 'lin', self.PRINT)

            elif ant == '2':
                self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna 2")
                self.emit(SIGNAL("antUpdate(QString)"), "2")
                self.SendCmd(self.commands['antenna_2'], 'sol', self.PRINT)
                # hkw add 20200311
                if self.PrinterTypeCombo.currentIndex() == PrinterTypeStingray:
                    self.SendCmd("echo trxpath 0 > /proc/net/rtl8821ds/wlan0/odm/cmd", 'lin', self.PRINT)

            else:
                self.emit(SIGNAL("auxstatUpdate(QString)"), "Setting printer to antenna diversity")
                self.emit(SIGNAL("antUpdate(QString)"), "All")
                self.SendCmd(self.commands['antenna_all'], 'sol', self.PRINT)
                # hkw add 20200311
                if self.PrinterTypeCombo.currentIndex() == PrinterTypeStingray:
                    self.SendCmd("echo trxpath 0 > /proc/net/rtl8821ds/wlan0/odm/cmd", 'lin', self.PRINT)

            time.sleep(6)  # wait for antenna change
            # Todo: get ota end signal to change antenna and start ota
        self.ota.start()

    def SendCmd(self, ToSend, dest, disp):
        """ Send Command to specific port

            :ToSend - Data string to send to COM port
            :dest - destination ('sol', 'lin', or 'rout')
            :disp - optional print output to textBrowser
        """
        if dest == 'sol':
            ser = serial.Serial(self.solcom, 115200, timeout=10, writeTimeout=10)
        elif dest == 'lin':
            ser = serial.Serial(self.lincom, 115200, timeout=10, writeTimeout=10)
        elif dest == 'rout':
            try:
                ser = serial.Serial(self.routcom, 115200, timeout=10, writeTimeout=10)
            except(OSError, serial.SerialException):
                print "Serial Error in diversity chg"
                return 'Error'
                pass
        else:
            return -1
        ser.isOpen()
        out = ''
        ser.write(ToSend + '\r\n')
        time.sleep(.5)
        if dest == 'sol':
            # print ser.inWaiting()
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
        # form.textBrowser.append(unicode(out))
        return out

    def plotGroup(self, xArray, yArray, groupArray, _linestyle=''):
        if _linestyle:
            self.ax.plot(xArray, yArray, linestyle=_linestyle, c='black')
        df = pd.DataFrame(dict(x=xArray, y=yArray, label=groupArray))
        groups = df.groupby('label')
        for name, group in groups:
            color = coloriter[name % len(coloriter)]
            shape = shapeiter[(name / len(coloriter)) % len(shapeiter)]
            self.ax.plot(group.x, group.y, label=name, c=color, marker=shape, ls='')

    @pyqtSlot(list)
    def graphOTA(self, plotpoint):
        rssi = plotpoint[0]
        throughput = plotpoint[1]
        attenuation = plotpoint[2]
        #TODO sssssss
        self.RSSIary.append(rssi)
        self.TParray.append(throughput)
        self.Attengrp.append(attenuation)
        ymax = self.ax.get_ylim()[1]
        if ymax < throughput:
            ymax = np.ceil(throughput / 5) * 5
            self.ax.set_ylim(0, ymax)
        if self.throughputMax < throughput:
            self.throughputMax = throughput
            self.rssiMax = rssi
        if rssi < self.rssiMin:
            self.rssiMin = rssi
            self.throughputMin = throughput
        color = coloriter[attenuation % len(coloriter)]
        shape = shapeiter[(attenuation / len(coloriter)) % len(shapeiter)]
        if len(plotpoint) > 3:
            # Graph Throughput vs. Time
            t = plotpoint[3]
            self.TimeArray.append(t)
            xmax = self.ax.get_xlim()[1]
            if xmax < t:
                xmax = np.ceil(t / 5) * 5
                self.ax.set_xlim(0, xmax)
            self.ax.plot(t, throughput, c=color, marker=shape, ls='')
        else:
            # Graph Throughput vs. RSSI
            # Caveat: x axis limits are reversed; initial xlim[0]=-20 xlim[1]=-100
            xlim = self.ax.get_xlim()
            if rssi < xlim[1]:
                xmin = np.floor(rssi / 5) * 5
                self.ax.set_xlim(xmin[0], xmin)
            elif xlim[0] < rssi:
                xmax = np.ceil(rssi / 5) * 5
                self.ax.set_xlim(xmax, xlim[1])
            self.ax.plot(rssi, throughput, c=color, marker=shape, ls='')
        self.fig.canvas.draw()

    @pyqtSlot(bool)
    def otafinished(self, completed):
        if len(self.TParray) > 0 and len(self.RSSIary) > 0:
            try:
                self.dtend = time.strftime("%b %d %Y %H:%M:%S")
                text = self.windowTitle + '\n'
                text += 'Max TP: ' + str(self.throughputMax) + 'Mbps @ {0:.2f}\n'.format(self.rssiMax)
                text += 'Min RSSI: ' + str(self.throughputMin) + 'Mbps @ {0:.2f}\n'.format(self.rssiMin)
                text += 'Pts: ' + str(len(self.TParray)) + '\n'
                if len(self.TimeArray) == 0:
                    # Graph Throughput vs. RSSI
                    new_t = np.array(self.TParray)
                    new_s = np.array(self.RSSIary)

                    inds = new_s.argsort()
                    sortTP = new_t[inds]
                    sortSS = np.sort(new_s)
                    pts = np.where(sortSS[:-1] != sortSS[1:])[0]
                    pts = pts + 1
                    newptsSS = []
                    newptsTP = []
                    for ii in range(len(pts)):
                        if ii == 0:
                            newptsSS.append(sortSS[pts[ii] - 1])  # RSSI
                            newptsTP.append(max(sortTP[0:pts[ii]]))  # TP
                        else:
                            if (pts[ii] - pts[ii - 1]) > 2:  # this weights the places where there are lots of pts
                                newptsSS.append(sortSS[pts[ii - 1]])
                                newptsTP.append(max(sortTP[pts[ii - 1]:pts[ii]]))
                                # print sortTP[pts[ii-1]:pts[ii]]
                                # print sortSS[pts[ii-1]:pts[ii]]

                    # Caveat: x axis limits are reversed; initial xlim[0]=-20 xlim[1]=-100
                    xlim = self.ax.get_xlim()

                    # add pts at start
                    # newptsSS.append(xlim[0])
                    # newptsTP.append(max(newptsTP))
                    # add pts at end
                    newptsSS.insert(0, newptsSS[0] - 1)
                    newptsTP.insert(0, 0)
                    # newptsSS.insert(0,xlim[1])
                    # newptsTP.insert(0,0)

                    XI = np.linspace(xlim[1], xlim[0], xlim[0] - xlim[1] + 1)
                    YI = np.interp(XI, newptsSS, newptsTP)  # Interpolation of points

                    # Draw red line
                    # print 'XI, YI:\n', XI, '\n', YI # TBD
                    self.ax.plot(XI, YI, 'r-')

                    ## TBD -v experiment
                    # Average throughput for each RSSI value
                    # xArray = []
                    # yArray = []
                    # for i in range(min(self.RSSIary), max(self.RSSIary)):
                    #    sum = 0
                    #    count = 0
                    #    for j in range(len(self.RSSIary)):
                    #        if self.RSSIary[j] == i:
                    #           sum += self.TParray[j]
                    #           count += 1
                    #    if count > 0:
                    #        xArray.append(i)
                    #        yArray.append(sum / count)
                    ## Plot interpolated averaged data
                    # ZI = np.interp(XI, xArray, yArray)
                    # print 'XI, ZI:\n', XI, '\n', ZI # TBD
                    # self.ax.plot(XI, ZI, 'g--')

                    # popt, pcov = scipy.optimize.curve_fit(func, xArray, yArray)
                    # self.ax.plot(xArray, func(xArray, *popt), 'y--')
                    # popt, pcov = scipy.optimize.curve_fit(func, self.RSSIary, self.TParray)
                    # self.ax.plot(self.RSSIary, func(self.RSSIary, *popt), 'b--')
                    ## TBD -^ experiment

                    # Annotate where we hit 5Mbps, 1Mbps and 0 Mbps
                    # Linear interpolation formula:
                    #   x = x0 + (y - y0) * (x1 - x0) / y1 - y0)
                    yMax = max(YI)
                    need5 = yMax > 5.0
                    need1 = yMax > 1.0
                    for ii in reversed(range(len(XI) - 1)):
                        y0 = YI[ii]
                        if y0 <= 5.0 and need5:
                            y1 = YI[ii + 1]
                            x0 = XI[ii]
                            x1 = XI[ii + 1]
                            x = x0 + (5.0 - y0) * (x1 - x0) / (y1 - y0)
                            text += '5Mbps @ {0:.2f}\n'.format(x)
                            need5 = False
                        if y0 <= 1.0 and need1:
                            y1 = YI[ii + 1]
                            x0 = XI[ii]
                            x1 = XI[ii + 1]
                            x = x0 + (1.0 - y0) * (x1 - x0) / (y1 - y0)
                            text += '1Mbps @ {0:.2f}\n'.format(x)
                            need1 = False
                        if y0 < 0.1:
                            text += '0Mbps @ {0:.2f}\n'.format(XI[ii])
                            break;

                text += 'Begin: ' + str(self.dtbegin) + '\nEnd: ' + str(self.dtend)
                textbox = AnnotationBbox(TextArea(text, minimumdescent=False),
                                         (self.ax.get_xlim()[0], self.ax.get_ylim()[0]),
                                         xybox=(0.02, 0.02),
                                         xycoords='data',
                                         boxcoords=("axes fraction", "axes fraction"),
                                         box_alignment=(0.0, 0.0))
                self.ax.add_artist(textbox)
                ml = MultipleLocator(1)
                self.ax.yaxis.set_minor_locator(ml)

                if len(self.TimeArray) == 0:
                    if self.ptsGrouping:
                        self.plotGroup(self.RSSIary, self.TParray, self.Attengrp)
                        self.ax.legend(fontsize='xx-small', title='Atten', bbox_to_anchor=(1.02, 1), loc=2,
                                       borderaxespad=0)
                    else:
                        self.ax.plot(self.RSSIary, self.TParray, 'bo')
                else:
                    self.plotGroup(self.TimeArray, self.TParray, self.Attengrp, '-')
                    if self.ptsGrouping:
                        self.ax.legend(fontsize='xx-small', title='Atten', bbox_to_anchor=(1.02, 1), loc=2,
                                       borderaxespad=0)
                self.fig.canvas.draw()
                # Saketh global ota save
                global Odata
                global SSS_data
                newRecord = {self.channel: (self.RSSIary, self.TParray)}
                self.SSS_time.append(time.strftime("%H:%M:%S"))
                SSS_record = {"data": (self.SSS_time,self.RSSIary, self.TParray,self.Attengrp)}
                if len(self.TimeArray) == 0:
                    print "New Record, RSSIary, TParray"
                    print newRecord, '\n', self.RSSIary, '\n', self.TParray
                else:
                    print "New Record, RSSIary, TParray, TimeArray, Attengrp"
                    print newRecord, '\n', self.RSSIary, '\n', self.TParray, '\n', self.TimeArray, '\n', self.Attengrp
                Odata.update(newRecord)
                SSS_data.update(SSS_record)
                size = self.fig.get_size_inches()
                print 'size=', size  # TBD
                self.fig.set_size_inches(16, 14)
                # self.fig.dpi = 100

                # Save channel data in JSON format and as graph in PNG format
                if self.channel:
                    if self.antenna:
                        name = 'Channel' + str(self.channel) + 'Antenna' + str(self.antenna)
                    else:
                        name = 'Channel' + str(self.channel)
                else:
                    if self.antenna:
                        name = 'Antenna' + str(self.antenna)
                    else:
                        name = 'Data'
                otadata = os.path.join(self.logDir, name + '.json')
                SSS_path = os.path.join(self.logDir,"SSS" + '.json')
                otagraph = os.path.join(self.logDir, name + '.png')
                print 'Saving an OTA data  in ' + otadata
                print 'Saving an OTA graph in ' + otagraph
                with open(otadata, 'wb') as outfile:
                    json.dump(Odata, outfile)
                with open(SSS_path, 'wb') as outfile:
                    json.dump(SSS_data, outfile)
                self.fig.canvas.print_figure(otagraph)
                # external draw
                with open(SSS_path,'wr') as outfile:
                    sss_data=json.load(outfile).get("data")
                external.draw_save(sss_data[0],sss_data[2],sss_data[1],[i*(-1) for i in sss_data[3]],
                                   save_path=os.path.join(self.logDir,"logging.png"))
                self.fig.set_size_inches(size)
                self.fig.canvas.draw()  # TBD

            except Exception as e:
                print 'OTAGraph.otafinished: exception: ' + str(e)
                traceback.print_exc()

        self.ota.wait()
        if not self.ota.isStopped():
            self.ota.stop()
        if self.channel:
            print 'Finished OTA for channel ' + str(self.channel)
        else:
            print 'Finished OTA BYE'

    def stopThread(self):
        self.ota.stop()


########################################################### END OTAGraph


################################################################
####  __  __          _ _             __  __         _      ####
#### |  \/  |___ _ _ (_) |_ ___ _ _  |  \/  |___  __| |___  ####
#### | |\/| / _ \ ' \| |  _/ _ \ '_| | |\/| / _ \/ _` / -_) ####
#### |_|  |_\___/_||_|_|\__\___/_|   |_|  |_\___/\__,_\___| ####
####                                                        ####      Begin
#####################################################################################

class NFmonitorGraph(FigureCanvas):
    """Matplotlib Figure widget to display CPU utilization"""

    def __init__(self, parent, parameters):
        # first image setup
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        # initialization of the canvas
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        # notify the system of updated policy
        FigureCanvas.updateGeometry(self)
        self.monNF = autoNF.MonitorNF(self)
        ########################################################################
        # monNF connect declarations ##
        self.connect(self.monNF, SIGNAL("mainstatUpdate(QString)"),
                     form.mainstatUpdate)
        self.connect(self.monNF, SIGNAL("auxstatUpdate(QString)"),
                     form.auxstatUpdate)
        self.connect(self.monNF, SIGNAL("IPUpdate(QString)"),
                     form.IPUpdate)
        self.connect(self.monNF, SIGNAL("chanbgUpdate(QString)"),
                     form.chanbgUpdate)
        self.connect(self.monNF, SIGNAL("antUpdate(QString)"),
                     form.antUpdate)
        self.connect(self.monNF, SIGNAL("finished(bool)"),
                     self.finished_mon, Qt.AutoConnection)
        self.monNF.TvsNoiseXY.connect(self.monGraph, Qt.AutoConnection)
        #       # self.connect(self.monNF, SIGNAL("finished(bool)"),
        #       #              self.NFfinished, Qt.AutoConnection)
        #       #self.connect(self.monNF, SIGNAL("finished(bool)"),
        #       #             self.on_Testplotbtn_clicked)
        #       ########################################################################
        self.ax.set_ylim(-100, -50)
        self.ax.set_xlim(0, 40)
        self.ax.set_xlabel('Time (sec)', size=22)
        self.ax.set_ylabel('Noise (dBm)', size=22)
        self.ax.grid(True, which='major', axis='both', linewidth=1.5, linestyle='-')
        self.ax.grid(True, which='minor', axis='both', linewidth=.5, linestyle='--')
        self.ax.tick_params(labelright=True)
        ml = MultipleLocator(1)
        majorLocator = MultipleLocator(5)
        self.ax.yaxis.set_minor_locator(ml)
        self.ax.yaxis.set_major_locator(majorLocator)
        self.ax.tick_params(labelright=True)
        self.ax.set_title("Monitor Mode <Live Data Plot>", size=28)
        self.solcom = parameters[0]
        self.routcom = parameters[1]
        self.lincom = parameters[2]
        self.commands = parameters[3]
        self.rundata = parameters[4]
        self.iperf = parameters[5]
        self.speed = parameters[6]
        self.timearray = []
        self.noisearay = []
        if self.monNF.isRunning():
            self.monNF.stop()
            self.monNF.wait()
        self.monNF.initialize( \
            self.solcom, \
            self.routcom, \
            self.lincom, \
            self.commands, \
            self.rundata, \
            self.iperf, \
            self.speed)
        self.monNF.start()

        # and disable figure-wide autoscale
        self.ax.set_autoscale_on(False)

    def monGraph(self, PlotXY):
        if len(self.ax.lines[:]) > 1:
            self.ax.lines[0].remove()
        self.timearray.append(PlotXY[0])
        self.noisearay.append(PlotXY[1])
        if max(self.timearray) > 40:
            xlim = np.ceil(max(self.timearray) / 5) * 5
            self.ax.set_xlim(xlim - 40, xlim)

        self.ax.plot(self.timearray, self.noisearay, '-ro')

        self.fig.canvas.draw()

    def speedUpdate(self, speed):
        self.monNF.updateSpeed(speed)
        print '##############\n#########\nSPEED__UPDATED!!\n#########\n#########\n'

    def stopThread(self):
        self.monNF.stop()

    def finished_mon(self, completed):
        self.monNF.wait()
        self.monNF.stop()
        form.finished()
        print "Finished!!!"


########################################################### END NFmonitorGraph


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = WirelessTesting()
    form.show()
    app.exec_()
