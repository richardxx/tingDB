"""
    Manage computing resources and handle the connections to operation server.
    by richardxx, 2014.1
"""
__author__ = 'richardxx'

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import plan_composer
import globals
import cloud_simulator
import time
import httplib
import urllib


# host address for this TingDB service
__ting_service_host = "localhost"
# Port of our TingDB service
__ting_service_port = 30000
# Port of the operational service
__ting_service_ops_port = 30001

# host address for our service database
__ting_service_db_host = "localhost"
# Port of out service database
__ting_service_db_port = 27017
__ting_service_db_name = "TingDBService"


# Internal variables, don't access them directly outside this module
__service_conn = None
__service_config_db = None


def init_service():
    """
        Start the TingDB service.
    """
    global __service_conn
    global __service_config_db

    try_times = 0
    while try_times < globals.MAX_TRYOUT_TIME and __service_conn is None:
        try:
            __service_conn = MongoClient(__ting_service_db_host, __ting_service_db_port)
        except ConnectionFailure, e:
            # Perhaps the database is not opened
            # We open it
            if __open_service_db() is False: return False

        try_times += 1

    if try_times == globals.MAX_TRYOUT_TIME:
        return False

    # Locate our service db
    __service_config_db = __service_conn["tingDBService"]

    # Rebuild the service if needed
    if cloud_simulator.test_hosts_integrity() is False:
        __clear_service_db()
        cloud_simulator.load_hosts()

    return True


def shutdown_service():
    global __service_conn
    global __service_config_db

    __service_conn.close()
    __service_config_db = None
    __service_conn = None

    __close_service_db()


def get_config_db():
    return __service_config_db


def get_config_collection(col_name):
    return __service_config_db[col_name]


def get_service_ops_address():
    """
        The operational service is located at the same host with service db.
    """
    return "%s:%d" % (__ting_service_db_host, __ting_service_ops_port)


def get_available_host(username):
    """
        Search for an available machine for holding this service.
        Once successfully found a host, the returned port of that host is labeled used.
        Note that this operation MUST be atomic.
    """
    hosts_collection = __service_config_db["hosts"]
    host = None
    try_times = 0

    while try_times < globals.MAX_TRYOUT_TIME:
        # We the field ports_left as the pseudo lock
        host = hosts_collection.find_and_modify(query={"ports_left": {"$gt": 0}},
                                                update={"$set": {"ports_left": 0}})
        if host is not None:
            # This query selects only one of the matched document randomly
            #TODO: We should select the host by the load balance
            break

        # Fail is perhaps caused by contention (some connections are modifying the database)
        # We sleep for 40ms
        time.sleep(0.04)
        try_times += 1

    if try_times == globals.MAX_TRYOUT_TIME:
        # There is no available machine left
        return "", -1

    # Now get the first available port from the list
    ports_map = host["ports_map"]
    port_index = 0
    while ports_map[port_index] == -1:
        port_index += 1

    # There MUST be at least one available port
    ports_left = host["ports_left"] - 1
    free_port = ports_map[port_index]

    # Update to database
    hosts_collection.update({"_id": host["_id"]},
                            {"$set": {"ports_map.%d" % port_index: -1,
                                      "ports_left": ports_left}})

    return host["hostname"], free_port


def return_port(host, port):
    """
        Free the port that was occupied.
    """
    hosts_collection = __service_config_db["hosts"]
    host = None
    try_times = 0

    while try_times < globals.MAX_TRYOUT_TIME:
        # We the field ports_left as the pseudo lock
        host = hosts_collection.find_and_modify(query={"_id": host, "ports_left": {"$gt": 0}},
                                                update={"$set": {"ports_left": 0}})
        if host is not None:
            break

        # Fail is perhaps caused by contention (some connections are modifying the database)
        # We sleep for 40ms
        time.sleep(0.04)
        try_times += 1

    if try_times == globals.MAX_TRYOUT_TIME:
        # There is no available machine left
        return False

    # Reset
    port_index = port - globals.DEFAULT_USER_PORT_MIN
    ports_left = host["ports_left"] + 1
    hosts_collection.update({"_id": host["_id"]},
                            {"$set": {"ports_map.%d" % port_index: port,
                                      "ports_left": ports_left}})

    return True


def send_request_to_op(plan_name, command = "op-start", _type = "servers"):
    """
        Send commands to operation server.
    """
    ret_data = ""

    try:
        params = urllib.urlencode({
            'plan_name': plan_name,
            'plan_type': _type
        })

        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection(get_service_ops_address())
        conn.request("POST", "/" + command, params, headers)

        # Perhaps the operational service is down due to errors
        conn.sock.settimeout(5.0)
        response = conn.getresponse()
        ret_data = response.read()

    except Exception, e:
        print "Perhaps the operational service is not on."

    return ret_data


###########################################################################
#####  Module private functions ###########################################
###########################################################################

def __open_service_db():
    ret_data = plan_composer.start_plan(__ting_service_db_name)
    return ret_data is not ""


def __close_service_db():
    ret_data = plan_composer.stop_plan(__ting_service_db_name)
    return ret_data is not ""


def __clear_service_db():
    """
        Returns to the start of the world
    """
    collection_names = __service_config_db.collection_names()

    for col_name in ["servers", "clusters", "hosts", "plans"]:
        if col_name in collection_names:
            col = __service_config_db[col_name]
            col.remove()
