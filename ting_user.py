"""
    Represents a user instance.
    by richardxx, 2014.1
"""
__author__ = 'richardxx'

from flask.ext.wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import Required, Length
import tingDB_service
import utils


# This class describes a user of your service
# All user related operations should be encapsulated here
class TingUser(Form):
    userNameInputBox = TextField('userName', validators=[Required(), Length(min=4, max=16)])
    passwordInputBox = PasswordField('password', validators=[Required(), Length(min=6, max=12)])

    #Private data
    __username = ""
    __password = ""
    __privilege = ""

    def obtain_user_input(self):
        if self.validate_on_submit():
            self.__username = self.userNameInputBox.data
            self.__password = self.passwordInputBox.data
            return True

        return False

    def do_login(self):
        if self.__has_logged():
            return True, "Logged"

        try:
            db = tingDB_service.get_config_db()
            users = db["users"]
            users = users.find({"name": self.__username})

            # results is in the type of Cursor
            if users.count() == 1:
                user = users.next()
                raw_password = self.__password
                encrypted_password = utils.encrypt_string(raw_password)

                if user["password"] == encrypted_password:
                    register_user_cache(self)
                    return True, "Corrected"

                self.__privilege = user["privilege"]
        except Exception, e:
            # Connect to database failed
            print e.message

        return False, "Wrong user name or password."

    def do_logout(self):
        if self.__has_logged():
            remove_user_cache(self)

    def do_register(self):
        if self.__has_logged():
            # We directly let that user log in
            return True, "Logged"

        try:
            db = tingDB_service.get_config_db()
            users = db["users"]

            # We first lookup if the user has been registered
            user_cursor = users.find({"name": self.__username})
            if user_cursor.count() > 0:
                return False, "This user name has been registered."

            # Prepare for user record
            raw_password = self.__password
            encrypted_password = utils.encrypt_string(raw_password)

            new_user = {
                "name": self.__username,
                "password": encrypted_password,
                "privilege": "normal"
            }

            users.insert(new_user)
            register_user_cache(self)

            return True, "Register successfully."
        except Exception, e:
            print e.message
            # TODO: open the user records server

        return False, "System error, cannot register new user at present."

    def create_db(self, db_name):
        """
            Create a new db and authenticate to it.
        """
        pass

    def get_user_limit(self):
        """
            Create a limit descriptor
        """
        if self.__has_logged() is False: return None

        user_limit = {
            "max_dbs": 0,
            "max_disk_size": 0
        }

        if self.__privilege == "normal":
            user_limit["max_dbs"] = 1
            user_limit["max_disk_size"] = 0.5
        elif self.__privilege == "gold":
            user_limit["max_dbs"] = 10
            user_limit["max_disk_size"] = 50
        elif self.__privilege == "platinum":
            user_limit["max_dbs"] = 100
            user_limit["max_disk_size"] = 500

        return user_limit

    def get_username(self):
        return self.__username

    def __has_logged(self):
        if self.__username == "":
            return False

        return find_user(self.__username) is not None


# A cache for the set of logged in users
__users_list = {}


def register_user_cache(user):
    __users_list[user.get_username()] = user


def remove_user_cache(user):
    __users_list.pop(user.get_username(), None)


def find_user(username):
    return __users_list.get(username, None)

