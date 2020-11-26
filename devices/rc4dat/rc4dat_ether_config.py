# prog_atten_ether_config.py

from rc4dat_usb import RC4DATUSB

# This function will set the configuration variables for a MiniCircuits RC4DAT
# programmable attenuator. It is not included with the code that interfaces
# with the programmable attenuator because configuration doesn't happen often.
# Also the manufacturer provides a graphical utility that can change the
# configuration.
def configRC4DATEthernet(port,ip=None,gateway=None,netmask=None,nameserver=None):
    config = RC4DATUSB(port)
    output = []
    if config.Open():
        if validateIP(ip):
            config.Write("SET IP "+ip)
            output.append(config.Read())
        if validateIP(gateway):
            config.Write("SET GATEWAY "+gateway)
            output.append(config.Read())
        if validateIP(netmask):
            config.Write("SET NETMASK "+netmask)
            output.append(config.Read())
        if validateIP(nameserver):
            config.Write("SET NAMESERVER "+nameserver)
            output.append(config.Read())
        config.Close()
        return output
    else:
        return False

def validateIP(ip):
    try:
        parts = ip.split('.')
        return len(parts) == 4 and all(0 <= int(part) < 256 for part in parts)
    except ValueError:
        return False # one of the 'parts' not convertible to integer
    except (AttributeError, TypeError):
        return False # `ip` isn't even a string
