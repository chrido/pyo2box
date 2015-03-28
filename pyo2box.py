"""
Module to communicate with a O2 Box 1421, similar to https://hilfe.o2online.de/docs/DOC-1332
"""

import sys
import requests
import logging
from collections import namedtuple

wlandevice = namedtuple('WlanDevice', ['mac', 'signal', 'link_rate'])

LOGGER = logging.getLogger(__name__)

class O2Box(object):
    def __init__(self, host, password):
        self.baseurl = "http://{}".format(host)
        self.password = password

    def get_wireless_devices(self):
        """
        Returns a list of wireless devices connected to the router

        """
        payload = {
            'controller': 'Overview',
            'action': 'Login',
            'id': '0',
            'idTextPassword': self.password
        }

        try:
            with requests.Session() as s:
                p = s.post(self.baseurl + '/cgi-bin/Hn_login.cgi', data=payload)
                lanoverview = s.get(self.baseurl + '/lan_overview.htm')

                #log immediately out, access is blocked if not
                s.get(self.baseurl + '/cgi-bin/Hn_logout.cgi')

                lines = lanoverview.text.split('\n')

                clientlines = list(filter(lambda l: 'STA_infos[' in l and 'lan_client_t' not in l, lines))
                client_cnt = int(len(clientlines)/4)

                def extract_client_infos():
                    for i in range(0, client_cnt):
                        cclines = map(lambda cc: cc.split('.')[1], (filter(lambda l: '[%i]' %i in l, clientlines)))
                        cleaned = list(map(lambda cc: cc.replace(';','').split('='), cclines))
                        properties = dict()
                        for key, val in cleaned:
                            if key =='mac':
                                macs = val.replace('[', '').replace(']', '').replace('\'', '').split(',')
                                mac = ':'.join(macs)
                            if key == 'RSSI':
                                signal = int(val)
                            if key == 'rate':
                                link_rate = int(val)

                        yield wlandevice(mac, signal, link_rate)

                return list(extract_client_infos())
        except:
            LOGGER.exception('error occured while getting wlan devices from router')
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) != 3:
        print("To get wireless devices: python pyo2box.py <host> <password>")
    else:
        host, password = sys.argv[1:]

        o2box = O2Box(host, password)
        devices = o2box.get_wireless_devices()

        if devices is None:
            print("Error occured")
        else:
            for dev in devices:
                print(dev)
