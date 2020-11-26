# -*- coding: iso-8859-1 -*-
# prog_atten_serial.py

from time import sleep
import sys
from rc4dat_base import RC4DATBase
try:
    import win32com.client  # Reference PyWin32
except ImportError:
    print ("Module import Error pywin32, {}".format(sys.exc_info()[1]))


# Provides an interface to the MiniCircuits RC4DAT programmable attenuator through
# USB.
class RC4DATUSB(RC4DATBase):
    def __init__(self):
        RC4DATBase.__init__(self)        
        try:
            self.Att1 = win32com.client.Dispatch("mcl_RUDAT.USB_DAT") # dll needed to communicate to attenuator
            self.Open()
        except Exception as e:
            print "Error({0}, {1})".format(sys.exc_info()[0], sys.exc_info()[1])
            print "Make sure mcl_RUDAT.USB_DAT.dll is available"
            print "can be downloaded as part of a software package to control the Attenuator"
            print "https://www.minicircuits.com/softwaredownload/RUDAT_CD.zip"

        
    def Open(self):
        try:
            Conn_Status = self.Att1.Connect()
        except Exception as e:
            print e
        if Conn_Status == 1:
            pass
            #print ("Connection Successful")
            #MN = self.Att1.Read_ModelName("")  # Read model name
            #print ("Model Name:", str(MN[1]))
            #SN = self.Att1.Read_SN("")  # Read serial number
            #print ("Serial Number:", str(SN[1]))
        else:
            raise IOError("Connection Failed make sure the device is connected")       
        
    def Write(self,cmd):
        pass   # residual from serial usage

    def Send(self, value):
        self.Att1.SetChannelAtt(1, value)
        self.Att1.SetChannelAtt(2, value)
        self.Att1.SetChannelAtt(3, value)
        self.Att1.SetChannelAtt(4, value)

    def Read(self, channel=None):
        if channel == 1:
            read = self.Att1.ReadChannelAtt(1) # Read attenuation
        elif channel == 2:
            read = self.Att1.ReadChannelAtt(2)  # Read attenuation
        elif channel == 3:
            read = self.Att1.ReadChannelAtt(3)  # Read attenuation
        elif channel == 4:
            read = self.Att1.ReadChannelAtt(4)  # Read attenuation
        else:
            read = []
            [read.append(self.Att1.ReadChannelAtt(x)) for x in xrange(1,5,1)]
            
        return read

    def Close(self):
        self.Att1.Disconnect()

    

    
