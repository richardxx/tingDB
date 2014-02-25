"""
    This module takes charges of creating DB plans.
    By richardxx, 2014.1
"""
__author__ = 'richardxx'


import tingDB_service
import plan_query
import time

# Generated sub-plans are cached in the queue
__servers_queue = []


def create_plan(username, plan_options):
    """
        Synthesize a server description according to specified options.
        It should intelligently decide the server locations for best computing resource utilization and throughput.
    """
    plan_type = plan_options["type"]

    if plan_type == "single":
        server_doc = __synthesize_single_server(username)

    elif plan_type == "replicaset":
        replicaset_options = plan_options.get("replica_set", None)
        server_doc = __synthesize_replica_set(username, replicaset_options)

    elif plan_type == "shard_cluster":
        shard_options = plan_options.get("shard_cluster", None)
        replicaset_options = plan_options.get("replica_set", None)
        server_doc = __synthesize_shard_cluster(username, shard_options, replicaset_options)

    else:
        raise Exception("Unrecognized plan")

    print "Server descriptor has been built"
    print server_doc

    if server_doc is None:
        __clear_servers()
        return False

    # Create plan record
    plan_name = server_doc["_id"]

    if __save_plan(plan_name, username, plan_options["max_disk_size"], plan_type) is True:
        print "Create plan successfully"
    else:
        __clear_servers()
        return False

    # Now we start the new plan
    __save_servers()
    col_name = get_collection_name_for_plan_type(plan_options["type"])
    plan_query.change_plan_status(plan_name, "online", col_name)

    return True


def get_collection_name_for_plan_type(plan_type):
    """
        We use servers and clusters collection to store the server descriptors.
        Servers contains only single machine servers, clusters contains replicaset and sharding clusters.
    """
    if plan_type == "single":
        return "servers"

    return "clusters"


###########################################################################
###############  Module private functions #################################
###########################################################################
def __synthesize_single_server(username, server_type="normal"):
    """
        Synthesize a plan for single mongod server.
        server_type could be: normal, mongos, configsvr, arbiter
        Return the address of this server
    """

    # We first construct the options passed to mongod
    cmdOptions = {
        "port": "",
        "directoryperdb": True,
        "nojournal": True if server_type == "arbiter" else False,
        "nohttpinterface": False if server_type == "normal" else False,
        "oplogSize": 512,
        "smallfiles": True
    }

    server_doc = {
        "description": __get_description(username, "single"),
        "address": "",
        "cmdOptions": cmdOptions
    }

    # Currently, we don't have support for opening standalone service
    # All services are shared on our machines
    hostname, port = tingDB_service.get_available_host(username)
    if port == -1: return None

    cmdOptions["port"] = port

    address = hostname + ":" + str(port)
    server_doc["address"] = address

    print "available host: %s" % address

    dbpath = "~/mongodb-data/%s-%d" % (username, port)
    if server_type == "mongos":
        server_doc["serverHome"] = dbpath + "-mongos"
    else:
        cmdOptions["dbpath"] = dbpath

    # Put this instance into database
    __register_server(server_doc, "servers")
    return server_doc


def __synthesize_replica_set(username, replicaset_options):
    if replicaset_options is None:
        print "Error: Replicaset options cannot be None."
        return None

    replicaset_doc = {
        "description": __get_description(username, "replicaset"),
        "members": []
    }

    i = 0
    n_members = replicaset_options["members"]
    while i < n_members:
        server_ref = __create_dbref_for_server(username, "normal")
        replicaset_doc["members"].append(server_ref)
        i += 1

    use_arbiter = replicaset_options["arbiter"]
    if use_arbiter:
        server_ref = __create_dbref_for_server(username, "arbiter")
        replicaset_doc["members"].append(server_ref)

    __register_server(replicaset_doc, "clusters")
    return replicaset_doc


def __synthesize_shard_cluster(username, shard_options, replicaset_options=None):
    if shard_options is None:
        print "Error: Shards options cannot be None"
        return None

    if shard_options["shards_type"] == "replicaset" and replicaset_options is None:
        print "Error: Replica options cannot be None when type of shard is replicaset."
        return None

    shard_cluster_doc = {
        "description": __get_description(username, "replicaset"),
        "members": [],
        "configServers": [],
        "shards": []
    }

    i = 0
    n_configs = shard_options["configs"]
    while i < n_configs:
        server_ref = __create_dbref_for_server(username, "configsvr")
        shard_cluster_doc["configServers"].append(server_ref)
        i += 1

    i = 0
    n_members = shard_options["members"]
    while i < n_members:
        server_ref = __create_dbref_for_server(username, "mongos")
        shard_cluster_doc["members"].append(server_ref)
        i += 1

    i = 0
    n_shards = shard_options["shards"]
    shards_type = shard_options["shards_type"]
    while i < n_shards:
        _ref = None

        if shards_type == "single":
            _ref = __create_dbref_for_server(username, "normal")
        else:
            _ref = __create_dbref_for_replicaset(username, replicaset_options)

        shard_cluster_doc["shards"].append(_ref)
        i += 1

    __register_server(shard_cluster_doc, "clusters")
    return shard_cluster_doc


def __create_dbref_for_server(username, server_type="normal"):
    """
        Built a new server and create a DBRef to it.
    """
    server_ref = {
        "server": {
            "$ref": "servers",
            "$id": ""
        },
        "arbiterOnly": True if server_type == "arbiter" else False
    }

    server_doc = __synthesize_single_server(username, server_type)
    server_ref["server"]["$id"] = server_doc["_id"]
    return server_ref


def __create_dbref_for_replicaset(username, replicaset_options):
    """
        Built a DBRef to a newly created replicaset.
    """
    cluster_ref = {
        "server": {
            "$ref": "clusters",
            "$id": ""
        }
    }

    cluster_doc = __synthesize_replica_set(username, replicaset_options)
    cluster_ref["server"]["$id"] = cluster_doc["_id"]
    return cluster_ref


def __save_plan(plan_name, username, max_disk_size, plan_type):
    """
        Save the generated plan to database.
    """
    try:
        plan_doc = {
            "_id": plan_name,
            "owner": username,
            "max_disk_size": max_disk_size,
            "type": plan_type,
            "status": "offline"
        }

        plans_collection = tingDB_service.get_config_collection("plans")
        plans_collection.insert(plan_doc)

    except Exception, e:
        return False

    return True


def __register_server(server_doc, _type):
    """
        We put this server descriptor into our servers queue.
        We will commit all the servers in one run.
        "type" could only be: servers and clusters.
    """
    global __servers_queue

    __servers_queue.append({
        "server_doc": server_doc,
        "type": _type
    })


def __save_servers():
    """
        Save the plan instances into database.
    """
    global __servers_queue
    config_db = tingDB_service.get_config_db()

    for plan in __servers_queue:
        plan_doc = plan["server_doc"]
        _type = plan["type"]
        plan_collection = config_db[_type]
        plan_collection.insert(plan_doc)


def __clear_servers():
    global __servers_queue
    __servers_queue = []


def __get_description(username, _type):
    return "plan_type = %s, owner = %s, time = %s" % \
           (_type, username, time.strftime("%d/%m/%Y"))
