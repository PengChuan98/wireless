################################################################################
# File Name: menuMain.py
# Author:    Kevin DeRossett
# Email:     kevin.derossett@hp.com
#
# Purpose of library:
# - The 'menuMain' module provides easy to use methods for the PDU's
#   interactive mode main menu.
#
################################################################################
# Release Notes:
#
# ----- September/10/2012 - Kevin DeRossett-------------------------------------
# - Initial release.
#     * When connected to pdu as interactive wrap menu with helpful methods.
################################################################################

import logging; logger = logging.getLogger(__name__)

class main(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # Enters into the Device Manager sub-menu.
    # Returns an instance of apcpdu.menuDeviceManager.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager()
    #
    def devicemanager(self):
        self.apcpdu.send("1")
        return devicemanager(self.apcpdu)

    # Enters into the Network sub-menu.
    # Returns an instance of apcpdu.menuNetwork.
    #
    # Example/s:
    #     * apcpdu.menu().network()
    #
    def network(self):
        self.apcpdu.send("2")
        return network(self.apcpdu)

    # Enters into the System sub-menu.
    # Returns an instance of apcpdu.menuSystem.
    #
    # Example/s:
    #     * apcpdu.menu().system()
    #
    def system(self):
        self.apcpdu.send("3")
        return system(self.apcpdu)

    # Selects Logout from the main menu.
    # Ensures local telnet socket has been closed.
    # Returns True when session closed, False otherwise.
    #
    # Example/s:
    #     * apcpdu.menu().logout()
    #
    def logout(self):
        self.apcpdu.send("4")
        self.apcpdu.close()
        return self.apcpdu.closed()

    # Sends ESC character causing the Main menu to refresh.
    # Returns this instance (self) of apcpdu.menuMain.
    #
    # Example/s:
    #     * apcpdu.menu().mainmenu()
    #
    def mainmenu(self):
        self.apcpdu.send(chr(0x1b))
        return self

    # Sends RETURN/ENTER character causing the Main menu to refresh.
    # Returns this instance (self) of apcpdu.menuMain.
    #
    # Example/s:
    #     * apcpdu.menu().refresh()
    #
    def refresh(self):
        self.apcpdu.send()
        return self

    # Enters into the Event Log sub-menu.
    # Returns an instance of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog()
    #
    def eventlog(self):
        self.apcpdu.send("\f")
        return eventlog(self.apcpdu, self)

class devicemanager(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # Enters into the Phase Management sub-menu.
    # Returns an instance of apcpdu.menuPhaseManagement.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().phasemanagement()
    #
    def phasemanagement(self):
        self.apcpdu.send("1")
        raise NotImplementedError("TODO ==>")

    # Enters into the Outlet Management sub-menu.
    # Returns an instance of apcpdu.menuOutletManagement.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().outletmanagement()
    #
    def outletmanagement(self):
        self.apcpdu.send("2")
        raise NotImplementedError("TODO ==>")

    # Enters into the Power Supply Status sub-menu.
    # Returns an instance of apcpdu.menuPowerSupplyStatus.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().powersupplystatus()
    #
    def powersupplystatus(self):
        self.apcpdu.send("3")
        raise NotImplementedError("TODO ==>")

    # Exits this sub-menu and returns to the Main menu.
    # Returns an instance of apcpdu.menuMain.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().back()
    #
    def back(self):
        self.apcpdu.send(chr(0x1b))
        return menuMain.menuMain(self.apcpdu)

    # Refreshes this menu.
    # Returns this instance (self) of apcpdu.menuDeviceManager.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().refresh()
    #
    def refresh(self):
        self.apcpdu.send()
        return self

    # Enters into the Event Log sub-menu.
    # Returns an instance of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().devicemanager().eventlog()
    #
    def eventlog(self):
        self.apcpdu.send("\f")
        return menuEventLog.menuEventLog(self.apcpdu, self)

class network(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # Enters into the TCP/IP sub-menu.
    # Returns an instance of apcpdu.menuTCPIP.
    #
    # Example/s:
    #     * apcpdu.menu().network().tcpip()
    #
    def tcpip(self):
        self.apcpdu.send("1")
        raise NotImplementedError("TODO ==>")

    # Enters into the DNS sub-menu.
    # Returns an instance of apcpdu.menuDNS.
    #
    # Example/s:
    #     * apcpdu.menu().network().dns()
    #
    def dns(self):
        self.apcpdu.send("2")
        raise NotImplementedError("TODO ==>")

    # Enters into the Ping Utility sub-menu.
    # Returns an instance of apcpdu.menuPingUtility.
    #
    # Example/s:
    #     * apcpdu.menu().network().pingutility()
    #
    def pingutility(self):
        self.apcpdu.send("3")
        raise NotImplementedError("TODO ==>")

    # Enters into the FTP Server sub-menu.
    # Returns an instance of apcpdu.menuFTPServer.
    #
    # Example/s:
    #     * apcpdu.menu().network().ftpserver()
    #
    def ftpserver(self):
        self.apcpdu.send("4")
        raise NotImplementedError("TODO ==>")

    # Enters into the Telnet/SSH sub-menu.
    # Returns an instance of apcpdu.menuTelnetSSH.
    #
    # Example/s:
    #     * apcpdu.menu().network().telnetssh()
    #
    def telnetssh(self):
        self.apcpdu.send("5")
        raise NotImplementedError("TODO ==>")

    # Enters into the Web/SSL/TLS sub-menu.
    # Returns an instance of apcpdu.menuWebSSLTLS.
    #
    # Example/s:
    #     * apcpdu.menu().network().webssltls()
    #
    def webssltls(self):
        self.apcpdu.send("6")
        raise NotImplementedError("TODO ==>")

    # Enters into the Email sub-menu.
    # Returns an instance of apcpdu.menuEmail.
    #
    # Example/s:
    #     * apcpdu.menu().network().email()
    #
    def email(self):
        self.apcpdu.send("7")
        raise NotImplementedError("TODO ==>")

    # Enters into the SNMP sub-menu.
    # Returns an instance of apcpdu.menuSNMP.
    #
    # Example/s:
    #     * apcpdu.menu().network().snmp()
    #
    def snmp(self):
        self.apcpdu.send("8")
        raise NotImplementedError("TODO ==>")

    # Enters into the Syslog sub-menu.
    # Returns an instance of apcpdu.menuSyslog.
    #
    # Example/s:
    #     * apcpdu.menu().network().syslog()
    #
    def syslog(self):
        self.apcpdu.send("9")
        raise NotImplementedError("TODO ==>")

    # Enters into the ISX Protocol sub-menu.
    # Returns an instance of apcpdu.menuISXProtocol.
    #
    # Example/s:
    #     * apcpdu.menu().network().isxprotocol()
    #
    def isxprotocol(self):
        self.apcpdu.send("10")
        raise NotImplementedError("TODO ==>")

    # Exits this sub-menu and returns to the Main menu.
    # Returns an instance of apcpdu.menuMain.
    #
    # Example/s:
    #     * apcpdu.menu().network().back()
    #
    def back(self):
        self.apcpdu.send(chr(0x1b))
        return menuMain.menuMain(self.apcpdu)

    # Refreshes this menu.
    # Returns this instance (self) of apcpdu.menuNetwork.
    #
    # Example/s:
    #     * apcpdu.menu().network().refresh()
    #
    def refresh(self):
        self.apcpdu.send()
        return self

    # Enters into the Event Log sub-menu.
    # Returns an instance of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().network().eventlog()
    #
    def eventlog(self):
        self.apcpdu.send("\f")
        return menuEventLog.menuEventLog(self.apcpdu, self)

class system(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # Enters into the User Manager sub-menu.
    # Returns an instance of apcpdu.menuUserManager.
    #
    # Example/s:
    #     * apcpdu.menu().system().usermanager()
    #
    def usermanager(self):
        self.apcpdu.send("1")
        raise NotImplementedError("TODO ==>")

    # Enters into the Identification sub-menu.
    # Returns an instance of apcpdu.menuIdentification.
    #
    # Example/s:
    #     * apcpdu.menu().system().identification()
    #
    def identification(self):
        self.apcpdu.send("2")
        raise NotImplementedError("TODO ==>")

    # Enters into the Date/Time sub-menu.
    # Returns an instance of apcpdu.menuDateTime.
    #
    # Example/s:
    #     * apcpdu.menu().system().datetime()
    #
    def datetime(self):
        self.apcpdu.send("3")
        raise NotImplementedError("TODO ==>")

    # Enters into the Tools sub-menu.
    # Returns an instance of apcpdu.menuTools.
    #
    # Example/s:
    #     * apcpdu.menu().system().tools()
    #
    def tools(self):
        self.apcpdu.send("4")
        raise NotImplementedError("TODO ==>")

    # Enters into the RADIUS sub-menu.
    # Returns an instance of apcpdu.menuRADIUS.
    #
    # Example/s:
    #     * apcpdu.menu().system().radius()
    #
    def radius(self):
        self.apcpdu.send("5")
        raise NotImplementedError("TODO ==>")

    # Enters into the Modem sub-menu.
    # Returns an instance of apcpdu.menuModem.
    #
    # Example/s:
    #     * apcpdu.menu().system().modem()
    #
    def modem(self):
        self.apcpdu.send("6")
        raise NotImplementedError("TODO ==>")

    # Enters into the About System sub-menu.
    # Returns an instance of apcpdu.menuAboutSystem.
    #
    # Example/s:
    #     * apcpdu.menu().system().aboutsystem()
    #
    def aboutsystem(self):
        self.apcpdu.send("7")
        raise NotImplementedError("TODO ==>")

    # Exits this sub-menu and returns to the Main menu.
    # Returns an instance of apcpdu.menuMain.
    #
    # Example/s:
    #     * apcpdu.menu().system().back()
    #
    def back(self):
        self.apcpdu.send(chr(0x1b))
        return menuMain.menuMain(self.apcpdu)

    # Refreshes this menu.
    # Returns this instance (self) of apcpdu.menuSystem.
    #
    # Example/s:
    #     * apcpdu.menu().system().refresh()
    #
    def refresh(self):
        self.apcpdu.send()
        return self

    # Enters into the Event Log sub-menu.
    # Returns an instance of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().system().eventlog()
    #
    def eventlog(self):
        self.apcpdu.send("\f")
        return menuEventLog.menuEventLog(self.apcpdu, self)

class eventlog(object):

    # Init...
    def __init__(self, apcpdu, parent):
        self.apcpdu = apcpdu
        self.parent = parent

    # Exits this sub-menu and returns to the parent menu.
    # Returns apcpdu.menu* instance that refers to parent.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog().exit()
    #
    def exit(self):
        self.apcpdu.send(chr(0x1b))
        return self.parent

    # Refreshes this menu.
    # Returns this instance (self) of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog().refresh()
    #
    def refresh(self):
        self.apcpdu.send("")
        return self

    # Gets the next page of the Event Log.
    # Returns this instance (self) of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog().next()
    #
    def next(self):
        self.apcpdu.send(" ", False)
        return self

    # Gets the previous page or refreshes the Event Log.
    # Returns this instance (self) of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog().back()
    #
    def back(self):
        self.apcpdu.send("b", False)
        return self

    # Deletes all entries in the Event Log.
    # Returns this instance (self) of apcpdu.menuEventLog.
    #
    # Example/s:
    #     * apcpdu.menu().eventlog().delete()
    #
    def delete(self):
        self.apcpdu.send("dyes")
        return self
