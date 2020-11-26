# -*- coding: iso-8859-1 -*-
#prog_atten_ethernet.py

import socket
import re
from time import sleep
from jfw50pa_base import JFW50PABase

# Provides an interface to the JFW 50PA-513 programmable attenuator through
# ethernet.
# Note: This has not been tested with multiple computers running this code
# and trying to connect. The device supports up to 4 connections at a time,
# but other connections are kicked off when someone connects.
class JFW50PAEthernet(JFW50PABase):
    def __init__(self,ip_addr,port=3001):
        JFW50PABase.__init__(self)
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip_addr = ip_addr
        self.port = port
        self.cmd_list = ''
        self.soc.setblocking(True)
        self.soc.settimeout(5)

    def Open(self):
        #try:
        self.soc.connect((self.ip_addr,self.port))
        output = self.Read()
        if output[0] == "50PA-513 Connection Open":
            # Now kick anyone else connected off
            self.Write("CLOSE")
            sleep(1)
            output = self.Read()[0].strip()
            if re.search("50PA-513 - [0-4] Connections Closing",output):
                return True
            else:
                return False
        else:
            return False
        #except socket.error as e:
            #print("Error creating socket: "+str(e))

    def Write(self,cmd):
        self.soc.send(cmd+'\r\n')

    def Send(self):
        self.soc.send(self.cmd_list)
        self.Flush()

    def Read(self):
        output = []
        while True:
            try:
                data = self.soc.recv(1200)
                if not data:
                    break
                data = data.strip().split('\r\n')
                for line in data:
                    output.append(line)
            except socket.timeout:
                break
        return output
    
    def Close(self):
        self.Read()
        self.Write("DIS")
        sleep(1)
        output = self.Read()
        if output == "50PA-513 Connection Closing":
            self.soc.Close()
            return True
        else:
            return False

    def setMsg(self,msg):
        if len(msg) <= 98 and isinstance(msg,str):
            self.Write("MESSAGE "+msg)
            sleep(1)
            output = self.Read()[0].strip()
            if output == "Message Stored":
                return True
            else:
                return False

    def clrMsg(self):
        self.Write("CLEAR")
        sleep(1)
        output = self.Read()[0].strip()
        if output == "Message Cleared":
            return True
        else:
            return False

if __name__ == '__main__':
    pa = JFW50PAEthernet('192.168.1.10')
    if pa.Open():
        print pa.Read()
        pa.Write('IDN')
        pa.Write('IDN')
        print pa.View()
        #pa.Send()
        print pa.Read()
        print pa.setMsg("Dead or alive, you're coming with me!")
        pa.Add('IDN')
        pa.Add('IDN')
        pa.Add('IDN')
        pa.Send()
        print pa.Read()
        print pa.clrMsg()
        pa.Write('IDN')
        #pa.Send()
        print pa.Read()
        print pa.Read()
        pa.Close()
