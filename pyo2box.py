"""
Module to communicate with a O2 Box 1421, similar to https://hilfe.o2online.de/docs/DOC-1332
"""

import sys
import requests
import logging
from collections import namedtuple

wlandevice = namedtuple('WlanDevice', ['mac', 'name', 'ip', 'signal', 'link_rate'])

LOGGER = logging.getLogger(__name__)


class O2Box(object):
    def __init__(self, host, password):
        self.baseurl = "http://{}".format(host)
        self.password = password

    def _pretty_mac(self, macugly):
        macs = macugly.replace('[', '').replace(']', '').replace('\'', '').split(',')
        return ':'.join(macs)


    def _extract_wireless_info(self, lines):
        """
        Extracts the info of all the wireless devices from the Javascript section of the HTML
        """
        clientlines = list(filter(lambda l: 'STA_infos[' in l and 'lan_client_t' not in l, lines))
        client_cnt = int(len(clientlines) / 4)

        def extract_client_infos():
            for i in range(0, client_cnt):
                cclines = map(lambda cc: cc.split('.')[1], (filter(lambda l: '[%i]' % i in l, clientlines)))
                cleaned = list(map(lambda cc: cc.replace(';', '').split('='), cclines))
                mac = signal = link_rate = None
                for key, val in cleaned:
                    if key == 'mac':
                        mac = self._pretty_mac(val)
                    if key == 'RSSI':
                        signal = int(val)
                    if key == 'rate':
                        link_rate = int(val)

                if mac is not None:
                    yield (mac, (signal, link_rate))

        return dict((m, rest) for m, rest in extract_client_infos())

    def _extract_dhcp_clients(self, lines):
        """
        Extracts all DHCP clients from the Javascript section of the HTML
        """
        clientlines = list(filter(lambda l: 'dhcpclients[' in l and '].' in l, lines))
        dhcp_cnt = int(len(clientlines) / 4)

        def extract_dhcp_clients():
            for i in range(0, dhcp_cnt):
                cclines = map(lambda cc: cc.split('.')[1], (filter(lambda l: '[%i]' % i in l, clientlines)))
                cleaned = list(map(lambda cc: cc.replace(';', '').replace(' ', '').replace('\'', '').split('='), cclines))
                ma = name = ip = None
                for key, val in cleaned:
                    if key == 'name':
                        if val != '':
                            name = val
                    if key == 'mac':
                        ma = self._pretty_mac(val)
                    if key == 'ip':
                        ipparts = val.replace('[', '').replace(']', '').replace(' ', '').split(',')
                        ip = '.'.join(ipparts)

                toyield = (ma, (name, ip))
                yield toyield

        return dict((m, rest) for m, rest in extract_dhcp_clients())

    def _login(self, session):
        """
        Login with current session
        Returns True when sucessful, False when unsuccessful
        """
        payload = {
            'controller': 'Overview',
            'action': 'Login',
            'id': '0',
            'idTextPassword': self.password
        }
        res = session.post(self.baseurl + '/cgi-bin/Hn_login.cgi', data=payload)
        lines = res.text.split('\n')
        for line in lines:
            if 'msgLoginPwd_err' in line:
                return False

        return True

    def _logout(self, session):
        """
        Always immediatly log out again, otherwise access to router would be blocked
        """
        session.get(self.baseurl + '/cgi-bin/Hn_logout.cgi')

    def try_login(self):
        """
        Tries to login and then logout
        Returns true if attemp was successful, false when unsuccessful
        """
        try:
            with requests.Session() as s:
                if self._login(s):
                    self._logout(s)
                    return True
                else:
                    return False
        except:
            LOGGER.exception('error occured while getting wlan devices from router')
            return False


    def get_wireless_devices(self):
        """
        Returns a list of wireless devices connected to the router

        """

        try:
            with requests.Session() as s:
                if not self._login(s):
                    LOGGER.error("login failed")
                    return None

                LOGGER.debug("logged in")

                lanoverview = s.get(self.baseurl + '/lan_overview.htm')
                LOGGER.debug("fetched lan overview")

                # log immediately out, access is blocked if not
                self._logout(s)
                LOGGER.debug("logged out")

                def extract_wireless_information():
                    lines = lanoverview.text.split('\n')

                    dhcpClients = self._extract_dhcp_clients(lines)

                    for k, infos in self._extract_wireless_info(lines).items():
                        if k in dhcpClients:
                            name, ip = dhcpClients[k]
                        else:
                            name = ip = None

                        yield wlandevice(k, name, ip, infos[0], infos[1])

                return list(extract_wireless_information())

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
