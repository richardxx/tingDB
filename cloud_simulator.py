"""
    It simulates the cloud management infrastructure.
    It manages all the machines available so far.
"""
__author__ = 'richardxx'

import globals
import service

# __hosts = ["chcpu1", "chcpu3", "chcpu5", "chcpu9"]
__hosts = ["localhost"]


def test_hosts_integrity():
    hosts_collection = service.get_config_collection("hosts")
    for hostname in __hosts:
        host = hosts_collection.find({"hostname": hostname})
        if host.count() == 0:
            return False

    return True


def load_hosts():
    """
        Import hard coded hosts.
    """
    hosts_collection = service.get_config_collection("hosts")

    for h in __hosts:
        record = {
            "hostname": "",
            "ports_left": globals.DEFAULT_USER_PORT_MAX - globals.DEFAULT_USER_PORT_MIN,
            "ports_map": None
        }

        # We insert all the ports descriptors into the document
        ports_map = []
        i = globals.DEFAULT_USER_PORT_MIN
        while i < globals.DEFAULT_USER_PORT_MAX:
            ports_map.append(i)
            i += 1

        # record["hostname"] = h + "cse.ust.hk"
        record["hostname"] = h
        record["ports_map"] = ports_map
        hosts_collection.insert(record)

