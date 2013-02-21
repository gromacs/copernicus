# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import cpc.util.exception
import hashlib
import logging
log=logging.getLogger('cpc.server.state.user_handler')

class UserError(cpc.util.CpcError):
    pass

class UserLevel(object):
    ANONYMOUS = 0
    REGULAR_USER = 1
    SUPERUSER = 2

    def __init__(self, level):
        self.level = level

    def __str__(self):
        if self.level == UserLevel.ANONYMOUS:
            return "Anonymous"
        elif self.level == UserLevel.REGULAR_USER:
            return "Regular user"
        elif self.level == UserLevel.SUPERUSER:
            return "Super user"
        else:
            return "Unknown user level"

def isValidLevel(level):
    """Checks if a given user level is a valid level"""
    return level in UserLevel.__dict__.values()

class User(object):
    """
    Represents a user.
    User data is cached in this instance, but any changes should be written
    to persistent storage immediately. Multiple instances of the same user may
    exist
    """
    def __init__(self, id, name, level):
        self.id = id
        self.name = name
        self.level_obj = UserLevel(level)

    def getUserid(self):
        return self.id

    def getUserlevel(self):
        return self.level_obj.level

    def getUserlevelAsString(self):
        return str(self.level_obj)

    def setUserlevel(self, level):
        self.level_obj = UserLevel(level)
        if not isValidLevel(level):
            raise UserError("Invalid userlevel")
        self.syncUser()

    def isSuperuser(self):
        return self.level_obj.level == UserLevel.SUPERUSER

    def getUsername(self):
        return self.name

    def promote(self):
        """
        Promotes user to the next user level, if available
        Throws UserError if the next level is unavailable
        """
        if isValidLevel(self.level_obj.level +  1):
            self.level_obj = UserLevel(self.level_obj.level + 1)
            self.syncUser()
        else:
            raise UserError("User already at highest level")

    def demote(self):
        """
        Promotes user to the previous user level, if available
        Throws UserError if the previous level is unavailable
        """
        if isValidLevel(self.level_obj.level - 1):
            self.level_obj = UserLevel(self.level_obj.level - 1)
            self.syncUser()
        else:
            raise UserError("User already at lowest level")

    def syncUser(self):
        UserHandler().syncUser(self)

class UserHandler(object):

    def __init__(self):
        from cpc.server.state.database import DBHandler, DataBaseError
        self.dbHandler = DBHandler()

    def validateUser(self, user, password):
        """
        Returns the user if the user exist, otherwise None.
        User is passed as string
        """
        hashed_pass = hashed_pass = hashlib.sha256(password).hexdigest()
        query = "select id,user,level from users where user=? and password=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,hashed_pass,))
            res = c.fetchone()
            if res is None:
                return None
            else:
                user = User(res[0], res[1], res[2])
                return user

    def addUser(self, user, password, userlevel):
        """
        Creates a new user in the database with the given level.
        User is passed a string.
        """
        query = "select user from users where user=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,))
            if c.fetchone() is not None:
                raise UserError("User already exists: %s"%user)

        query = "insert into users (user, password, level) values(?, ?, ?)"
        hashed_pass = hashlib.sha256(password).hexdigest()
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,hashed_pass,userlevel))

    def deleteUser(self, user):
        """
        Deletes a user from the system, including its access rights
        User is passed a User object.
        """
        self._ensureType(user)
        query_users = "delete from users where id=?"
        query_users_projects = "delete from users_project where user=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query_users, (user.getUserid(),))
            c.execute(query_users_projects, (user.getUserid(),))

    def userAccessToProject(self, user, project):
        """
        Returns True if a user has permission to read/write the given project.
        A True return value does NOT guarantee that the project actually exist.
        """
        self._ensureType(user)
        #super users have all access
        if user.isSuperuser():
            return True
        query = "select user from users_project where user=? and project=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user.getUserid(), project,))
            return c.fetchone() is not None

    def getUserFromString(self, user):
        """
        Returns the user object if given user string exist, None otherwise
        """
        query = "select id,user,level from users where user=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,))
            res = c.fetchone()
            if res is None:
                return None
            else:
                user = User(res[0], res[1], res[2])
                return user

    def wipeAccessToProject(self,project):
        """
        Wipes access to everyone for a given project
        """
        query = "delete from users_project where project=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (project,))

    def getProjectListForUser(self,user):
        """
        Returns a list of projects a user has access to. Empty list if no access
        """
        self._ensureType(user)
        query = "select project from users_project where user=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user.getUserid(),))
            return [el[0] for el in c.fetchall()]

    def addUserToProject(self, user, project):
        """
        Grants access to a user to a project. OK to run multiple times
        """
        self._ensureType(user)
        query = "select user from users_project where user=? and project=?"
        insertquery = "insert into users_project values(?, ?)"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user.getUserid(), project,))
            if c.fetchone() is None:
                c.execute(insertquery, (user.getUserid(), project,))

    def syncUser(self, user):
        """
        Updates the database to match the values in the user (name, level)
        """
        self._ensureType(user)
        query = "update users set user=?, level=? where id = ?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user.getUsername(),user.getUserlevel(),
                              user.getUserid()))

    def getUsersAsList(self):
        query = "select user, level from users"
        with self.dbHandler.getCursor() as c:
            c.execute(query)
            return [{"user" : el[0], "level" : str(UserLevel(el[1]))}
                    for el in c.fetchall()]

    def _ensureType(self, user):
        if not isinstance(user, User):
            raise RuntimeError("Internal error: passed wrong type database")


class UserPool:
    """
    Tries to reuse user objects
    Benefits of this is that a getUserFromString() in the UserHandler may
    return the same object, eliminating the need for a user to relogin after
    any changes has been made to it.
    """
    __shared_state = {}
    def __init__(self):
        self.__dict__ = self.__shared_state

    #def getUser(self, user):

