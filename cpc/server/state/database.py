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


import sqlite3
import os
import logging
import hashlib
import cpc.util.exception
log=logging.getLogger('cpc.server.state.database')

class DataBaseError(cpc.util.exception.CpcError):
    pass

class DBCursor(object):
    """
    This wraps the transaction managesment provided by the connection object.
    Calling __enter__/__exit__ provides transaction with auto-rollback and
    auto-commit.
    """
    def __init__(self, dbpath):
        self.dbpath = dbpath
    def __enter__(self):
        if not os.path.isfile(self.dbpath):
            raise DataBaseError("Unable to find database at %s"%self.dbpath)
        self.conn = sqlite3.connect(self.dbpath)
        self.conn.__enter__()
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.__exit__(exc_type, exc_val, exc_tb)
        self.conn.close()

class DBHandler(object):
    """
    Provides access to the server database. Can be used from several threads.
    example usage is
        handler = DBHandler()
        with handler.getCursor() as c:
            c.execute("query")
            c.execute("query")
    This provides a transactional cursor which will rollback any changes if an
    exception is throw at any time during the 'with' clause. The changes are
    commited once the with-clause goes out of scope.
    """
    def __init__(self):
        from cpc.util.conf.server_conf import ServerConf
        self.conf = ServerConf()
        self.dbpath = os.path.join(self.conf.getConfDir(),'users.db')

    def getCursor(self):
        return DBCursor(self.dbpath)


    def validateUser(self, user, password):
        hashed_pass = hashed_pass = hashlib.sha256(password).hexdigest()
        query = "select user from users where user=? and password=?"
        with self.getCursor() as c:
            c.execute(query, (user,hashed_pass,))
            res = c.fetchone()
        return res is not None

    def createUser(self, user, password):
        query = "select user from users where user=?"
        with self.getCursor() as c:
            c.execute(query, (user,))
            if c.fetchone() is not None:
                raise DataBaseError("User already exists: %s"%user)

        query = "insert into users values(?, ?)"
        hashed_pass = hashlib.sha256(password).hexdigest()
        with self.getCursor() as c:
            c.execute(query, (user,hashed_pass,))

    def getProject(self,user):
        #should have better error handling
        query = "select default_project from users where user=?"
        with self.getCursor() as c:
            c.execute(query, (user,))
            res = c.fetchone()
            if res is None:
                return None
            else:
                return res[0]

    def allocateDatabase(self):
        if os.path.isfile(self.dbpath):
            raise DataBaseError("Database already exist at %s"%self.dbpath)
        sqlite3.connect(self.dbpath)

def setupDatabase(rootpass):
    """
    Tries to setup the database, may throw
    """
    handler = DBHandler()
    handler.allocateDatabase()
    hashed_pass = hashlib.sha256(rootpass).hexdigest()
    with handler.getCursor() as c:
        c.execute("create table users(user TEXT unique, password TEXT)")
        c.execute("insert into users VALUES('root', '%s')"%hashed_pass)


