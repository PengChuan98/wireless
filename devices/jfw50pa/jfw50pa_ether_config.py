# prog_atten_ether_config.py

from jfw50pa_serial import JFW50PASerial

# This function will set the configuration variables for a JFW 50PA-513
# programmable attenuator. It is not included with the code that interfaces
# with the programmable attenuator because configuration doesn't happen often.
# Also the manufacturer provides a graphical utility that can change the
# configuration.
def configJFW50PAEthernet(port,ip=None,gateway=None,netmask=None,nameserver=None):
    config = JFW50PASerial(port)
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
