# prog_atten_base.py

# Base class which ProgAttenSerial and ProgAttenEthernet
# inherit from.
class RC4DATBase(object):
    def __init__(self):
        self.cmd_list = ''

    # Adds a command to a list of commands to send all
    # at once using Send() in this classes child classes.
    def Add(self,cmd):
        cmds = self.cmd_list+cmd+'\r\n'
        if len(cmds) <= 1200:
            self.cmd_list = self.cmd_list+cmd+'\r\n'
        else:
            raise BufferError("the buffer is full")

    def View(self):
        return self.cmd_list

    def Get(self):
        return self.cmd_list

    def Flush(self):
        self.cmd_list = ''
