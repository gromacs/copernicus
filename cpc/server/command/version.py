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




import cpc.util


class Version(object):
    """Dot-separated version number handling."""
    def __init__(self, versionStr):
        self.versionStr=versionStr
        self.versionList=[]
        for nr in versionStr.split():
            try:
                self.versionList.append(int(nr))
            except ValueError:
                cpc.util.CpcError("version string '%s' doesn't consist of numbers"%versionStr)

    def __cmp__(self, other):
        """Comparison operator function"""
        if len(self.versionList) > len(other.versionList):
            maxlen=len(self.versionList)
        else:
            maxlen=len(other.versionList)
        for i in range(maxlen):
            if i < len(self.versionList):
                sv=self.versionList[i]
            else:
                sv=0 # pad zeroes for version numbers we don't have
            if i < len(other.versionList):
                ov=other.versionList[i]
            else:
                ov=0 # pad zeroes for version numbers the other doesn't have
            if sv > ov:
                return 1
            elif ov < sv:
                return -1
        # if we're here, there was a tie so far, and they're completely equal
        return 0

    def getStr(self):
        return self.versionStr


