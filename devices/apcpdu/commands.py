################################################################################
# File Name: commands.py
# Author:    Kevin DeRossett
# Email:     kevin.derossett@hp.com
#
# Purpose of library:
# - The 'commands' module provides easy to use methods for the PDU's
#   non-interactive mode.
#
################################################################################
# Release Notes:
#
# ----- September/10/2012 - Kevin DeRossett-------------------------------------
# - Initial release.
#     * When connected to pdu as non-interactive wrap commands with helpful methods.
################################################################################

import logging; logger = logging.getLogger(__name__)
import re

class commands(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # Turns one or more outlets on.
    #
    # Example/s:
    #     * apcpdu.cmd().on("1")
    #     * apcpdu.cmd().on(1)
    #     * apcpdu.cmd().on([1, "2"])
    #     * apcpdu.cmd().on((1, "2"))
    #
    def on(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("on " + outlets)

    # Turns one or more outlets off.
    #
    # Example/s:
    #     * apcpdu.cmd().off("1")
    #     * apcpdu.cmd().off(1)
    #     * apcpdu.cmd().off([1, "2"])
    #     * apcpdu.cmd().off((1, "2"))
    #
    def off(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("off " + outlets)

    # Reboots one or more outlets.
    #
    # Example/s:
    #     * apcpdu.cmd().reboot("1")
    #     * apcpdu.cmd().reboot(1)
    #     * apcpdu.cmd().reboot([1, "2"])
    #     * apcpdu.cmd().reboot((1, "2"))
    #
    def reboot(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("reboot " + outlets)

    # Gets the outlet groups.
    def outletgroups(self):
        return self.apcpdu.send("outletgroups")

    # Gets the reboot duration for one or more outlets. Sets the reboot
    # duration for one outlet.
    #
    # Example/s:
    #     * apcpdu.cmd().rebootduration()
    #     * apcpdu.cmd().rebootduration("1")
    #     * apcpdu.cmd().rebootduration(1)
    #     * apcpdu.cmd().rebootduration([1, "2"])
    #     * apcpdu.cmd().rebootduration((1, "2"))
    #     * apcpdu.cmd().rebootduration("1", "1")
    #     * apcpdu.cmd().rebootduration(1, 1)
    #
    def rebootduration(self, outlets="", atime=""):
        if (type(outlets) == list) | (type(outlets) == tuple):
            if atime == "":
                outs = ""
                for outlet in outlets:
                    if type(outlet) != str: outs += str(outlet) + " "; continue
                    else: outs += outlet + " "; continue
                outlets = outs
            else:
                if type(outlets[0]) != str: outlets = str(outlets[0])
                else: outlets = outlets[0]
        elif type(outlets) != str: outlets = str(outlets)
        if type(atime) != str: atime = str(atime)
        if (outlets != "") & (atime != ""):
            return self.apcpdu.send("rebootduration " + outlets + ":" + atime)
        else:
            return self.apcpdu.send("rebootduration " + outlets)

    # Gets the power on delay for one or more outlets. Sets the power on delay
    # for one outlet.
    #
    # Example/s:
    #     * apcpdu.cmd().powerondelay()
    #     * apcpdu.cmd().powerondelay("1")
    #     * apcpdu.cmd().powerondelay(1)
    #     * apcpdu.cmd().powerondelay([1, "2"])
    #     * apcpdu.cmd().powerondelay((1, "2"))
    #     * apcpdu.cmd().powerondelay("1", "1")
    #     * apcpdu.cmd().powerondelay(1, 1)
    #
    def powerondelay(self, outlets="", atime=""):
        if (type(outlets) == list) | (type(outlets) == tuple):
            if atime == "":
                outs = ""
                for outlet in outlets:
                    if type(outlet) != str: outs += str(outlet) + " "; continue
                    else: outs += outlet + " "; continue
                outlets = outs
            else:
                if type(outlets[0]) != str: outlets = str(outlets[0])
                else: outlets = outlets[0]
        elif type(outlets) != str: outlets = str(outlets)
        if type(atime) != str: atime = str(atime)
        if (outlets != "") & (atime != ""):
            return self.apcpdu.send("powerondelay " + outlets + ":" + atime)
        else:
            return self.apcpdu.send("powerondelay " + outlets)

    # Gets the power off delay for one or more outlets. Sets the power off delay
    # for one outlet.
    #
    # Example/s:
    #     * apcpdu.cmd().poweroffdelay()
    #     * apcpdu.cmd().poweroffdelay("1")
    #     * apcpdu.cmd().poweroffdelay(1)
    #     * apcpdu.cmd().poweroffdelay([1, "2"])
    #     * apcpdu.cmd().poweroffdelay((1, "2"))
    #     * apcpdu.cmd().poweroffdelay("1", "1")
    #     * apcpdu.cmd().poweroffdelay(1, 1)
    #
    def poweroffdelay(self, outlets="", atime=""):
        if (type(outlets) == list) | (type(outlets) == tuple):
            if atime == "":
                outs = ""
                for outlet in outlets:
                    if type(outlet) != str: outs += str(outlet) + " "; continue
                    else: outs += outlet + " "; continue
                outlets = outs
            else:
                if type(outlets[0]) != str: outlets = str(outlets[0])
                else: outlets = outlets[0]
        elif type(outlets) != str: outlets = str(outlets)
        if type(atime) != str: atime = str(atime)
        if (outlets != "") & (atime != ""):
            return self.apcpdu.send("poweroffdelay " + outlets + ":" + atime)
        else:
            return self.apcpdu.send("poweroffdelay " + outlets)

    # Gets the PDU cold start delay. Sets the PDU cold start delay.
    #
    # Example/s:
    #     * apcpdu.cmd().pducoldstartdelay()
    #     * apcpdu.cmd().pducoldstartdelay("1")
    #     * apcpdu.cmd().pducoldstartdelay(1)
    #
    def pducoldstartdelay(self, atime=""):
        if type(atime) != str: atime = str(atime)
        return self.apcpdu.send("pducoldstartdelay " + atime)

    # Gets the amperage overload alarm. Sets the amperage overload alarm.
    #
    # Example/s:
    #     * apcpdu.cmd().overloadalarm()
    #     * apcpdu.cmd().overloadalarm("1")
    #     * apcpdu.cmd().overloadalarm(1)
    #     * apcpdu.cmd().overloadalarm("1", "1")
    #     * apcpdu.cmd().overloadalarm(1, 1)
    #
    def overloadalarm(self, phasenum="", current=""):
        if type(phasenum) != str: phasenum = str(phasenum)
        if type(current) != str: current = str(current)
        if (phasenum != "") & (current != ""):
            return self.apcpdu.send("overloadalarm " + phasenum + " " + current)
        else:
            return self.apcpdu.send("overloadalarm " + phasenum)

    # Gets the amperage near overload warning. Sets the amperage near overload
    # warning.
    #
    # Example/s:
    #     * apcpdu.cmd().nearoverloadwarning()
    #     * apcpdu.cmd().nearoverloadwarning("1")
    #     * apcpdu.cmd().nearoverloadwarning(1)
    #     * apcpdu.cmd().nearoverloadwarning("1", "1")
    #     * apcpdu.cmd().nearoverloadwarning(1, 1)
    #
    def nearoverloadwarning(self, phasenum="", current=""):
        if type(phasenum) != str: phasenum = str(phasenum)
        if type(current) != str: current = str(current)
        if (phasenum != "") & (current != ""):
            return self.apcpdu.send("nearoverloadwarning " + phasenum + " " + current)
        else:
            return self.apcpdu.send("nearoverloadwarning " + phasenum)

    # Gets the amperage low load warning. Sets the amperage low load warning.
    #
    # Example/s:
    #     * apcpdu.cmd().lowloadwarning()
    #     * apcpdu.cmd().lowloadwarning("1")
    #     * apcpdu.cmd().lowloadwarning(1)
    #     * apcpdu.cmd().lowloadwarning("1", "1")
    #     * apcpdu.cmd().lowloadwarning(1, 1)
    #
    def lowloadwarning(self, phasenum="", current=""):
        if type(phasenum) != str: phasenum = str(phasenum)
        if type(current) != str: current = str(current)
        if (phasenum != "") & (current != ""):
            return self.apcpdu.send("lowloadwarning " + phasenum + " " + current)
        else:
            return self.apcpdu.send("lowloadwarning " + phasenum)

    # Gets the overload restriction. Sets the overload restriction.
    #
    # Example/s:
    #     * apcpdu.cmd().overloadrestriction()
    #     * apcpdu.cmd().overloadrestriction("1")
    #     * apcpdu.cmd().overloadrestriction(1)
    #     * apcpdu.cmd().overloadrestriction("1", "on")
    #     * apcpdu.cmd().overloadrestriction("1", "off")
    #     * apcpdu.cmd().overloadrestriction(1, "on")
    #     * apcpdu.cmd().overloadrestriction(1, "off")
    #     * apcpdu.cmd().overloadrestriction("1", True)
    #     * apcpdu.cmd().overloadrestriction("1", False)
    #     * apcpdu.cmd().overloadrestriction(1, True)
    #     * apcpdu.cmd().overloadrestriction(1, False)
    #
    def overloadrestriction(self, phasenum="", on=""):
        if type(phasenum) != str: phasenum = str(phasenum)
        if on == True: on = "on"
        if on == False: on = "off"
        if type(on) != str: on = str(on)
        if (phasenum != "") & (on != ""):
            return self.apcpdu.send("overloadrestriction " + phasenum + " " + on)
        else:
            return self.apcpdu.send("overloadrestriction " + phasenum)

    def adduser(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'adduser'")

    def deluser(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'deluser'")

    def assign(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'assign'")

    def unassign(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'unassign'")

    # Gets the list of users and which ports have been assigned to them.
    #
    # Example/s:
    #     * apcpdu.cmd().list()
    #
    def list(self):
        ports = []
        lines = self.apcpdu.send("list")[2].splitlines()
        for line in lines:
            tokens = line.split(':')
            if (len(tokens) > 2) and (self.apcpdu.username == tokens[1].strip()):
                ports = tokens[2].strip().split(',')
        return tuple(ports)

    # Gets the status of one or more outlets.
    #
    # Example/s:
    #     * apcpdu.cmd().status()
    #     * apcpdu.cmd().status("1")
    #     * apcpdu.cmd().status(1)
    #     * apcpdu.cmd().status([1, "2"])
    #     * apcpdu.cmd().status((1, "2"))
    #
    def status(self, outlets=""):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("status " + outlets)

    # Sets the name of an outlet.
    #
    # Example/s:
    #     * apcpdu.cmd().name("1", "some new name")
    #     * apcpdu.cmd().status(1, "some new name")
    #
    def name(self, outlet, name):
        if type(outlet) != str: outlet = str(outlet)
        if type(name) != str: name = str(name)
        return self.apcpdu.send("name " + outlet + " \"" + name + "\"")

    # Gets the current/amperage.
    def current(self):
        return self.apcpdu.send("current")

    # Gets the wattage.
    def power(self):
        return self.apcpdu.send("power")

    def password(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'password'")

    def passwd(self):
        raise NotImplementedError("TODO ==> implement wrapper method for 'passwd'")

    # Gets current logged in user name.
    def whoami(self):
        return self.apcpdu.send("whoami")

    # Resets the PDU to outlet settings to defaults.
    def reset_defaults_pdu(self):
        return self.apcpdu.send("reset_defaults_pdu")

    # Uploads an .ini file
    def uploadini(self):
        return self.apcpdu.send("uploadini") # does nothing unless using serial

    # Gets the PDU firmware version.
    def ver(self):
        return self.apcpdu.send("ver")

    # Gets the PDU firmware version.
    def version(self):
        return self.apcpdu.send("version")

    # Logs out of and closes the current telnet session.
    def logout(self):
        self.apcpdu.send("logout")
        return self.apcpdu.close()

    # Logs out of and closes the current telnet session.
    def logoff(self):
        self.apcpdu.send("logoff")
        return self.apcpdu.close()

    # Logs out of and closes the current telnet session.
    def exit(self):
        self.apcpdu.send("exit")
        return self.apcpdu.close()

    # Logs out of and closes the current telnet session.
    def quit(self):
        self.apcpdu.send("quit")
        return self.apcpdu.close()

    # Logs out of and closes the current telnet session.
    def bye(self):
        self.apcpdu.send("bye")
        return self.apcpdu.close()

    # Gets help for various commands.
    def help(self, command=""):
        if type(command) != str: command = str(command)
        return self.apcpdu.send("help " + command)

    # Turns one or more outlets on after a delay.
    #
    # Example/s:
    #     * apcpdu.cmd().delayedon("1")
    #     * apcpdu.cmd().delayedon(1)
    #     * apcpdu.cmd().delayedon([1, "2"])
    #     * apcpdu.cmd().delayedon((1, "2"))
    #
    def delayedon(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("delayedon " + outlets)

    # Turns one or more outlets off after a delay.
    #
    # Example/s:
    #     * apcpdu.cmd().delayedoff("1")
    #     * apcpdu.cmd().delayedoff(1)
    #     * apcpdu.cmd().delayedoff([1, "2"])
    #     * apcpdu.cmd().delayedoff((1, "2"))
    #
    def delayedoff(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("delayedoff " + outlets)

    # Reboots one or more outlets after a delay.
    #
    # Example/s:
    #     * apcpdu.cmd().delayedreboot("1")
    #     * apcpdu.cmd().delayedreboot(1)
    #     * apcpdu.cmd().delayedreboot([1, "2"])
    #     * apcpdu.cmd().delayedreboot((1, "2"))
    #
    def delayedreboot(self, outlets):
        if (type(outlets) == list) | (type(outlets) == tuple):
            outs = ""
            for outlet in outlets:
                if type(outlet) != str: outs += str(outlet) + " "; continue
                else: outs += outlet + " "; continue
            outlets = outs
        elif type(outlets) != str: outlets = str(outlets)
        return self.apcpdu.send("delayedreboot " + outlets)
