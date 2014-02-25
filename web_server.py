# A simple web server for managing database service on cloud
# by richardxx, 2014.1

__author__ = 'richardxx'

import sys
from flask import Flask
from flask import url_for, redirect
from flask import render_template
from flask import request
import ting_user
import plan_composer
import tingDB_service
import plan_query


app = Flask("__name__")
app.config.from_object('config')
app.config['DEBUG'] = True


@app.route("/", methods=['GET', 'POST'])
@app.route("/index", methods=['GET', 'POST'])
def show_index_page():
    user = ting_user.TingUser()

    if request.method == 'POST':
        if user.obtain_user_input():
            action_res = False

            if "signin" in request.form:
                action_res = user.do_login()
            elif "register" in request.form:
                action_res = user.do_register()

            if action_res is True:
                return redirect("%s/console" % user.get_username())

    return render_template("index.html", form=user)


@app.route('/<username>/console', methods=['GET'])
def show_admin_page(username):
    if ting_user.find_user(username) is None:
        return redirect("/")

    return render_template("console.html", userName=username)


@app.route('/<username>/createdb', methods=['GET'])
def show_createdb_page(username):
    if ting_user.find_user(username) is None:
        return redirect("/")

    return render_template("createdb.html", userName=username)


@app.route('/<username>/managedb', methods=['GET'])
def show_managedb_page(username):
    if ting_user.find_user(username) is None:
        return redirect("/")

    # We first get the list of URIs
    URIs = plan_query.get_URIs_for_user(username)
    n_uris = len(URIs)
    return render_template("managedb.html", userName=username, URIs=URIs, n_uris=n_uris)


@app.route('/<username>/dbops_new', methods=['POST'])
def dbops_new(username):
    if ting_user.find_user(username) is None:
        return "lost"

    plan_options = request.form
    return "ok" if plan_composer.create_plan(username, plan_options) is True else "fail"


###########################################################################
#####  Module bootstrap functions #########################################
###########################################################################

if __name__ == "__main__":
    if tingDB_service.init_service() is True:
        # Start web server
        app.run(port=tingDB_service.__ting_service_port)

        # Perhaps this is unreachable at all
        tingDB_service.shutdown_service()


