#NAME
#    AccessPointWl
#
#FILE
#    C:\TANC-master\PythonWirelessProgram\AccessPointWl.py
#
#CLASSES
#    __builtin__.object
#        AccessPoint
#    exceptions.Exception(exceptions.BaseException)
#        ConnectionError
#        InvalidDocstringError
#        InvalidParameterError
#        ValueNotHandledError
#        VariableNotFoundError
#
import os
import sys
import time
import re
import exceptions
import traceback
import paramiko

# Default SSH Parameters
max_rx_bytes = 8192

LF = '\n' # Linefeed
CR = '\r' # Carriage Return

#  Base class used by all APs
#
#  Setters change internal variables but don't do anything to the AP. Once you
#  have made any desired changes, call Post() to apply them to the AP
#
#  Args:
#      ip_address (str, optional): IP address of the AP. Defaults to the AP's
#          default IP address
#      band (str, optional): Wireless band to operate on. Defaults to '2.4'
#
#class AccessPoint(__builtin__.object):
class AccessPointWl(object):

    debug = False

    def close(self):
        if AccessPointWl.debug:
            print 'AccessPointWl.close()'
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


    def open(self):
        return None
        if self.shell and self.shell.closed:
            self.close()
        if not (self.ssh and self.shell):
            self.close()
            try:
                self.ssh = paramiko.SSHClient()
                if self.ssh:
                    # Test Geck
                    print 'AccessPointWl.open(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ') trying'
                    self.ssh.load_system_host_keys()
                    self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self.ssh.connect(self.ip_address, port=self.port, username=self.username, password=self.password)
                    self.shell = self.ssh.invoke_shell()
                    if self.shell:
                        self.shell.settimeout(1)
                        if AccessPointWl.debug:
                            print 'AccessPointWl.open(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ') succeeded'
                        self.command('')
                    else:
                        if AccessPointWl.debug:
                            print 'AccessPointWl.open(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ') invoke_shell failed'
                else:
                    print 'AccessPointWl.open(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ') SSHClient failed'
            except Exception as e:
                print 'AccessPointWl.open(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ') Caught exception: ' + str(e)
                traceback.print_exc()
                self.close()
        return self.shell


    def __del__(self):
        if AccessPointWl.debug:
            print 'AccessPointWl.__del__()'
        self.close()


#  __init__(self, ip_address, band)
#
    def __init__(self, ip_address = '192.168.1.1', band = '2.4'):
        if AccessPointWl.debug:
            print 'AccessPointWl.__init__(' + ip_address + ',' + band + ')'
        self.ip_address = ip_address    # str
        self.is5GHz     = (band == '5') # str
        self.port       = 22            # int
        self.username   = 'admin'       # str
        self.password   = 'password'    # str
        self.broadcast  = True          # bool
        self.channel    = None          # str
        self.width      = '20'          # str
        self.mode       = None          # str
        self.ssid       = None          # str
        self.security   = 1             # index into supported_securities

        self.ssh        = None
        self.shell      = None
        self.posted     = False
        self._supported_channels = None # list of strings


    def command(self, text):
        response = ''
        if self.open():
            if self.shell and not self.shell.closed:
                if AccessPointWl.debug:
                    print 'AccessPointWl.command(' + text + ')'

                # Flush receive buffer
                if self.shell and not self.shell.closed:
                    try:
                        while self.shell.recv_ready():
                            data = self.shell.recv(max_rx_bytes)
                            #print 'Flushing[' + data + ']' # TBD
                    except Exception as e:
                        print 'AccessPointWl.command(' + text + ') flush exception: ' + str(e.__class__) + ': ' + str(e)
                        traceback.print_exc()
                        self.close()

                # Send command
                cmd = text + CR
                if self.shell and not self.shell.closed:
                    try:
                        self.shell.send(cmd)
                    except Exception as e:
                        print 'AccessPointWl.command(' + text + ') send exception: ' + str(e.__class__) + ': ' + str(e)
                        traceback.print_exc()
                        self.close()

                # Wait for response
                time.sleep(1) # TBD

                # Receive response
                cmd = text + CR + LF
                if self.shell and not self.shell.closed:
                    try:
                        # TBD: how do we know when response is complete?
                        while self.shell.recv_ready():
                            data = self.shell.recv(max_rx_bytes)
                            if data:
                                response = response + data
                            time.sleep(0.1) # TBD
                        if cmd in response:
                            response = response.replace(cmd, '', 1)
                        if AccessPointWl.debug:
                            print 'AccessPointWl.command: response=[' + response + ']' # TBD
                    except Exception as e:
                        print 'AccessPointWl.command(' + text + ') recv exception: ' + str(e.__class__) + ': ' + str(e)
                        traceback.print_exc()
                        self.close()
            else:
                print 'AccessPointWl.command(' + text + ') shell not open'
        return response


#  Data descriptors defined here:
#
#  __dict__
#      dictionary for instance variables (if defined)
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  auth_key
#      Key used for WPA authentication
#
#  name
#      Name of the AP
#
#  supported_bands

    supported_bands = ['2.4', '5']
#
#  supported_broadcasts

#
#  supported_channel_widths
    def get_supported_channel_widths(self):
        if self.is5GHz:
            # 5 GHz
            widths = ['20', '40', '80']
        else:
            # 2.4 GHz
            widths = ['20', '40']
        if AccessPointWl.debug:
            print 'AccessPointWl.get_supported_channel_widths: widths=' + str(widths)
        return widths

    supported_channel_widths = property(get_supported_channel_widths)

#
#  supported_channels
    def get_supported_channels(self):
        try:
            if self.is5GHz:
                # 5 GHz is wl1
                response = self.command('nvram get wl1_chlist')
            else:
                # 2.4 GHz is wl0
                response = self.command('nvram get wl0_chlist')
            response = response.split(CR)[0] # Get first line read
            self._supported_channels = response.split(' ') # Separated by spaces
            if len(self._supported_channels) < 3: # TBD - kluge for RT-AC87U no 5 GHz list
                if self.is5GHz:
                   #self._supported_channels = ['36','40','44','48','149','153','157','161','165']
                   self._supported_channels = ['36','40','44','48','52','56','60','64','100','112','116','132','136', '140','149','153','157','161','165']
                else:
                   self._supported_channels = ['1','2','3','4','5','6','7','8','9','10','11']
        except Exception as e:
            print 'AccessPointWl.get_supported_channels: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        if AccessPointWl.debug:
            print 'AccessPointWl.get_supported_channels: channels=' + str(self._supported_channels)
        return self._supported_channels

    supported_channels = property(get_supported_channels)

#
#  supported_firmware
#      The firmware version of the AP that the code supports

#
#  supported_modes
    def get_supported_modes(self):
        if self.is5GHz:
            # 5 GHz
            modes = ['ag', 'agn', 'ac']
        else:
            # 2.4 GHz
            modes = ['bg', 'bgn']
        if AccessPointWl.debug:
            print 'AccessPointWl.get_supported_modes: modes=' + str(modes)
        return modes

    supported_modes = property(get_supported_modes)

#
#  supported_securities
    supported_securities = [\
    'Open System',\
    'WPA2-Personal',\
    'WPA-Auto-Personal',\
    'WPA2-Enterprise',\
    'WPA-Auto-Enterprise']

#
#  wep_key
#      Key used for WEP authentication

#  Methods defined here:
#
#  GetBand(self)
#      Gets the current wireless band the AP is operating on
#
#      Returns:
#          str: Band of the AP (either '2.4' or '5')
#
    def GetBand(self):
        if self.is5GHz:
            return '5'
        else:
            return '2.4'

#  GetBroadcast(self)
#      Finds out whether the AP is currently broadcasting its SSID
#
#      Returns:
#          bool: True if broadcasting, False otherwise
#
    def GetBroadcast(self):
        broadcast = self.broadcast
        try:
            if self.is5GHz:
                # 5 GHz is wl1
                response = self.command('nvram get wl1_closed')
            else:
                # 2.4 GHz is wl0
                response = self.command('nvram get wl0_closed')
            if '=0' in response:
                broadcast = False
            else:
                broadcast = True
            if AccessPointWl.debug:
                print 'AccessPointWl.GetBroadcast: broadcast=' + str(broadcast)
        except Exception as e:
            print 'AccessPointWl.GetBroadcast: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return broadcast

#  GetChannel(self)
#      Gets the current wireless channel being used.
#
#      Returns:
#          str: Channel number being used
#
    def GetChannel(self):
        channel = self.channel
        try:
            if self.is5GHz:
                # 5 GHz is wl1
                response = self.command('nvram get wl1_chanspec')
            else:
                # 2.4 GHz is wl0
                response = self.command('nvram get wl0_chanspec')
            response = response.split(CR)[0] # Get first line read
            m = re.search('(\d+)', response, re.U) # Get numeric only
            if m and m.group(1):
                channel = str(m.group(1))
            if AccessPointWl.debug:
                print 'AccessPointWl.GetChannel: channel=' + channel
        except Exception as e:
            print 'AccessPointWl.GetChannel: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return channel

#  GetChannelWidth(self)
#      Gets the channel width being used by the AP.
#
#      Returns:
#          str: Channel width currently being used
#
#      Raises:
#          ValueNotHandledError: If the channel width is not supported
#
    def GetChannelWidth(self):
        width = self.width
        try:
            if self.is5GHz:
                # 5 GHz is wl1
                response = self.command('nvram get wl1_chanspec')
            else:
                # 2.4 GHz is wl0
                response = self.command('nvram get wl0_chanspec')
            response = response.split(CR)[0] # Get first line read
            if '/80' in response:
                width = '80'
            elif 'l' in response or 'u' in response:
                width = '40'
            else:
                width = '20'
            if AccessPointWl.debug:
                print 'AccessPointWl.GetChannelWidth: channel width=' + width
        except Exception as e:
            print 'AccessPointWl.GetChannelWidth: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return width

#  GetIP(self)
#      Gets the IP address of the AP.
#
#      Returns:
#          str: IP address
#
    def GetIP(self):
        ip = self.ip_address
        try:
            response = self.command('nvram get lan_ipaddr')
            if response:
                response = response.split(CR)[0]
                if response:
                    ip = response.split('=')[1]
                    if AccessPointWl.debug:
                        print 'AccessPointWl.GetIP: ip=' + ip
        except Exception as e:
            print 'AccessPointWl.GetIP: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return ip

#  GetMode(self)
#      Finds out what mode the AP is currently in.
#
#      Returns:
#          str: Current mode (e.g. 'b', 'bgn', 'ac', etc.)
#
#      Raises:
#          ValueNotHandledError: If the AP mode discovered is not supported
#
    def GetMode(self):
        mode = self.mode
        try:
            # TBD - this is probably bogus and never returns ac
            if self.is5GHz:
                # 5 GHz is wl1
                n = self.command('nvram get wl1_nmode')
                g = self.command('nvram get wl1_gmode')
                if '=0' in n:
                    if '=0' in g:
                        mode = 'a'
                    else:
                        mode = 'ag'
                else:
                    mode = 'agn'
            else:
                # 2.4 GHz is wl0
                n = self.command('nvram get wl0_nmode')
                g = self.command('nvram get wl0_gmode')
                if '=0' in n:
                    if '=0' in n:
                        mode = 'b'
                    else:
                        mode = 'bg'
                else:
                    mode = 'bgn'
            if AccessPointWl.debug:
                print 'AccessPointWl.GetMode: mode=' + mode
        except Exception as e:
            print 'AccessPointWl.GetMode: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return mode

#  GetSSID(self)
#      Gets the current SSID of the AP.
#
#      Returns:
#          str: SSID of the AP
#
    def GetSSID(self):
        ssid = self.ssid
        try:
            if self.is5GHz:
                # 5 GHz is wl1
                response = self.command('nvram get wl1_ssid')
            else:
                # 2.4GHz is wl0
                response = self.command('nvram get wl0_ssid')
            ssid = response.split(CR)[0] # Get first line read
            if AccessPointWl.debug:
                print 'AccessPointWl.GetSSID: ssid=' + ssid
        except Exception as e:
            print 'AccessPointWl.GetSSID: Caught exception: ' + str(e.__class__) + ': ' + str(e)
            traceback.print_exc()
            self.close()
        return ssid

#  SetBand(self, value)
#      Sets the wireless band of the router (Only 2.4 and 5 are supported)
#
#      Valid Usage:
#
#          >>> ap.SetBand('2.4') # all APs support 2.4 GHz
#          >>> ap.SetBand(2.4)   # doesn't have to be a string
#          >>> ap.SetBand(5)     # only works if the AP supports 5 GHz
#
#      Invalid Usage:
#
#          >>> ap.SetBand(3)    # 0nly 2.4 and 5 are legitimate bands
#          >>> ap.SetBand('ac') # mode, not a band
#
#      Args:
#          value (int/float/str): GHz of the wireless band
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the band is not supported
#
    def SetBand(self, value):
        value = str(value)
        if AccessPointWl.debug:
            print 'AccessPointWl.SetBand(' + value + ')'
        bands = AccessPointWl.supported_bands
        if value in bands:
            is5GHz = (value == '5')
            if self.is5GHz != is5GHz:
                self.is5GHz = is5GHz
                self.posted = False
        else:
            raise InvalidParameterError('AccessPointWl.SetBand(' + value + ')')

#  SetBroadcast(self, value)
#      Sets the wireless broadcast mode of the AP.
#
#      Valid Usage:
#
#          >>> ap.SetBroadcast(True)  # enables SSID broadcasting
#          >>> ap.SetBroadcast(1)     # also enables broadcasting
#          >>> ap.SetBroadcast(False) # hides the AP's SSID
#          >>> ap.SetBroadcast(0)     # also hides the SSID
#
#      Invalid Usage:
#
#          >>> ap.SetBroadcast('True') # strings don't work
#          >>> ap.SetBroadcast(2)      # 1 and 0 are the only valid ints
#
#      Args:
#          value (int/bool): Broadcast value
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given broadcast value is not supported
#
    def SetBroadcast(self, value):
        if AccessPointWl.debug:
            print 'AccessPointWl.SetBroadcast(' + str(value) + ')'
        if value:
            broadcast = True
        else:
            broadcast = False
        if self.broadcast != broadcast:
            if self.is5GHz:
                if self.broadcast:
                    self.command('nvram set wl1_closed=0')
                else:
                    self.command('nvram set wl1_closed=1')
            else:
                if self.broadcast:
                    self.command('nvram set wl0_closed=0')
                else:
                    self.command('nvram set wl0_closed=1')
            self.broadcast = broadcast
            self.posted = false

#  SetChannel(self, value)
#      Sets the wireless channel of the AP.
#
#      Valid Usage:
#
#          >>> ap.SetChannel(3)      # ints can be passed
#          >>> ap.SetChannel('7')    # strings also work
#          >>> ap.SetChannel('44')   # 5 GHz has different channel numbers
#          >>> ap.SetChannel('Auto') # All APs support an auto mode
#
#      Invalid Usage:
#
#          >>> ap.SetChannel(456)   # not a valid channel
#          >>> ap.SetChannel('dog') # can't be recognized as an int
#
#      Args:
#          value (int/str): Channel number
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given channel is not supported
#
    def SetChannel(self, value):
        channel = str(value)
        if AccessPointWl.debug:
            print 'AccessPointWl.SetChannel(' + channel + ')'
        if self.channel != channel:
            if not self._supported_channels:
                self.get_supported_channels()
            if channel in self._supported_channels:
                self.channel = channel
                self.posted = False
                if int(channel) > 14:
                    # 5 GHz is wl1
                    cmd = 'nvram set wl1_chanspec='
                    if self.width == '40':
                        if int(channel) > 60:
                            channel = channel + 'u'
                        else:
                            channel = channel + 'l'
                    elif self.width == '80':
                        channel = channel + '/80'
                else:
                    # 2.4GHz is wl0
                    cmd = 'nvram set wl0_chanspec='
                    if self.width == '40':
                        if int(channel) > 9:
                            channel = channel + 'u'
                        else:
                            channel = channel + 'l'
                self.command(cmd + channel)
                self.command('nvram set wl_chanspec=' + channel)
            else:
                raise InvalidParameterError('AccessPointWl.SetChannel(' + channel + ')')

#  SetChannelWidth(self, value)
#      Sets the wireless channel width to use.
#
#      Valid Usage:
#
#          >>> ap.SetChannelWidth('20')    # 20 MHz channel width
#          >>> ap.SetChannelWidth(20)      # ints also work
#          >>> ap.SetChannelWidth('20/40') # some APs support coexistence
#
#      Invalid Usage:
#
#          >>> ap.SetChannelWidth(50) # not a real channel width
#
#      Args:
#          value (int/str): Channel width to use
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given channel width is not supported
#
    def SetChannelWidth(self, value):
        width = str(value)
        if AccessPointWl.debug:
            print 'AccessPointWl.SetChannelWidth(' + width + ')'
        if self.width != width:
            if not width in self.get_supported_channel_widths():
                raise InvalidParameterError('AccessPointWl.SetChannelWidth(' + width + ')')
                width = '20'
            self.width = width
            self.SetChannel(self.channel)

#  SetIP(self, value)
#      Sets the IP address of the AP (only used to connect at the moment)
#
#      Valid Usage:
#
#          >>> ap.SetIP('192.168.1.5') # legitimate IP address
#          >>> ap.SetIP('10.0.0.4')    # another legitimate IP address
#
#      Invalid Usage:
#
#          >>> ap.SetIP('12345')         # invalid IP address format
#          >>> ap.SetIP('192.168.1.300') # numbers must be between 0 and 255
#
#      Args:
#          value (str): IP address to change to
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given IP address is not valid
#
    def SetIP(self, value):
        print 'AccessPointWl.SetIP(' + value + ')'
        print 'Note: Changing IP address of router is a bad idea!'
        if self.ip_address != value:
            self.ip_address = value
            self.posted = False
            self.command('nvram set lan_ipaddr=' + value)

#  SetMode(self, value)
#      Sets the mode of the AP. (available modes vary from AP to AP)
#
#      Valid Usage:
#
#          >>> ap.SetMode('bgn') # support for all 802.11 modes on 2.4 GHz
#          >>> ap.SetMode('n')   # 802.11n only (can work on either 2.4 or 5 GHz)
#          >>> ap.SetMode('a')   # legacy 5 GHz mode
#          >>> ap.SetMode('ac')  # 802.11ac
#
#      Invalid Usage:
#
#          >>> ap.SetMode('y') # not an 802.11 mode on 2.4 or 5 GHz
#
#      Args:
#          value (str): Mode to set
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given mode is not supported
#
    def SetMode(self, value):
        if AccessPointWl.debug:
            print 'AccessPointWl.SetMode(' + value + ')'
        #if self.mode != value:
        #    modes = self.get_supported_modes()
        #    if value in modes:
        #        self.mode = value
        #        self.posted = False
        #    else:
        #       raise InvalidParameterError('AccessPointWl.SetMode(' + value + ')')
        self.mode = value # TBD

#  SetSSID(self, value)
#      Sets the SSID of the router.
#
#      Valid Usage:
#
#          >>> ap.SetSSID('really_cool_ap_ssid') # a really cool SSID
#          >>> ap.SetSSID('password')            # horrible password, but still valid
#          >>> ap.SetSSID(12345678)              # works because it can be cast to a string
#
#      Invalid Usage:
#
#          >>> ap.SetSSID('extremely_long_ssid_for_no_apparent_reason') # SSID can't be more than 32 characters
#
#      Args:
#          value (str): New SSID
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given SSID is not valid
#
    def SetSSID(self, value):
        ssid = str(value)
        print 'AccessPointWl.SetSSID(' + ssid + ')'
        if self.ssid != ssid:
            if len(ssid) > 0:
                self.ssid = ssid
                self.posted = False
                if self.is5GHz:
                    self.command('nvram set wl1_ssid=' + ssid)
                else:
                    self.command('nvram set wl0_ssid=' + ssid)
            else:
                raise InvalidParameterError('AccessPointWl.SetSSID(' + ssid + ')')

#  SetSecurity(self, value)
#      Sets the security mode of the AP (supported security modes vary from AP to AP)
#
#      Default authentication keys are as follows:
#
#      - WEP: *ABCDEF0123456789ABCDEF0123456789* (stored in ``wep_key``)
#
#      - WPA: *abcde12345* (stored in ``auth_key``)
#
#      - WPAEnterprise: *allion123* (stored in ``radius_key``)
#
#      Valid Usage:
#
#          >>> ap.SetSecurity('Open')                # no encryption
#          >>> ap.auth_key = 'super_secure_password' # changes the WPA key
#          >>> ap.SetSecurity('WPA2')                # only WPA2 encryption
#
#      Invalid Usage:
#
#          >>> ap.SetSecurity('Disabled') # use 'Open' instead
#          >>> ap.SetSecurity('WEP2')     # not a real encryption technique
#
#      Args:
#          value (str): Security mode to change to
#
#      Returns:
#          None: None
#
#      Raises:
#          InvalidParameterError: If the given security type is not supported
#
    def SetSecurity(self, value):
        security = str(value)
        if AccessPointWl.debug:
            print 'AccessPointWl.SetSecurity(' + str(security) + ')'
        found = False
        for i in range(len(self.supported_securities)):
            if self.supported_securities[i] == security:
                found = True
                self.security = i
                self.posted = False
                break
        if not found:
            raise InvalidParameterError('AccessPointWl.SetSecurity(' + security + ')')


#Netgear R7000
#Installed firmware:     V1.0.7.10_1.2.3
#Current band:           2.4 GHz
#Current SSID:           NETGEAR52
#Current channel:        1
#Current mode:           bgn
#Current channel width:  40 MHz
#Current security:       Open
#Current broadcast:      True

#  __str__(self)
#
    def __str__(self):
        str = 'ASUS RT-AC68U\n'
        if self.is5GHz:
            band = '5'
        else:
            band = '2.4'
        ssid    = self.GetSSID()
        channel = self.GetChannel()
        mode    = self.GetMode()
        width   = self.GetChannelWidth()
        str += '\tCurrent band:           ' + band + ' GHz\n'
        if ssid:
            str += '\tCurrent SSID:           ' + ssid + '\n'
        if channel:
            str += '\tCurrent channel:        ' + channel + '\n'
        if mode:
            str += '\tCurrent mode:           ' + mode + '\n'
        if width:
            str += '\tCurrent channel width:  ' + width + ' MHz\n'
        # TBD: security isn't implemented, so lie and say it's always WPA2-Personal
        str += '\tCurrent security:       ' + self.supported_securities[1] + '\n'
        if self.GetBroadcast:
            str += '\tCurrent broadcast:      True\n'
        else:
            str += '\tCurrent broadcast:      False\n'
        #return 'AccessPointWl(' + self.ip_address + ',' + str(self.port) + ',' + self.username + ',' + self.password + ',' + band + ')'
        return str

#  turn_dhcp_off(self)
#
    def turn_dhcp_off(self):
        print 'AccessPointWl.turn_dhcp_off() not implemented'
        # TBD
        pass

    # Caveat: Post only updates IP address, Channel number, Channel width
    # Note: channel width is encoded into chanspec with channel
    # TBD - mode and security not currently supported
    def Post(self):
        if AccessPointWl.debug:
            print 'AccessPointWl.Post()'
        if not self.posted:
            if self.open():
                ch = self.channel
                try:
                    self.command('nvram commit')
                    time.sleep(5) # Don't restart wireless in the middle of writing NVRAM!
                    self.command('restart_wireless')
                    time.sleep(10)
                    self.command('nvram set wlready=1') # TBD - is this necessary?
                    self.posted = True
                except Exception as e:
                    print 'AccessPointWl.Post: Caught exception: ' + str(e.__class__) + ': ' + str(e)
                    traceback.print_exc()
                    self.close()

class ConnectionError(exceptions.Exception):
    pass

#  Indicates an error when trying to connect to an AP.
#
#  **Common causes:**
#
#  - The control PC isn't on the same network as the AP
#
#  - The AP is currently powered off or rebooting
#
#  - The IP address of the AP doesn't match what you think it is
#
#  Method resolution order:
#      ConnectionError
#      exceptions.Exception
#      exceptions.BaseException
#      __builtin__.object
#
#  Methods defined here:
#
#  __init__(self)
#
#  ----------------------------------------------------------------------
#  Data descriptors defined here:
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  ----------------------------------------------------------------------
#  Data and other attributes inherited from exceptions.Exception:
#
#  __new__ = <built-in method __new__ of type object>
#      T.__new__(S, ...) -> a new object with type S, a subtype of T
#
#  ----------------------------------------------------------------------
#  Methods inherited from exceptions.BaseException:
#
#  __delattr__(...)
#      x.__delattr__('name') <==> del x.name
#
#  __getattribute__(...)
#      x.__getattribute__('name') <==> x.name
#
#  __getitem__(...)
#      x.__getitem__(y) <==> x[y]
#
#  __getslice__(...)
#      x.__getslice__(i, j) <==> x[i:j]
#
#      Use of negative indices is not supported.
#
#  __reduce__(...)
#
#  __repr__(...)
#      x.__repr__() <==> repr(x)
#
#  __setattr__(...)
#      x.__setattr__('name', value) <==> x.name = value
#
#  __setstate__(...)
#
#  __str__(...)
#      x.__str__() <==> str(x)
#
#  __unicode__(...)
#
#  ----------------------------------------------------------------------
#  Data descriptors inherited from exceptions.BaseException:
#
#  __dict__
#
#  args
#
#  message

class InvalidDocstringError(exceptions.Exception):
    pass

#  Indicates the user didn't format the AP's docstring properly
#
#  When adding support for a new AP, you must make sure to include the name of
#  the AP and the firmware version you are adding support for in the class's
#  docstring. It must be formatted in the following way::
#
#      '''Class for <ap_name> automation.
#
#      Firmware version: <insert firmware here>
#      '''
#
#  This is the bare minimum required for every AP's docstring. Feel free to add
#  any other documentation to the docstring.
#
#  Method resolution order:
#      InvalidDocstringError
#      exceptions.Exception
#      exceptions.BaseException
#      __builtin__.object
#
#  Methods defined here:
#
#  __init__(self)
#
#  ----------------------------------------------------------------------
#  Data descriptors defined here:
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  ----------------------------------------------------------------------
#  Data and other attributes inherited from exceptions.Exception:
#
#  __new__ = <built-in method __new__ of type object>
#      T.__new__(S, ...) -> a new object with type S, a subtype of T
#
#  ----------------------------------------------------------------------
#  Methods inherited from exceptions.BaseException:
#
#  __delattr__(...)
#      x.__delattr__('name') <==> del x.name
#
#  __getattribute__(...)
#      x.__getattribute__('name') <==> x.name
#
#  __getitem__(...)
#      x.__getitem__(y) <==> x[y]
#
#  __getslice__(...)
#      x.__getslice__(i, j) <==> x[i:j]
#
#      Use of negative indices is not supported.
#
#  __reduce__(...)
#
#  __repr__(...)
#      x.__repr__() <==> repr(x)
#
#  __setattr__(...)
#      x.__setattr__('name', value) <==> x.name = value
#
#  __setstate__(...)
#
#  __str__(...)
#      x.__str__() <==> str(x)
#
#  __unicode__(...)
#
#  ----------------------------------------------------------------------
#  Data descriptors inherited from exceptions.BaseException:
#
#  __dict__
#
#  args
#
#  message

class InvalidParameterError(exceptions.Exception):
    pass

#  Indicates an invalid parameter was given.
#
#  A list of valid options for the function that threw this error will be printed.
#
#  Method resolution order:
#      InvalidParameterError
#      exceptions.Exception
#      exceptions.BaseException
#      __builtin__.object
#
#  Methods defined here:
#
#  __init__(self, msg)
#
#  ----------------------------------------------------------------------
#  Data descriptors defined here:
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  ----------------------------------------------------------------------
#  Data and other attributes inherited from exceptions.Exception:
#
#  __new__ = <built-in method __new__ of type object>
#      T.__new__(S, ...) -> a new object with type S, a subtype of T
#
#  ----------------------------------------------------------------------
#  Methods inherited from exceptions.BaseException:
#
#  __delattr__(...)
#      x.__delattr__('name') <==> del x.name
#
#  __getattribute__(...)
#      x.__getattribute__('name') <==> x.name
#
#  __getitem__(...)
#      x.__getitem__(y) <==> x[y]
#
#  __getslice__(...)
#      x.__getslice__(i, j) <==> x[i:j]
#
#      Use of negative indices is not supported.
#
#  __reduce__(...)
#
#  __repr__(...)
#      x.__repr__() <==> repr(x)
#
#  __setattr__(...)
#      x.__setattr__('name', value) <==> x.name = value
#
#  __setstate__(...)
#
#  __str__(...)
#      x.__str__() <==> str(x)
#
#  __unicode__(...)
#
#  ----------------------------------------------------------------------
#  Data descriptors inherited from exceptions.BaseException:
#
#  __dict__
#
#  args
#
#  message

class ValueNotHandledError(exceptions.Exception):
    pass

#  Indicates a value found does not have support in the code.
#
#  **Common causes:**
#
#  - A developer missed a specific mode, security, etc. when programming the AP
#
#  - The firmware of the AP does not match what is supported
#
#  Method resolution order:
#      ValueNotHandledError
#      exceptions.Exception
#      exceptions.BaseException
#      __builtin__.object
#
#  Methods defined here:
#
#  __init__(self, value)
#
#  ----------------------------------------------------------------------
#  Data descriptors defined here:
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  ----------------------------------------------------------------------
#  Data and other attributes inherited from exceptions.Exception:
#
#  __new__ = <built-in method __new__ of type object>
#      T.__new__(S, ...) -> a new object with type S, a subtype of T
#
#  ----------------------------------------------------------------------
#  Methods inherited from exceptions.BaseException:
#
#  __delattr__(...)
#      x.__delattr__('name') <==> del x.name
#
#  __getattribute__(...)
#      x.__getattribute__('name') <==> x.name
#
#  __getitem__(...)
#      x.__getitem__(y) <==> x[y]
#
#  __getslice__(...)
#      x.__getslice__(i, j) <==> x[i:j]
#
#      Use of negative indices is not supported.
#
#  __reduce__(...)
#
#  __repr__(...)
#      x.__repr__() <==> repr(x)
#
#  __setattr__(...)
#      x.__setattr__('name', value) <==> x.name = value
#
#  __setstate__(...)
#
#  __str__(...)
#      x.__str__() <==> str(x)
#
#  __unicode__(...)
#
#  ----------------------------------------------------------------------
#  Data descriptors inherited from exceptions.BaseException:
#
#  __dict__
#
#  args
#
#  message

class VariableNotFoundError(exceptions.Exception):
    pass

#  Indicates the variable name didn't exist in the HTML source.
#
#  **Common causes:**
#
#  - The AP you initialized doesn't match what is being connected to
#
#  - An error occurred when getting the content from the AP's html source
#
#  - The firmware of the AP does not match what is supported
#
#  Method resolution order:
#      VariableNotFoundError
#      exceptions.Exception
#      exceptions.BaseException
#      __builtin__.object
#
#  Methods defined here:
#
#  __init__(self, value)
#
#  ----------------------------------------------------------------------
#  Data descriptors defined here:
#
#  __weakref__
#      list of weak references to the object (if defined)
#
#  ----------------------------------------------------------------------
#  Data and other attributes inherited from exceptions.Exception:
#
#  __new__ = <built-in method __new__ of type object>
#      T.__new__(S, ...) -> a new object with type S, a subtype of T
#
#  ----------------------------------------------------------------------
#  Methods inherited from exceptions.BaseException:
#
#  __delattr__(...)
#      x.__delattr__('name') <==> del x.name
#
#  __getattribute__(...)
#      x.__getattribute__('name') <==> x.name
#
#  __getitem__(...)
#      x.__getitem__(y) <==> x[y]
#
#  __getslice__(...)
#      x.__getslice__(i, j) <==> x[i:j]
#
#      Use of negative indices is not supported.
#
#  __reduce__(...)
#
#  __repr__(...)
#      x.__repr__() <==> repr(x)
#
#  __setattr__(...)
#      x.__setattr__('name', value) <==> x.name = value
#
#  __setstate__(...)
#
#  __str__(...)
#      x.__str__() <==> str(x)
#
#  __unicode__(...)
#
#  ----------------------------------------------------------------------
#  Data descriptors inherited from exceptions.BaseException:
#
#  __dict__
#
#  args
#
#  message

#FUNCTIONS
#    reverse_dict_search(dict, value)
#        Searches a dictionary for the key that maps to the given value
#
#        Args:
#            dict (dict): Dictionary to search through
#            value (str): The value in the dictionary to find a matching key for
#
#        Returns:
#            str: The key that maps to the given value
#
#        Raises:
#            KeyError: If the value doesn't exist in the dictionary
