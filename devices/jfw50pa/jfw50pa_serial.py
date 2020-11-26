# -*- coding: iso-8859-1 -*-
# prog_atten_serial.py

import serial
from time import sleep
from jfw50pa_base import JFW50PABase

# Provides an interface to the JFW 50PA-513 programmable attenuator through
# serial.
class JFW50PASerial(JFW50PABase):
    def __init__(self,port,baudrate=9600,timeout=1):
        JFW50PABase.__init__(self)
        self.port = port
        self.ser = serial.Serial(baudrate=baudrate,timeout=timeout)
        
    def Open(self):
        try:
            self.ser.port = self.port
            self.ser.open()
        except serial.SerialException as e:
            print e
        except ValueError as e:
            print e
        finally:
            return self.ser.isOpen()

    def Write(self,cmd):
        self.ser.write(cmd+'\r\n')

    def Send(self):
        self.ser.write(self.cmd_list)
        self.Flush()

    def Read(self):
        output = []
        is_done = False
        while not is_done:
            line = self.ser.readline().strip()
            if line == '':
                is_done = True
            else:
                output.append(line)
        return output

    def Close(self):
        self.ser.close()
        return not self.ser.isOpen()

    def setBaudrate(self,baud):
        if not isinstance(baud, int):
            raise TypeError("baudrate must be an integer ")
        if not ((baud == 9600) or (baud == 19200) or (baud == 38400)):
            raise ValueError("baudrate must be 9600, 19200, or 38400")
        self.Write('CB'+str(baud))
        self.Close()
        sleep(8)
        self.baudrate = baud
        return self.Open()

    
