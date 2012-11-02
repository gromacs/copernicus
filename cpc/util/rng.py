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


import random
import hashlib
import threading
import os


seeded=False # whether the command id generator has been seeded
seededLock=threading.Lock()


def getRandomHash():
    """Create a random hash for challenge-response type uses."""
    global seeded, seededLock
    with seededLock:
        if not seeded:
            random.seed(os.urandom(8))
            seeded=True
    # TODO: We should be using a cryptographically secure RNG for this
    ret=hashlib.sha1("%x%x%x%x"%
                     (random.getrandbits(32), 
                      random.getrandbits(32),
                      random.getrandbits(32), 
                      random.getrandbits(32))).hexdigest()
    return ret


