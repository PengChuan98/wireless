################################################################################
# File Name: apcpdu.py
# Author:    Kevin DeRossett
# Email:     kevin.derossett@hp.com
#
# Purpose of library:
# - The 'apcpdu' module is the main entry point for the 'apcpdu' package.
#   It is responsible for: managing the telnet connection, synchronizing IO,
#   providing access to helpful classes for menu navigation, and sending commands.
#
################################################################################
# Release Notes:
#
# ----- September/10/2012 - Kevin DeRossett-------------------------------------
# - Initial release.
#     * Open/Close telnet sessions
#     * Easy telnet IO syncronization with send()
#     * When connected to pdu as interactive provide access to helpful menu() class/s
#     * When connected to pdu as non-interactive provide access to helpful cmd() class/s
################################################################################

import logging; logger = logging.getLogger(__name__)
import os
import sys
import re
import time
import telnetlib

import menu
import commands
import snmp

MODES = {
    'interactive':0,
    'non-interactive':1,
    'snmp':2,
}

class apcpdu(object):

    # Init...
    def __init__(self, mode, host, port=None, username=None, password=None):
        if isinstance(mode, basestring):
            mode = MODES[mode.lower()]
        if mode in (0, 1, 2):
            # The basics
            self.mode = mode
            self.host = host
            if port is None:
                if mode in (0, 1):
                    self.port = 23
                else:
                    self.port = 161
            else:
                self.port = port
            if username is None:
                if mode in (0, 1):
                    self.username = 'apc'
                else:
                    self.username = 'public'
            else:
                self.username = username
            if password is None:
                if mode in (0, 1):
                    self.password = 'apc'
                else:
                    self.password = 'private'
            else:
                self.password = password
            if mode in (0, 1):
                self.telnet = telnetlib.Telnet()
                self.connected = False
            else:
                self.telnet = None
                self.connected = True
        else:
            raise Exception('') # TODO ==> 

    # Opens the telnet session and parses initial output to set class variables.
    def open(self):
        if self.mode in (0, 1):
            if self.closed():
                # Open telnet connection
                logger.debug('Open telnet connection')
                self.telnet.open(self.host, self.port); time.sleep(1)
                # Read until prompted for user name
                # If the PDU event log is left open and the telnet session is closed,
                # the PDU does not do the normal login process. Then, while we wait for
                # the login prompt the PDU determins inactivity and closes the connection.
                logger.debug('Expect "Event Log" or "User Name :"')
                result = self.telnet.expect([re.compile(r"-+\sEvent\sLog\s-+", re.M), re.compile(r"User\sName\s:\s", re.M)])
                # Write 'result' to stdout
                sys.stdout.write(result[2])
                sys.stdout.flush()
                if result[0] == 0:
                    logger.debug('Found "Event Log", backing out')
                    # We are stuck in the event log... back out and restart session
                    self.telnet.write(chr(0x1b) + "\r\n4\r\n"); time.sleep(1)
                    self.telnet.close(); time.sleep(1)
                    self.telnet.open(self.host, self.port); time.sleep(1)
                    # Read until prompted for user name
                    logger.debug('Expect "User Name :"')
                    result = self.telnet.expect([re.compile(r"User\sName\s:\s", re.M)])
                # Write user name to socket
                logger.debug('Write "'+self.username+'"')
                self.telnet.write(self.username + "\r\n"); time.sleep(1)
                # Read until prompted for password
                logger.debug('Expect "Password  :"')
                sys.stdout.write(self.telnet.expect([re.compile(r"Password\s\s:\s", re.M)])[2])
                sys.stdout.flush()
                if self.mode == 0:
                    # Write password to socket
                    logger.debug('Write "'+self.password+'"')
                    self.telnet.write(self.password + "\r\n"); time.sleep(1)
                    # Read echoed password characters to get them off the buffer
                    sys.stdout.write(self.telnet.read_until("*" * self.password.__len__()))
                    sys.stdout.flush()
                    # Read until prompt, store in 'out' and parse for classvars
                    result = self.telnet.expect([re.compile(r"User\sName\s:\s", re.M), re.compile(r"^>\s$", re.M)])
                    # Write 'result' to stdout
                    sys.stdout.write(result[2])
                    sys.stdout.flush()
                    if result[0] == 0:
                        self.telnet.close()
                        self.connected = False
                        raise Exception('Login failure')
                else:
                    # Write password to socket
                    logger.debug('Write "'+self.password+' -c"')
                    self.telnet.write(self.password + " -c\r\n"); time.sleep(1)
                    # Read echoed password characters to get them off the buffer
                    sys.stdout.write(self.telnet.read_until("*" * (self.password.__len__() + 3)))
                    sys.stdout.flush()
                    # Read until prompt, store in 'out' and parse for classvars
                    result = self.telnet.expect([re.compile(r"User\sName\s:\s", re.M), re.compile(r"^APC>\s$", re.M)])
                    # Write 'result' to stdout
                    sys.stdout.write(result[2])
                    sys.stdout.flush()
                    if result[0] == 0:
                        self.telnet.close()
                        self.connected = False
                        raise Exception('Login failure')
                self.connected = True
        else:
            self.connected = True
        return self.connected

    # Returns connection state of the current telnet session.
    def opened(self):
        if self.mode in (0, 1):
            return self.connected
        else:
            return True

    # Closes the telnet session.
    def close(self):
        if self.mode in (0, 1):
            if self.opened():
                logger.debug('Close telnet connection')
                if self.mode == 0:
                    for x in xrange(15):
                        self.telnet.write(chr(0x1b))
                    self.telnet.write("4\r\n")
                self.telnet.close(); time.sleep(1)
                self.connected = False
        else:
            self.connected = True
        return not self.connected

    # Returns connection state of the current telnet session.
    def closed(self):
        if self.mode in (0, 1):
            return not self.connected
        else:
            return False

    # Sends a 'command' string to the PDU. Waits for output to match an 'expect'
    # list of optional regular expression objects. By default send() will wait
    # for output to match [re.compile(r"^> $", re.M), re.compile(r"^APC> $", re.M)].
    # send() handles empty 'command' strings as ENTER/RETURN.
    # send() handles chr(0x1b) 'command' strings as ESCAPE.
    # send() handles "\f" 'command' strings as CTRL-L.
    #
    # The cmd() and menu() methods are a better alternative to using send() directly.
    #
    def send(self, command="", withReturn=True, expect=[re.compile(r"^>\s$", re.M), re.compile(r"^APC>\s$", re.M)]):
        if self.mode in (0, 1):
            logger.debug('Sending '+repr(command))
            # Avoid exception and open the connection for forgetful people.
            if self.closed(): self.open()
            # Should we send an ENTER/RETURN automatically?
            if withReturn: rtn = "\r\n"
            else: rtn = ""
            # Write 'command' and press ENTER/RETURN
            if command == "":
                sys.stdout.write("ENTER")
                sys.stdout.flush()
                self.telnet.write("\r\n")
            elif command == chr(0x1b):
                sys.stdout.write("ESC")
                sys.stdout.flush()
                self.telnet.write(command)
            elif command == "\f":
                sys.stdout.write("CTRL-L")
                sys.stdout.flush()
                if self.mode == 0: self.telnet.write(command)
                else: self.telnet.write(command + rtn)
            else:
                self.telnet.write(command + rtn)
            time.sleep(1)
            if self.opened:
                # Read until prompt, store in 'result'
                result = self.telnet.expect(expect)
                sys.stdout.write(result[2])
                sys.stdout.flush()
                return result
            else:
                # Read until end, store in 'result'
                result = self.telnet.read_all()
                sys.stdout.write(result)
                sys.stdout.flush()
                return (-1, None, result)
        else:
            raise Exception('') # TODO ==>

    # Returns an instance of apcpdu.menuMain.
    # apcpdu.menuMain handles telnet IO syncronization and has many builtin
    # helper methods for menu navigation. This is meant to be used when logged
    # onto the APC PDU in interactive mode.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().phasemanagement().overloadalarmthreshold("16")
    # OR
    #     * menu = apcpdu.menu()
    #       menu = menu.devicemanager()
    #       menu = menu.phasemanagement()
    #       menu = menu.overloadalarmthreshold("16")
    #
    def menu(self):
        if self.mode == 0:
            # Avoid exception and open the connection for forgetful people.
            if self.closed(): self.open()
            # Return class with entry point to nav menus
            return menu.main(self)
        else:
            raise Exception("menu() must be used with mode 0 (interactive).")

    # Returns an instance of apcpdu.commands.
    # apcpdu.commands handles telnet IO syncronization and has many builtin
    # helper methods for sending commands to the PDU. This is meant to be used
    # when logged onto the APC PDU in non-interactive mode.
    #
    # Example/s:
    #     * apcpdu.cmd().on("1")
    #     * apcpdu.cmd().off("1")
    #     * apcpdu.cmd().reboot("1")
    #
    def cmd(self):
        if self.mode == 1:
            # Avoid exception and open the connection for forgetful people.
            if self.closed(): self.open()
            # Return class with direct command methods
            return commands.commands(self)
        else:
            raise Exception("cmd() must be used with mode 1 (non-interactive).")

    # Returns an instance of apcpdu.snmp.
    def snmp(self):
        if self.mode == 2:
            # Return class with SNMP methods.
            return snmp.snmp(self)
        else:
            raise Exception("snmp() must be used with mode 2 (snmp).")
