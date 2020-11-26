#!/usr/bin/env python2.7

import subprocess
import time
import argparse

DEFAULT_WAIT_TIME = 1
DEFAULT_PLUG_RANGE = (1,8)

def repow(ip, plug_num, wait=0, mode="restart"):
    community = "private"

    def isPlugInRange(num):
        if num >= DEFAULT_PLUG_RANGE[0] and num <= DEFAULT_PLUG_RANGE[1]:
            return True
        else:
            return False

    def isIp(ip):
        parts = ip.split(".")
        try:
            if len(parts) != 4 or not all(0 <= int(part) < 256 for part in parts):
                return False
        except (ValueError, AttributeError, TypeError):
            return False
        return True

    def runCmds(nums, pdu_cmd):
        if isinstance(nums, (list, set)):
            if not all(isinstance(num, int) for num in nums):
                raise TypeError("%s is not an integer or list or set of integers" % (nums))
            for num in nums:
                if isPlugInRange(num):
                    cmd = "snmpset -v 1 -c {community} {powerstripIP} .1.3.6.1.4.1.318.1.1.4.4.2.1.3.{powerstripplug} i {pducommand}".format(community=community, powerstripIP=ip, powerstripplug=num, pducommand=pdu_cmd)
                    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    proc.wait()
                else:
                    print "Error: plug number %i is out of range" % (num)
        else:
            raise TypeError("%s is not an integer or list or set of integers" % (str(nums)))

    if not isIp(ip):
        raise TypeError("%s is an invalid ip address" % value)
    if not isinstance(wait, (int, float)):
        raise TypeError("%s is not an integer or float" % (wait))
    if wait < 0:
        raise ValueError("%d is not positive. Wait time must be positive" % (wait))
    if mode.lower() == "restart" and wait == 0:
        wait = DEFAULT_WAIT_TIME
    if isinstance(plug_num, int):
        plug_num = [plug_num]
    if not (mode.lower() == "on" or mode.lower() == "off" or mode.lower() == "restart"):
        raise ValueError("%s is not a valid power mode (on/off/restart)" % (args.state))
    if mode.lower() == "off" or mode.lower() == "restart":
        runCmds(plug_num, 2)
    time.sleep(wait)
    if mode.lower() == "on" or mode.lower() == "restart":
        runCmds(plug_num, 1)

description =   "REPOW - REMOTE POWER: Control a APC switched rack APU from Linux"
epilog =    "Author: Nick Gudman; Email: nicholas.jam.gudman@hp.com; " \
            "Last Updated: April 11, 2016"

def repowCmd():
    parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                    prefix_chars="-")
    parser.add_argument("ip", help="IP address of power strip")
    parser.add_argument("plugnumbers", type=int,
                        nargs="*", help="plug number(s)")
    parser.add_argument("mode", help="power mode (on/off/restart)")
    parser.add_argument("-t", "--time", dest="time", type=int,
                        nargs="?", default=0,
                        help="wait time interval in seconds (default 1 seconds " \
                            "for restarts, 0 seconds for on/off)")

    args = parser.parse_args()
    _remotePower(args.ip, args.plugnumbers, args.time, args.mode)

if __name__ == "__main__":
    repowCmd()
