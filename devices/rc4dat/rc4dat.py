# -*- coding: iso-8859-1 -*-
# prog_atten.py

from rc4dat_usb import RC4DATUSB
from rc4dat_ethernet import RC4DATEthernet
from rc4dat_exceptions import RC4DATExcept
try:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from device import SetDevice
except ImportError, ValueError:
    from device import SetDevice

# Allows the user to access, write, and read to a MiniCircuits RC4DAT
# programmable attentuator using either USB communication or
# Ethernet.
class RC4DAT(RC4DATExcept, SetDevice):
    def __init__(self, ip=None, start=None, stop=None,
                step=None, current=None):
        SetDevice.__init__(self, start=start, stop=stop, step=step, current=current)
        if ip:    
            self.pa = RC4DATEthernet(ip)            
        else:
            self.pa = RC4DATUSB()            

    def Open(self):
        return self.pa.Open()

    # Clears the command list
    def Flush(self):
        self.pa.Flush()

    def View(self):
        return self.pa.View()
    
    # Send a list of commands all at once. It can't be greater
    # than 1200 characters


    # Reads the output buffer from the programmable attenuator
    # and clears it. Returns a list where each line outputed is
    # an element.
    def Read(self):
        return self.pa.Read()

    def Close(self):
        return self.pa.Close()

    def set(self, channel, value):
        self.setAttenuator(channel, value)
        self.pa.Send(value)
    # All of the following functions create commands that are added
    # to a command list that is sent to the programmable attenuator
    # when the Send() function is called.
    def setAttenuator(self,num,value,resp=False):
        self._checkAttenNum(num)
        self._checkAttenValue(value)
        self.pa.Add("SAR"+str(num)+' '+str(value))

    def setMultipleAtten(self,num1,value1,num2,value2):
        self._checkAttenNum(num1)
        self._checkAttenValue(value1)
        self._checkAttenNum(num2)
        self._checkAttenValue(value2)
        self.pa.Add("SMA "+str(num1)+' '+str(value1)+','+str(num2)+' '+str(value2))

    def setAllAtten(self,value):
        self._checkAttenValue(value)
        self.pa.Add("SAA "+str(value))

    def getAttenuator(self,num):
        self._checkAttenNum(num)
        self.pa.Add("RA"+str(num))

    def getAllAtten(self):
        self.pa.Add("RAA")

    def setFadeAtten(self,num,start,end,interval,time='M'):
        self._checkAttenNum(num)
        self._checkAttenValue(start)
        self._checkAttenValue(end)
        self._checkAttenFaderStartStop(start,end)
        self._checkTime(interval)
        self._checkAttenTime(time)
        self.pa.Add("FA"+str(num)+' '+str(start)+' '+str(end)+' '+str(interval)+time)

    def setVariableHandover(self,num1,num2,value1,value2,interval,time='M'):
        self._checkAttenNum(num1)
        self._checkAttenValue(value1)
        self._checkAttenNum(num2)
        self._checkAttenValue(value2)
        self._checkAttenNums(num1,num2)
        self._checkTime(interval)
        self._checkAttenTime(time)
        self.pa.Add('VHND A'+str(num1)+' A'+str(num2)+' V'+str(value1)+' V'+str(value2)+' T'+str(interval)+time)

    def pause(self,length,time='M'):
        self._checkTime(length)
        self._checkAttenTime(time)
        self.pa.Add('PAUSE'+str(length)+time)    

    def storeAttenuators(self):
        self.pa.Add("STORE")

    def recallAttenuators(self):
        self.pa.Add("RECALL")

if __name__ == '__main__':
    a = RC4DAT('192.168.1.72')
    a.setAttenuator(1, 25, resp=True)
    print a.Read()
