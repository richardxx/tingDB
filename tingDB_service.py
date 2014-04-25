"""
    Entry point for the tingDB service.
    It manages computing resources and handle the connections to operation server.
    by richardxx, 2014.1
"""
__author__ = 'richardxx'

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import sys
import plan_query
import globals
import cloud_simulator
import time
import httplib
import urllib
import signal


# host address for this TingDB service
__ting_service_host = "localhost"
# Port of our TingDB service
__ting_service_port = 30000
# Port of the operational service
__ting_service_ops_port = 30001


# The plan we should connect to
__tingDB_server_name = "tingDB"
# host address for our service database
__tingDB_host = "localhost"
# Port of out service database
__tingDB_port = 27017
# The config database
__tingDB_config_db = "tingDBService"


# Internal variables, don't access them directly outside this module
__tingDB_conn = None
__tingDB_config_db_conn = None


def init_service():
    """
        Start the TingDB service.
    """

    # Connect or start the service db
    __connect_service_db()

    # Rebuild the service if needed
    if cloud_simulator.test_hosts_integrity() is False:
        __clear_service_db()
        cloud_simulator.load_hosts()

    # Install the signal handlers (e.g. handling Ctrl+C)
    __setup_handlers();

    return True


def shutdown_service():
    """
        Close the tingDB service.
    """
    global __tingDB_conn
    global __tingDB_config_db_conn

    __tingDB_conn.close()
    __tingDB_config_db_conn = None
    __tingDB_conn = None

    __close_service_db()


def get_config_db():
    if __tingDB_conn is None or __tingDB_conn.alive() is False:
        # Always be sure the database is open
        __connect_service_db()

    return __tingDB_config_db_conn


def get_config_collection(col_name):
    # Return a reference to specified collection
    return get_config_db()[col_name]


def get_service_ops_address():
    """
        The operational service is located at the same host with service db.
    """
    return "%s:%d" % (__tingDB_host, __ting_service_ops_port)


def get_available_host(username):
    """
        Search for an available machine for holding this service.
        Once successfully found a host, the returned port of that host is labeled used.
        Note that this operation MUST be atomic.
    """
    hosts_collection = __tingDB_config_db_conn["hosts"]
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
    hosts_collection = __tingDB_config_db_conn["hosts"]
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


def send_request_to_op(plan_name, command, _type = "servers"):
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

        # Perhaps the operation server is down due to errors
        # Therefore, we need a timeout test
        conn.sock.settimeout(globals.MAX_DB_CONNECTION_TIMEOUT)
        response = conn.getresponse()
        ret_data = response.read()

    except Exception, e:
        print "Perhaps the operation service is off. Please turn it on first"

    return ret_data


###########################################################################
#####  Module private functions ###########################################
###########################################################################
def __connect_service_db():
    global __tingDB_conn
    global __tingDB_config_db_conn

    # We try to connect to our the database used by our own
    try:
        __tingDB_conn = MongoClient(__tingDB_host, __tingDB_port)
    except ConnectionFailure, e:
        # Perhaps the database is not opened
        # We try to open it
        if __start_service_db() is False:
            sys.exit(-1)

    try_times = 0
    while __tingDB_conn is None and try_times < globals.MAX_TRYOUT_TIME:
        try:
            __tingDB_conn = MongoClient(__tingDB_host, __tingDB_port)
        except ConnectionFailure, e:
            time.sleep(3)

        try_times += 1

    if try_times == globals.MAX_TRYOUT_TIME:
        sys.exit(-1)

    # Locate our service db
    __tingDB_config_db_conn = __tingDB_conn[__tingDB_config_db]


def __start_service_db():
    # Start the mongodb service
    ret_data = plan_query.start_plan(__tingDB_server_name)
    return ret_data is not ""


def __close_service_db():
    ret_data = plan_query.stop_plan(__tingDB_config_db)
    return ret_data is not ""


def __clear_service_db():
    """
        Returns to the start of the world
    """
    collection_names = __tingDB_config_db_conn.collection_names()

    for col_name in ["servers", "clusters", "hosts", "plans"]:
        if col_name in collection_names:
            col = __tingDB_config_db_conn[col_name]
            col.remove()


def __setup_handlers():
     signal.signal(signal.SIGINT, __sigint_handler)


def __sigint_handler(signal, frame):
    print "You press CTRL+C to terminate this program"
    shutdown_service()
    exit(0)
