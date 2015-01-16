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
from cpc.server.state.user_handler import UserLevel
log=logging.getLogger(__name__)

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
    committed once the with-clause goes out of scope.
    Note that transaction only cover DML statements and will implicitly commit
    before any non-dml, such as a CREATE TABLE
    """
    def __init__(self):
        from cpc.util.conf.server_conf import ServerConf
        self.conf = ServerConf()
        self.dbpath = os.path.join(self.conf.getConfDir(),'users.db')

    def getCursor(self):
        return DBCursor(self.dbpath)

    def allocateDatabase(self):
        if os.path.isfile(self.dbpath):
            raise DataBaseError("Database already exist at %s"%self.dbpath)
        sqlite3.connect(self.dbpath)

def setupDatabase(rootpass):
    """
    Tries to setup the database, may throw
    """
    db_handler = DBHandler()
    db_handler.allocateDatabase()
    query = "insert into users (user, password, level) values(?, ?, ?)"
    hashed_pass = hashlib.sha256(rootpass).hexdigest()
    with db_handler.getCursor() as c:
        c.execute("create table users(id integer primary key autoincrement,"
        "user TEXT unique, password TEXT, level INTEGER)")
        c.execute(query, ('cpc-admin', hashed_pass, UserLevel.SUPERUSER))
        c.execute("create table users_project(user INTEGER, project TEXT)")




