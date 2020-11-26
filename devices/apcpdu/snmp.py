################################################################################
# File Name: snmp.py
# Author:    Kevin DeRossett
# Email:     kevin.derossett@hp.com
#
# Purpose of library:
# - The 'snmp' module provides easy to use methods for the PDU's SNMP interface.
#
################################################################################
# Release Notes:
#
# ----- August/14/2014 - Kevin DeRossett-------------------------------------
# - Initial release.
#     * Send SNMP packets to control PDU.
################################################################################

import logging; logger = logging.getLogger(__name__)
from pysnmp.entity.rfc3413.oneliner import cmdgen; cmdGen = cmdgen.CommandGenerator()
from pysnmp.proto import rfc1902

def GET(apcpdu, oid):
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
        cmdgen.CommunityData(apcpdu.username, mpModel=0),
        cmdgen.UdpTransportTarget((apcpdu.host, apcpdu.port)),
        oid,
    )
    # Check for errors and print out results
    if errorIndication:
        logger.debug(errorIndication)
    else:
        if errorStatus:
            logger.debug('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex)-1] or '?'))
        else:
            for name, val in varBinds:
                logger.debug('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
            return varBinds[0][1]

def SET(apcpdu, oid, value):
    errorIndication, errorStatus, errorIndex, varBinds = cmdGen.setCmd(
        cmdgen.CommunityData(apcpdu.password, mpModel=0),
        cmdgen.UdpTransportTarget((apcpdu.host, apcpdu.port)),
        (oid, value),
    )
    # Check for errors and print out results
    if errorIndication:
        logger.debug(errorIndication)
    else:
        if errorStatus:
            logger.debug('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex)-1] or '?'))
        else:
            for name, val in varBinds:
                logger.debug('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
            return varBinds[0][1]

class snmp(object):

    # Init...
    def __init__(self, apcpdu):
        self.apcpdu = apcpdu

    # .iso.org.dod.internet.mgmt.mib-2.system.sysDescr
    def sysDescr(self):
        """
A textual description of the entity. This value should include the full name and
version identification of the system's hardware type, software operating-system,
and networking software. It is mandatory that this only contain printable ASCII
characters.
"""
        return GET(self.apcpdu, '1.3.6.1.2.1.1.1.0')

    # .iso.org.dod.internet.mgmt.mib-2.system.sysObjectID
    def sysObjectID(self):
        """
The vendor's authoritative identification of the network management subsystem
contained in the entity. This value is allocated within the SMI enterprises
subtree (1.3.6.1.4.1) and provides an easy and unambiguous means for determining
`what kind of box' is being managed. For example, if vendor `Flintstones, Inc.'
was assigned the subtree 1.3.6.1.4.1.4242, it could assign the identifier
1.3.6.1.4.1.4242.1.1 to its `Fred Router'.
"""
        return GET(self.apcpdu, '1.3.6.1.2.1.1.2.0')

    # .iso.org.dod.internet.mgmt.mib-2.system.sysUpTime
    def sysUpTime(self):
        """
The time (in hundredths of a second) since the network management portion of the
system was last re-initialized.
"""
        return GET(self.apcpdu, '1.3.6.1.2.1.1.3.0')

    # .iso.org.dod.internet.mgmt.mib-2.system.sysContact
    def sysContact(self, value=None):
        """
The textual identification of the contact person for this managed node, together
with information on how to contact this person. If no contact information is
known, the value is the zero-length string.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.2.1.1.4.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.2.1.1.4.0', rfc1902.OctetString(value))

    # .iso.org.dod.internet.mgmt.mib-2.system.sysName
    def sysName(self, value=None):
        """
An administratively-assigned name for this managed node. By convention, this is
the node's fully-qualified domain name. If the name is unknown, the value is the
zero-length string.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.2.1.1.5.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.2.1.1.5.0', rfc1902.OctetString(value))

    # .iso.org.dod.internet.mgmt.mib-2.system.sysLocation
    def sysLocation(self, value=None):
        """
The physical location of this node (e.g., `telephone closet, 3rd floor'). If the
location is unknown, the value is the zero-length string.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.2.1.1.6.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.2.1.1.6.0', rfc1902.OctetString(value))

    # .iso.org.dod.internet.mgmt.mib-2.system.sysServices
    def sysServices(self):
        """
A value which indicates the set of services that this entity may potentially
offers. The value is a sum. This sum initially takes the value zero, Then, for
each layer, L, in the range 1 through 7, that this node performs transactions
for, 2 raised to (L - 1) is added to the sum. For example, a node which performs
only routing functions would have a value of 4 (2^(3-1)). In contrast, a node
which is a host offering application services would have a value of
72 (2^(4-1) + 2^(7-1)). Note that in the context of the Internet suite of
protocols, values should be calculated accordingly:

layer functionality
1 physical (e.g., repeaters)
2 datalink/subnetwork (e.g., bridges)
3 internet (e.g., supports the IP)
4 end-to-end (e.g., supports the TCP)
7 applications (e.g., supports the SMTP)

For systems including OSI protocols, layers 5 and 6 may also be counted.
"""
        return GET(self.apcpdu, '1.3.6.1.2.1.1.7.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUIdent.sPDUIdentHardwareRev
    def sPDUIdentHardwareRev(self):
        """
The hardware revision of the PDU. This value is set at the factory.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.1.1.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUIdent.sPDUIdentFirmwareRev
    def sPDUIdentFirmwareRev(self):
        """
An 8 byte ID string identifying the PDU firmware revision. This value is set at
the factory.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.1.2.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUIdent.sPDUIdentDateOfManufacture
    def sPDUIdentDateOfManufacture(self):
        """
The date when the PDU was manufactured in mm/dd/yy format. This value is set at
the factory. The year 2000 will be represented by 00.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.1.3.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUIdent.sPDUIdentModelNumber
    def sPDUIdentModelNumber(self):
        """
A 10-character string identifying the model number of the PDU internal. This
value is set at the factory.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.1.4.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUIdent.sPDUIdentSerialNumber
    def sPDUIdentSerialNumber(self):
        """
A 12-character string identifying the serial number of the PDU internal
microprocessor. This value is set at the factory.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.1.5.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterControl.sPDUMasterControlSwitch
    def sPDUMasterControlSwitch(self, value=None):
        """
Setting this OID to turnAllOnNow (1) will turn all outlets on immediately.

Setting this OID to turnAllOnSequence (2) will turn all outlets on as defined by
each outlet's sPDUOutletPowerOnTime OID value.

Setting this OID to turnAllOff (3) will turn all outlets off immediately.

Setting this OID to rebootAllNow (4) will reboot all outlets immediately.

For MasterSwitch firmware version 1.X, setting this OID to rebootAllSequence (5)
reboots all outlets, with power returned to the outlets in the sequence defined
by each outlet's sPDUOutletPowerOnTime OID value.

For MasterSwitch firmware version 2.X, setting this OID to rebootAllSequence (5)
will cause a turnAllOffSequence to be performed. Once all outlets are off, the
MasterSwitch will then delay the sPDUMasterConfigReboot OID time, and then
perform a turnAllOnSequence. 

For MasterSwitch firmware version 2.X, setting this OID to
turnAllOffSequence (7) will turn all outlets off as defined by each outlet's
sPDUOutletPowerOffTime OID value.

For MasterSwitch firmware version 1.X, setting this OID to
turnAllOffSequence (7) will have no effect.

Getting this OID will return the noCommand (6) value.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.2.1.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.2.1.0', rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterControl.sPDUMasterState
    def sPDUMasterState(self):
        """
Getting this OID will cause the status of all outlets to be returned. This OID
is provided for informational purposes only. To change the outlet state, the
user should use the sPDUOutletCtl OID in the sPDUOutletControlTable.

The format of the data returned is a character string consisting of the word
'On' if the outlet is on or 'Off' if the outlet is off. At least one space will
delimit each outlet entry in the string. 

If the outlet states are unknown, the character string 'Unknown' will be
returned. This signifies that there is an inconsistency in the PDU. In the rare
case that this should happen, the user is advised to shut down all equipment
powered by the PDU and then cycle the PDU's power. This will put the PDU in a
consistent state.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.2.2.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterControl.sPDUMasterPending
    def sPDUMasterPending(self):
        """
Getting this OID will cause the command pending status of all outlets to be
returned.

The format of the data returned is a character string consisting of the word
'Yes' if a command is pending for the outlet or 'No' if there is no command
pending for the outlet. At least one space will delimit each outlet entry in the
string. 

If the pending states are unknown, the character string 'Unknown' will be
returned. This signifies that there is an inconsistency in the PDU. In the rare
case that this should happen, the user is advised to shut down all equipment
powered by the PDU and then cycle the PDU's power. This will put the PDU in a
consistent state.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.2.3.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterConfig.sPDUMasterConfigPowerOn
    def sPDUMasterConfigPowerOn(self, value=None):
        """
The amount of delay, in seconds, between when power is provided to the PDU and
when the PDU provides basic master power to the outlets.

Allowed values are:

-1 never apply power automatically.
0 apply power immediately.
15 apply power in 15 seconds.
30 apply power in 30 seconds.
45 apply power in 45 seconds.
60 apply power in 60 seconds (1 minute).
120 apply power in 120 seconds (2 minutes).
300 apply power in 300 seconds (5 minutes).

If a value other than a supported value is provided in a set request, the PDU
interprets it as the next lower acceptable value. If the provided value is lower
than the lowest acceptable value, the lowest acceptable value is used.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.1.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.1.0', rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterConfig.sPDUMasterConfigReboot
    def sPDUMasterConfigReboot(self, value=None):
        """
During a reboot sequence, power is turned off and then back on. This OID defines
the amount of time to wait, in seconds, after turning the power off, at the
start of the sequence, before turning power back on, at the end of the reboot
sequence.

Allowed values are:

5 wait 5 seconds between off/on.
10 wait 10 seconds between off/on.
15 wait 15 seconds between off/on.
20 wait 20 seconds between off/on.
30 wait 30 seconds between off/on.
45 wait 45 seconds between off/on.
60 wait 60 seconds (1 minute) between off/on.

If a value other than a supported value is provided in a set request, the PDU
interprets it as the next lower acceptable value. If the provided value is lower
than the lowest acceptable value, the lowest acceptable value is used.

This OID is read-only for the MasterSwitch version 2.X and is the maximum
sPDUOutletRebootDuration OID of the individual outlets.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.2.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.2.0', rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUMasterConfig.sPDUMasterConfigPDUName
    def sPDUMasterConfigPDUName(self, value=None):
        """
The name of the PDU.
"""
        # 
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.3.0')
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.3.3.0', rfc1902.OctetString(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletControl.sPDUOutletControlTableSize
    def sPDUOutletControlTableSize(self):
        """
The number of outlets for the PDU.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.4.1.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletControl.sPDUOutletControlTable.sPDUOutletControlEntry.sPDUOutletPending
    def sPDUOutletPending(self, portIndex=1):
        """
Reports whether the current outlet has a pending command.

If the commandPendingUnknown (3) value is returned, all devices powered by the
PDU should be shut down. The PDU's power should then be cycled to clear this
condition.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.4.2.1.2.'+str(portIndex))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletControl.sPDUOutletControlTable.sPDUOutletControlEntry.sPDUOutletCtl
    def sPDUOutletCtl(self, portIndex=1, value=None):
        """
Getting this variable will return the outlet state. If the outlet is on, the
outletOn (1) value will be returned. If the outlet is off, the outletOff (2)
value will be returned. 

If the state of the outlet cannot be determined, the outletUnknown (4) value
will be returned. If the outletUnknown condition should occur, all devices
powered by the PDU should be shut down. The PDU's power should then be cycled to
clear this condition.

Setting this variable to outletOn (1) will turn the outlet on.

Setting this variable to outletOff (2) will turn the outlet off. 

Setting this variable to outletReboot (3) will reboot the outlet.

Setting this variable to outletOnWithDelay (5) will turn the outlet on after the
sPDUOutletPowerOnTime OID has elapsed. This option is not valid for MasterSwitch
firmware version 1.X.

Setting this variable to outletOffWithDelay (6) will turn the outlet off after
the sPDUOutletPowerOffTime OID has elapsed. This option is not valid for
MasterSwitch firmware version 1.X.

Setting this variable to outletRebootWithDelay (7) will turn the outlet off
after the sPDUOutletPowerOffTime OID has elapsed, wait the
sPDUOutletRebootDuration OID time, then turn the outlet back on. This option is
not valid for MasterSwitch firmware version 1.X.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.4.2.1.3.'+str(portIndex))
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.4.2.1.3.'+str(portIndex), rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletControl.sPDUOutletControlTable.sPDUOutletControlEntry.sPDUOutletCtlName
    def sPDUOutletCtlName(self, portIndex=1):
        """
The name of the outlet. Maximum size is 20 characters. This OID is provided for
informational purposes only. This value is set by the sPDUOutletName OID.
"""
        return GET(self.apcpdu, '.1.3.6.1.4.1.318.1.1.4.4.2.1.4.'+str(portIndex))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletConfig.sPDUOutletConfigTableSize
    def sPDUOutletConfigTableSize(self):
        """
The number of outlets for the PDU.
"""
        return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.1.0')

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletConfig.sPDUOutletConfigTable.sPDUOutletConfigEntry.sPDUOutletPowerOnTime
    def sPDUOutletPowerOnTime(self, portIndex=1, value=None):
        """
The amount of time (in seconds) the outlet will delay powering on when the
MasterSwitch is powered on.

Allowed values are:

-1 never power on automatically.
0 power on with the Master Switch.
15 power on 15 seconds after the MasterSwitch has power applied.
30 power on 30 seconds after the MasterSwitch has power applied.
45 power on 45 seconds after the MasterSwitch has power applied.
60 power on 60 seconds (1 minute) after the MasterSwitch has power applied.
120 power on 120 seconds (2 minutes) after the MasterSwitch has power applied.
300 power on 300 seconds (5 minutes) after the MasterSwitch has power applied.

If a value other than a supported value is provided in a set request, the PDU
interprets it as the next lower acceptable value. If the provided value is lower
than the lowest acceptable value, the lowest acceptable value is used.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.2.'+str(portIndex))
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.2.'+str(portIndex), rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletConfig.sPDUOutletConfigTable.sPDUOutletConfigEntry.sPDUOutletName
    def sPDUOutletName(self, portIndex=1, value=None):
        """
The name of the outlet. Maximum size is 20 characters.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.3.'+str(portIndex))
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.3.'+str(portIndex), rfc1902.OctetString(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletConfig.sPDUOutletConfigTable.sPDUOutletConfigEntry.sPDUOutletPowerOffTime
    def sPDUOutletPowerOffTime(self, portIndex=1, value=None):
        """
The amount of time (in seconds) the outlet will delay powering off.

Allowed values are:

-1 never power off automatically.
0 power off with the MasterSwitch.
15 power off 15 seconds after being commanded.
30 power off 30 seconds after being commanded.
45 power off 45 seconds after being commanded.
60 power off 60 seconds (1 minute) after being commanded.
120 power off 120 seconds (2 minutes) after being commanded.
300 power off 300 seconds (5 minutes) after being commanded.

If a value other than a supported value is provided in a set request, the PDU
interprets it as the next lower acceptable value. If the provided value is lower
than the lowest acceptable value, the lowest acceptable  value is used.

This OID is not available for MasterSwitch firmware version 1.X.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.4.'+str(portIndex))
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.4.'+str(portIndex), rfc1902.Integer32(value))

    # .iso.org.dod.internet.private.enterprises.apc.products.hardware.masterswitch.sPDUOutletConfig.sPDUOutletConfigTable.sPDUOutletConfigEntry.sPDUOutletRebootDuration
    def sPDUOutletRebootDuration(self, portIndex=1, value=None):
        """
During a reboot sequence, power is turned off and then 
 back on. This OID defines the amount of time to wait, 
 in seconds, after turning the power off, at the start
 of the sequence, before turning power back on, at the
 end of the reboot sequence. 
 
 Allowed values are:
 
 5 wait 5 seconds between off/on.
 10 wait 10 seconds between off/on.
 15 wait 15 seconds between off/on.
 20 wait 20 seconds between off/on.
 30 wait 30 seconds between off/on.
 45 wait 45 seconds between off/on.
 60 wait 60 seconds (1 minute) between off/on.
 
 If a value other than a supported value is provided in a 
 set request, the PDU interprets it as the next lower
 acceptable value. If the provided value is lower than
 the lowest acceptable value, the lowest acceptable 
 value is used.
 
 This OID is not available for MasterSwitch firmware version 1.X.
"""
        if value is None:
            return GET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.5.'+str(portIndex))
        else:
            return SET(self.apcpdu, '1.3.6.1.4.1.318.1.1.4.5.2.1.5.'+str(portIndex), rfc1902.Integer32(value))
