import importlib
import os
import glob
import re
from AccessPoints import *
from AccessPoints import AccessPointWl


class Death(Exception):
    def __init__(self):
        Exception.__init__(self, 'Invalid Broadcast value')


def give_me_bool_or_give_me_death(dict):
    """Finds the Broadcast field and changes it to a boolean from string

    Args:
        val (dict): Dictionary of parsed config entries

    Returns:
        Dict: Modified dictionary with the boolean instead of string
    """
    if 'Broadcast' in dict:
        if dict['Broadcast'] in ['False', '0']:
            dict['Broadcast'] = False
        elif dict['Broadcast'] in ['True', '1']:
            dict['Broadcast'] = True
        else:
            raise Death()

    return dict


class AccessPointFactory(object):
    def __init__(self):
        pass

    def getAccessPoint(self, ap_name, band='2.4', ip_address=None):
        """Gets an AccessPoint object according to the name given.

        Args:
            ap_name (str): Name of the ap (must match the python file)
            ip_address (str, optional): IP address of the AP
            band (str, optional): Wireless band to operate on (default 2.4)

        Raises:
            ValueError: Description
        """
        if ap_name == 'rtac68u':
            if ip_address:
                return AccessPointWl.AccessPointWl(ip_address=ap_address, band=band)
            else:
                return AccessPointWl.AccessPointWl(band=band)

        try:
            ap_module = importlib.import_module('AccessPoints.{}'.format(ap_name))
            ap = getattr(ap_module, ap_name)
        except:
            print 'Router {} is not supported at this time'.format(ap_name)
            return None
        else:

            """
            Properties:
            router_obj.supported_bands
            router_obj.supported_channels
            router_obj.supported_securities
            router_obj.supported_modes
            router_obj.supported_channel_widths
    
            Functions:
            router_obj.SetBroadcast()
            router_obj.SetChannelWidth()
            router_obj.SetSecurity()
            router_obj.SetMode()
            router_obj.SetChannel()
            """
            if ip_address:
                return ap(ip_address=ip_address, band=band)
            else:
                return ap(band=band)



    def configure_ap(self, config_file):
        """Configures an AP based on the parameters in the given config file

        Args:
            config_file (str): Path to the config file to use

        Returns:
            None: None
        """
        params = self._parse_config_file(config_file)
        ap = self.getAccessPoint(params['Name'], params['Band'], params['IP'])
        # Dont need these any more
        del params['Name']
        del params['Band']
        del params['IP']

        print ap
        for p in params:
            print 'Calling ap.Set{}("{}")'.format(p.title(), params[p])
            setter = getattr(ap, 'Set{}'.format(p))
            setter(params[p])

        ap.Post()


    def _parse_config_file(self, config_file):
        """Grabs the data from a config file and returns a dictionary

        Args:
            config_file (str): Path to the config file to use

        Returns:
            Dict: Dictionary of parameters and their values
        """
        if not os.path.isfile(config_file):
            raise FileNotFoundError('{} does not exist!'.format(config_file))

        # Get the raw file contents
        with open(config_file, 'r') as f:
            raw_data = f.read()

        # Look for the Router portion of the file
        raw_data = raw_data.split('[Router]')[1]

        # Parse each data element into a dictionary
        params = re.findall('(\w+)\s*=\s*(.*)', raw_data)
        final_dict = {p[0]: p[1] for p in params}
        return give_me_bool_or_give_me_death(final_dict)

