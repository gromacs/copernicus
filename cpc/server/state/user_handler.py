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

class UserError(cpc.util.CpcError):
    pass

class UserLevel(object):
    ANONYMOUS = 0
    REGULAR_USER = 1
    SUPERUSER = 2

class UserHandler(object):

    def __init__(self):
        from cpc.server.state.database import DBHandler, DataBaseError
        self.dbHandler = DBHandler()
    def validateUser(self, user, password):
        """
        Returns the users userlevel if the user exist, otherwise None
        """
        hashed_pass = hashed_pass = hashlib.sha256(password).hexdigest()
        query = "select level from users where user=? and password=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,hashed_pass,))
            res = c.fetchone()
            if res is None:
                return None
            else:
                return res[0]

    def createUser(self, user, password, userlevel):
        query = "select user from users where user=?"
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,))
            if c.fetchone() is not None:
                raise UserError("User already exists: %s"%user)

        query = "insert into users (user, password, level) values(?, ?, ?)"
        hashed_pass = hashlib.sha256(password).hexdigest()
        with self.dbHandler.getCursor() as c:
            c.execute(query, (user,hashed_pass,userlevel))