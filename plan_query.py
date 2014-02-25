"""
    A module that defines how to manipulate the plan config db.
    By richardxx, 2014.1
"""
__author__ = 'richardxx'

import time
import tingDB_service
import plan_composer


def start_plan(plan_name, _type="servers", try_times = 5):
    """
        _type can only be servers and clusters.
    """
    while try_times > 0:
        response = tingDB_service.send_request_to_op(plan_name, "op-start", _type)
        if response != "":
            return response

        time.sleep(1)
        try_times -= 1

    return ""


def stop_plan(plan_name, _type="servers", try_times = 5):
    while try_times > 0:
        response = tingDB_service.send_request_to_op(plan_name, "op-stop", _type)
        if response != "":
            return response

        time.sleep(1)
        try_times -= 1

    return ""


def change_plan_status(plan_name, new_state, plan_type = ""):
    """
        Turn plan on and off.
    """
    plans_collection = tingDB_service.get_config_collection("plans")

    if plan_type == "":
        # We get the type ourselves
        plan_cursor = plans_collection.find({"plan_name": plan_name})
        plan_type = plan_cursor[0]["type"]

    doc_col = plan_composer.get_collection_name_for_plan_type(plan_type)

    if new_state == "online":
        ret_data = start_plan(plan_name, doc_col)
    elif new_state == "offline":
        ret_data = stop_plan(plan_name, doc_col)
    else:
        return False

    if ret_data != "":
        plans_collection.update({"plan_name": plan_name},
                                {"$set": {"status": new_state}})

    return True


def get_plans_for_user(username):
    """
        Returns all the plans for a given user.
    """
    plans_collection = tingDB_service.get_config_collection("plans")
    plans_cursor = plans_collection.find({"owner": username})
    plans = []

    for plan in plans_cursor:
        plans.append(plan)

    return plans


def get_URIs_for_user(username):
    """
        Retrieve the URIs for all the plans for a given user.
    """
    plans = get_plans_for_user(username)
    URIs = []

    for plan in plans:
        uri = tingDB_service.send_request_to_op(plan["_id"], "op-geturi")
        URIs.append(uri)

    return URIs


def __get_server_for_plan(plan):
    """
        Get server descriptor from plan descriptor.
    """
    plan_name = plan["_id"]
    plan_type = plan["type"]
    col_name = plan_composer.get_collection_name_for_plan_type(plan_type)
    servers_collection = tingDB_service.get_config_collection(col_name)

    server_cursor = servers_collection.find({"_id": plan_name})
    return server_cursor[0]


