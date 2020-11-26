#!/usr/bin/env python2.7

# hptcptesttng.py
# Author: Nick Gudman
# Date Last Modified: December 19, 2014

import socket
import time
import argparse
import signal
import sys
import datetime
import threading
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *

DEFAULT_APPLICATION_BUF_SIZE = 8*1024
DEFAULT_SOCKET_BUF_SIZE = 8*1024
DEFAULT_TRANSMIT_PORT = 9101
DEFAULT_RECEIVE_PORT = 9102
DEFAULT_FORMAT = "BYTE"
FORMAT_VALUE = {"BYTE":1, "KB":1000, "MB":1000000, "BIT":0.125*1,
        "KBIT":0.125*1000, "MBIT":0.125*1000000}

# These check functions are needed in order to maintain compatibility
def checkInput(input, low_limit, input_name):
    if not isinstance(input, int):
        raise TypeError(str(input_name)+" must be an integer")
    if input < low_limit:
        raise ValueError(str(input_name)+" must be greater than "+str(low_limit))

def checkPort(port):
    checkInput(port, 1, "port")

def checkBufSize(buf_size):
    checkInput(buf_size, 1, "application buffer size")

def checkNumTests(num_tests):
    checkInput(num_tests, 1, "socket buffer size")

def checkNumBytes(num_bytes):
    checkInput(num_bytes, 1, "number of test bytes")

def checkTimeout(timeout):
    checkInput(timeout, 1, "length of test time")

def checkIp(ip):
    parts = ip.split(".")
    try:
        if len(parts) != 4 or not all(0 <= int(part) < 256 for part in parts):
            raise TypeError("%s is an invalid ip address" % ip)
    except (ValueError, AttributeError, TypeError):
        raise TypeError("%s is an invalid ip address" % ip)

def checkTestFormat(value):
    if not str(value).upper() in FORMAT_VALUE:
        raise HpTcpTestTngError("%s is not an acceptable test format" % value.upper())

class HpTcpTestTngError(Exception):
    pass

class HpTcpTestTNG(socket.socket):
    def __init__(self, ip=None, app_buf_size=DEFAULT_APPLICATION_BUF_SIZE,
                soc_buf_size=DEFAULT_SOCKET_BUF_SIZE, num_tests=None,
                num_bytes=None, timeout=None, trans_port=DEFAULT_TRANSMIT_PORT,
                recv_port=DEFAULT_RECEIVE_PORT, test_format=DEFAULT_FORMAT):
        if ip:
            checkIp(ip)
        self._ip = ip
        checkInput(app_buf_size, 1, "application buffer size")
        self._app_buf_size = app_buf_size
        checkInput(soc_buf_size, 1, "socket buffer size")
        self._soc_buf_size = soc_buf_size
        if num_tests:
            checkInput(num_tests, 1, "number of tests")
        self._num_tests = num_tests
        if num_bytes:
            checkInput(num_bytes, 1, "number of test bytes")
        self._num_bytes = num_bytes
        if timeout:
            checkInput(timeout, 1, "length of test time")
        self._timeout = timeout
        self._checkTestType()
        checkInput(trans_port, 1, "transmit port")
        self._trans_port = trans_port
        checkInput(recv_port, 1, "receive port")
        self._recv_port = recv_port
        checkTestFormat(test_format)
        self._test_format = test_format

        self._total_recv_bytes = 0
        self._total_recv_time = 0
        self._total_recv_tests = 0
        self._total_trans_bytes = 0
        self._total_trans_time = 0
        self._total_trans_tests = 0

    def runTransmit(self, msg_char="."):
        self._isTest()
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self._soc_buf_size)
        if self._timeout:
            self.settimeout(self._timeout)
        else:
            self.settimeout(None)
        self.connect((self._ip, self.trans_port))
        transmit_str = (self._app_buf_size) * msg_char
        test_time = 0
        if self._timeout:
            num_tests = 0
            while test_time < self._timeout:
                start_time = time.time()
                self.sendall(transmit_str)
                delta = time.time() - start_time
                test_time += delta
                self._total_trans_bytes += self._app_buf_size
                self._total_trans_time += delta
                num_tests += 1
                self._total_trans_tests += 1
        else:
            if self._num_bytes:
                num_tests = int(self._num_bytes / self._app_buf_size)
            elif self._num_tests:
                num_tests = self._num_tests
            start_time = time.time()
            for i in xrange(num_tests):
                self.sendall(transmit_str)
                self._total_trans_bytes += self._app_buf_size
                self._total_trans_tests += 1
                prev_test_time = test_time
                test_time = time.time() - start_time
                self._total_trans_time += (test_time - prev_test_time)
        self.close()
        result = float(((self._app_buf_size * num_tests) / test_time) / FORMAT_VALUE[self._test_format])
        return "{:.2f}".format(result)

    def runReceive(self):
        self._isTest()
        cnt = 0
        time_taken = 0
        buf = bytearray(self._app_buf_size)
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self._soc_buf_size)
        if self._timeout:
            self.settimeout(self._timeout)
        else:
            self.settimeout(None)
        self.connect((self._ip, self._recv_port))
        if self._num_tests:
            start_time = time.time()
            for i in xrange(self._num_tests):
                tmp_cnt = self.recv_into(buf)
                cnt += tmp_cnt
                self._total_recv_bytes += tmp_cnt
                self._total_recv_tests += 1
                prev_time_taken = time_taken
                time_taken = time.time() - start_time
                self._total_recv_time += (time_taken - prev_time_taken)
        elif self._num_bytes:
            start_time = time.time()
            while cnt < self._num_bytes:
                tmp_cnt = self.recv_into(buf)
                cnt += tmp_cnt
                self._total_recv_bytes += tmp_cnt
                self._total_recv_tests += 1
                prev_time_taken = time_taken
                time_taken = time.time() - start_time
                self._total_recv_time += (time_taken - prev_time_taken)
        elif self._timeout:
            while time_taken < self._timeout:
                start_time = time.time()
                tmp_cnt = self.recv_into(buf)
                cnt += tmp_cnt
                delta = time.time() - start_time
                time_taken += delta
                self._total_recv_bytes += tmp_cnt
                self._total_recv_time += delta
                self._total_recv_tests += 1
        self.close()
        result = float(cnt / time_taken) / FORMAT_VALUE[self._test_format]
        return "{:.2f}".format(result)

    def _isTest(self):
        if self._num_tests is None and self._num_bytes is None and self._timeout is None:
            raise HpTcpTestTngError("number of tests to run, number of bytes to test with, or test time length must be specified")

    def _checkTestType(self):
        if (self._num_tests and self._num_bytes) or (self._num_tests and self._timeout) or (self._num_bytes and self._timeout):
            raise HpTcpTestTngError("cannot specify multiple tests to run")

    # The rest of the functions in this class are setters and getters. The setters will check to
    # see if the value is valid before setting the variable
    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, value):
        checkIp(value)
        self._ip = value

    @property
    def app_buf_size(self):
        return self._app_buf_size

    @app_buf_size.setter
    def app_buf_size(self, value):
        checkInput(value, 1, "application buffer size")
        self._app_buf_size = value

    @property
    def soc_buf_size(self):
        return self._soc_buf_size

    @soc_buf_size.setter
    def soc_buf_size(self, value):
        checkInput(value, 1, "socket buffer size")
        self._soc_buf_size = value

    # The variables num_tests, num_bytes, and timeout are mutually exclusive so when the setter
    # for one of these variables is called it sets the other two variables to None
    @property
    def num_tests(self):
        return self._num_tests

    @num_tests.setter
    def num_tests(self, value):
        checkInput(value, 1, "number of tests to run")
        self._num_bytes = None
        self._timeout = None
        self._num_tests = value

    @property
    def num_bytes(self):
        return self._num_bytes

    @num_bytes.setter
    def num_bytes(self, value):
        checkInput(value, 1, "number of test bytes")
        self._num_tests = None
        self._timeout = None
        self._num_bytes = value

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        checkInput(value, 1, "length of test time")
        self._num_tests = None
        self._num_bytes = None
        self._timeout = value

    @property
    def trans_port(self):
        return self._trans_port

    @trans_port.setter
    def trans_port(self, value):
        checkInput(value, 1, "transmit port")
        self._trans_port = value

    @property
    def recv_port(self):
        return self._recv_port

    @recv_port.setter
    def recv_port(self, value):
        checkInput(value, 1, "receive port")
        self._recv_port = value

    @property
    def test_format(self):
        return self._test_format

    @test_format.setter
    def test_format(self, value):
        checkTestFormat(value)
        self._test_format = value

    @property
    def total_trans_bytes(self):
        return self._total_trans_bytes

    @property
    def total_trans_time(self):
        return self._total_trans_time

    @property
    def total_trans_tests(self):
        return self._total_trans_tests

    @property
    def total_recv_bytes(self):
        return self._total_recv_bytes

    @property
    def total_recv_time(self):
        return self._total_recv_time

    @property
    def total_recv_tests(self):
        return self._total_recv_tests

# The following are objects, helper functions, and functions needed to maintain
# compatibility for calling HpTcpTestTNG functionally
_tng = HpTcpTestTNG()

def _setupTest(ip, app_buf_size, soc_buf_size, num_tests, num_bytes, timeout, test_format):
    _tng.ip = ip
    _tng.app_buf_size = app_buf_size
    _tng.soc_buf_size = soc_buf_size
    if num_tests is not None:
        _tng.num_tests = num_tests
    if num_bytes is not None:
        _tng.num_bytes = num_bytes
    if timeout is not None:
        _tng.timeout = timeout
    _tng.test_format = test_format

def transmitTest(ip, app_buf_size=DEFAULT_APPLICATION_BUF_SIZE,
                 soc_buf_size=DEFAULT_SOCKET_BUF_SIZE, num_tests=None,
                 num_bytes=None, timeout=None, test_format=DEFAULT_FORMAT,
                 port=DEFAULT_TRANSMIT_PORT):
    _setupTest(ip, app_buf_size, soc_buf_size, num_tests, num_bytes, timeout, test_format)
    _tng.trans_port = port
    return _tng.runTransmit()

def receiveTest(ip, app_buf_size=DEFAULT_APPLICATION_BUF_SIZE,
                soc_buf_size=DEFAULT_SOCKET_BUF_SIZE, num_tests=None,
                num_bytes=None, timeout=None, test_format=DEFAULT_FORMAT,
                port=DEFAULT_RECEIVE_PORT):
    _setupTest(ip, app_buf_size, soc_buf_size, num_tests, num_bytes, timeout, test_format)
    _tng.recv_port = port
    return _tng.runReceive()

# The following code includes a class that manages command line functionality
description =   "HP TCP TEST - THE NEXT GENERATION: This program performs TCP speed tests on HP printers and " \
                "returns the kilobytes per second (by default). TCP speed tests will only work with HP " \
                "printers on ports 9101 and 9102 (or must function the same as ports 9101 and 9102). Only one type of " \
                "test can be selected at a time. If no test type is specified then the program will default to running " \
                "the test 1000 times. The Python version of this program was written using Python 2.7 and is only " \
                "guaranteed to work with that (though pyrun works well so far). A brief summary of the test results will " \
                "display if the program prematurely exits or Ctrl-C is pressed."
epilog =    "Author: Nick Gudman; Email: nicholas.jam.gudman@hp.com; " \
            "Last Updated: December 19, 2014"

class hpTcpTestTngCmd(QThread):
    def __init__(self, args, parent=None):
        super(hpTcpTestTngCmd, self).__init__(parent)
        self.stopped = False
        self.mutex = QMutex()
        self.completed = False
        self._tcp_test = HpTcpTestTNG()
        self.parser = argparse.ArgumentParser(description=description,epilog=epilog,prefix_chars="-/")

        self.parser.add_argument("ip",help="IP address of test's target")

        test_group = self.parser.add_mutually_exclusive_group()
        test_group.add_argument("-t","-T","/t","/T","--transmit",dest="transmit",action="store_true",help="test transmit speed")
        test_group.add_argument("-r","-R","/r","/R","--receive",dest="receive",action="store_true",help="test receive speed")
        test_group.add_argument("-x","-X","/x","/X","--testboth",dest="test_both",action="store_true",help="test receive and transmit speed")
        test_group.add_argument("-z","-Z","/z","/Z","--concurrent-test",dest="concurrent_test",action="store_true",help="test receive and transmit speed concurrently")

        self.parser.add_argument("-f","-F","/f","/F","--format",dest="format",default="KB",help="output format, [BYTE/KB/MB/BIT/KBIT/MBIT] per second, default is KB/S")
        self.parser.add_argument("-s","-S","/s","/S","--appbufsize",dest="app_buf_size",default=8,type=int,help="application buffer size (KB), default 8KB")
        self.parser.add_argument("-o","-O","/o","/O","--socbufsize",dest="soc_buf_size",default=8,type=int,help="socket buffer size (KB), default 8KB")
        self.parser.add_argument("-p","-P","/p","/P","--port",dest="port",type=int,help="port #; transmit default 9101, receive default 9102")
        self.parser.add_argument("-e","-E","/e","/E","--repeat",dest="repeat",default=1,type=int,help="# of times to repeat the test; default is 1; 0 runs infinitely")
        self.parser.add_argument("-l","-L","/l","/L","--logfile",dest="logfile",default=0,type=int,help="1/0 = output/no output to logfile current directory hptcp.log")
        #self.parser.add_argument("-v","-V","/v","/V","--interval",dest="interval",default=0,type=float,help="result print interval")

        options_group = self.parser.add_mutually_exclusive_group()
        options_group.add_argument("-n","-N","/n","/N","--number",dest="number",type=int,help="# of tests to run before stopping, default 1000")
        options_group.add_argument("-k","-K","/k","/K","--total",dest="kilobytes",type=int,help="# of KB to test with before stopping")
        options_group.add_argument("-i","-I","/i","/I","--time",dest="time",type=int,help="# of seconds to perform the test before stopping")

        self._test_repeat = 0
        self._start_time = 0
        self._args = self.parser.parse_args(args)
        #self._args = self.parser.parse_args(['/f', 'MBIT', '/i', '1', '/e', '10','/l','1', '/t', '192.168.2.8'])



    def stop(self):
        try:
            self.mutex.lock()
            self.stopped = True

        finally:
            self.mutex.unlock()


    def isStopped(self):
        try:
            self.mutex.lock()
            return self.stopped
        finally:
            self.mutex.unlock()

    def run(self):
        #print self._args
        self.i = 0
        #self.counter = 0
        if self._args.logfile:
            self.fn = os.getcwd() + "\\hpTcp.log"
            openfile = open(self.fn, 'a')
            openfile.write('\n\n\nHPTCP Python Version 2.0\n')
            begin = time.strftime("%b %d %Y %H:%M:%S")
            openfile.write('Timestamp started: ' + begin)
            openfile.write('\nConnect To: ' + str(self._args.ip) +':'+\
            str(self._args.port)+ '\nTest for '+str(self._args.repeat)+' times' \
            ' at ' + str(self._args.time) + 's intervals\n')
            openfile.close()

            self.emit(SIGNAL("logUpdate(QString)"), '\n\nHPTCP Python Version 2.0')
            self.emit(SIGNAL("logUpdate(QString)"), 'Timestamp started: ' + begin)
            self.emit(SIGNAL("logUpdate(QString)"),('Connect To: ' + str(self._args.ip) +':'+\
            str(self._args.port)+ '\nTest for '+str(self._args.repeat)+' times' \
            ' at ' + str(self._args.time) + 's intervals\n'))
        self.processArgs()


    def _processOptions(self):
        self._tcp_test.ip = self._args.ip
        self._tcp_test.app_buf_size = self._args.app_buf_size * 1024
        self._tcp_test.soc_buf_size = self._args.soc_buf_size * 1024
        if self._args.number:
            self._tcp_test.num_tests = self._args.number
        elif not (self._args.kilobytes or self._args.time):
            self._tcp_test.num_tests = 1000
        if self._args.kilobytes:
            self._tcp_test.num_bytes = self._args.kilobytes * 1024
        if self._args.time:
            self._tcp_test.timeout = self._args.time
        if self._args.port:
            if self._args.transmit:
                self._tcp_test.trans_port = self._args.port
            elif self._args.receive:
                self._tcp_test.recv_port = self._args.port
            elif self._args.test_both:
                raise RuntimeError("Can only specify a non-default port number for transmit or receive tests, not both")
        elif self._args.transmit:
            self._tcp_test.trans_port = 9101
        elif self._args.receive:
            self._tcp_test.recv_port = 9102
        if self._args.format:
            self._tcp_test.test_format = self._args.format.upper()
        if not isinstance(self._args.repeat, int):
            raise TypeError("number of repeats must be an integer")
        if self._args.repeat < 0:
            raise ValueError("number of repeats must be a positive or zero to repeat indefinitely")
        self._test_repeat = self._args.repeat

        if not (self._args.transmit or self._args.receive or self._args.test_both or self._args.concurrent_test):
            raise RuntimeError("Need to specify a transmit test, receive test, both, or concurrent tests")

    def _signalHandler(self, signal, frame):
        lines = list()
        lines.append("\n\n** Test Exited Prematurely **")
        if self._args.transmit or self._args.test_both or self._args.concurrent_test:
            #lines.append("Total number of transmit tests: %d" % (self._tcp_test.total_trans_tests))
            lines.append("Total number of {:s}s transmitted: {:.2f}".format(self._tcp_test.test_format, float(self._tcp_test.total_trans_bytes / FORMAT_VALUE[self._tcp_test.test_format])))
            lines.append("Total transmission time in seconds: {:.2f}".format(float(self._tcp_test.total_trans_time)))
            try:
                rate = float(self._tcp_test.total_trans_bytes / self._tcp_test.total_trans_time)
            except ZeroDivisionError:
                rate = 0
            lines.append("Transmitted at a rate of {:.2f} {:s}/S".format(rate / FORMAT_VALUE[self._tcp_test.test_format], self._tcp_test.test_format))
        if len(lines) > 1:
            lines = ["{s:{c}<{n}}".format(s=line, n=50, c=" ") for line in lines]
        else:
            lines = lines + 4* [str()]
        if self._args.receive or self._args.test_both or self._args.concurrent_test:
            lines[1] += "Total number of receive tests: %d" % (self._tcp_test.total_recv_tests)
            lines[2] += "Total number of {:s}s received: {:.2f}".format(self._tcp_test.test_format, float(self._tcp_test.total_recv_bytes / FORMAT_VALUE[self._tcp_test.test_format]))
            lines[3] += "Total receive time in seconds: {:.2f}".format(float(self._tcp_test.total_recv_time))
            try:
                rate = float(self._tcp_test.total_recv_bytes / self._tcp_test.total_recv_time)
            except ZeroDivisionError:
                rate = 0
            lines[4] += "Received at a rate of {:.2f} {:s}/S".format(rate / FORMAT_VALUE[self._tcp_test.test_format], self._tcp_test.test_format)
        lines.append("\nTime since program started: %s (hh:mm:ss)" % (str(datetime.timedelta(seconds=(float("{:.2f}".format(time.time() - self._start_time)))))))
        #for line in lines:
            #self.counter += 1
            #if self._args.logfile:
            #        openfile = open(self.fn, 'a')
            #        openfile.write(str((self.counter-1)*float(self._args.time))+'-'+str(self.counter*float(self._args.time)) + ': Error\n')
            #        openfile.close()
            #self.emit(SIGNAL("logUpdate(QString)"), str((self.counter-1)*float(self._args.time))+'-'+str(self.counter*float(self._args.time)) + ': Error\n')
            #print line
        print str('\nFailed send/recieve at Time: {:.3f} (s)'.format(time.time()-self._start_time))

        self.processArgs()
        #sys.exit(0)

    def processArgs(self):
        def innerTest(func_ptr):
            if port is not None:
                result = func_ptr(ip,app_buf_size,soc_buf_size,num_tests,num_bytes,timeout,test_format,port)
            else:
                result = func_ptr(ip,app_buf_size,soc_buf_size,num_tests,num_bytes,timeout,test_format)
            return float(result)

        def printTestResults(results):
            def createStr(result, test_type):
                test_string = "{s:{c}<{n}}".format(s="TCP "+test_type+" Test:", n=20, c=" ")
                return "{:s} {:.2f} {:s}/S".format(test_string, float(result), self._tcp_test.test_format)

            trans_results, recv_results = tuple([filter(lambda x: x != None, tuple(t)) for t in zip(*results)])
            result_str = str()
            if len(trans_results) > 0:
                result_str += createStr(sum(trans_results) / len(trans_results), "Transmit")
            if len(trans_results) > 0 and len(recv_results) > 0:
                result_str += "\t"
            if len(recv_results) > 0:
                result_str += createStr(sum(recv_results) / len(recv_results), "Receive")
            if result_str:

                self.i += 1

                result_str = '{0:<16} {1}'.format(str((self.i-1)*float(self._args.time))+\
                    '-'+str(self.i*float(self._args.time))+':', result_str )
                #print '1: '+result_str
                self.emit(SIGNAL("logUpdate(QString)"), result_str)
                if self._args.logfile:
                    openfile = open(self.fn, 'a')
                    openfile.write(result_str + '\n')
                    if self.stopped:
                        openfile.write(result_str + '\nHPTCP Stopped')
                        self.emit(SIGNAL("logUpdate(QString)"), "HPTCP Stopped")
                    openfile.close()

        def runTests():
            def threadWrapper(func, result):
                try:
                    result = float(func())
                except socket.error:
                    self._signalHandler(None, None)

            trans_result = None
            recv_result = None
            if self._args.concurrent_test:
                print 'MULTITHREADING ENABLED'
                trans_thread = threading.Thread(target=threadWrapper, args=(self._tcp_test.runTransmit, trans_result))
                recv_thread = threading.Thread(target=threadWrapper, args=(self._tcp_test.runReceive, recv_result))
                trans_thread.start()
                #recv_thread.start()

                trans_thread.join()
                #recv_thread.join()

            if self._args.transmit or self._args.test_both:
                try:
                    trans_result = float(self._tcp_test.runTransmit())
                except socket.error:
                    self._signalHandler(None, None)
            if self._args.receive or self._args.test_both:
                try:
                    recv_result = float(self._tcp_test.runReceive())
                except socket.error:
                    self._signalHandler(None, None)
            return trans_result, recv_result

        self._processOptions()
        #signal.signal(signal.SIGINT, self._signalHandler)
        if self._args.test_both or self._args.transmit or self._args.receive or self._args.concurrent_test:
            results = list()
            if self.i == 0:
                self._start_time = time.time()

            while(not self.stopped):
                results.append(runTests())
                #print self.stopped
                if self._test_repeat > 0:
                    if self.i < self._test_repeat:
                        printTestResults(results)
                        results = list()
                    else:
                        break
                else:
                    printTestResults(results)

#if __name__ == "__main__":
#    hpTcpTestTngCmd()
