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


import time
class Session(object):
    """
    Session object are owned by the SessionHandler and maintains a state
    between client request. All requests are assigned a session and its lifetime
    is at least one request long.
    """
    def __init__(self, uid):
        self.uid = uid
        self.data = dict()
        self.create_timestamp = int(time.time())

    def __contains__(self, key):
        return key in self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def get(self, key, default=None):
        """
        @return session value with given key, or default or none if not such key
        exists.
        """
        return self.data.get(key, default)

    def reset(self):
        self.data = dict()

    def set(self, key, value):
        """
        Sets the given key to given value
        """
        self.data[key] = value

class SessionHandler(object):
    """
    Handles all the sessions
    """
    def __init__(self):
        self.sessions = dict()

    def getSession(self, uid, auto_create=False):
        """
        """
        try:
            #TODO: expiration
            return self.sessions[uid]
        except KeyError as e:
            if not auto_create:
                return None
            return self.createSession(uid)


    def createSession(self, uid):
        """
        Creates a session with the given uid
        @return the newly creates session
        """
        session = self.sessions[uid] = Session(uid)
        return session