# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Magnus Lundborg,
# Erik Lindahl, and others.
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


import string

#import apperror

#class IdentifierError(apperror.ApplicationError):
    #def __init__(self, idString):
        #self.str="'%s' is not a valid identifier"

# keyword strings belong here.

# the self instance
Self="self"

# I/O name specifiers
In="in"
Out="out"
# subnet inputs/outputs
SubIn="sub_in"
SubOut="sub_out"
# explicitly named external inputs/outputs
ExtIn="ext_in"
ExtOut="ext_out"



# The message objects
Msg="msg"
MsgError="error"
MsgWarning="warning"
MsgLog="log"


# instance separator
InstSep=':'
ArraySepStart='['
ArraySepEnd=']'

# subtype separator
SubTypeSep='.'

# module separator
ModSep='::'


# the set of keywords that are not allowed for identifiers
keywords=set([ Self, In, Out, SubIn, SubOut, ExtIn, ExtOut ])

# the identifier allowed characters
allowedIdFirstChars = set(string.ascii_letters)
allowedIdChars = string.ascii_letters + string.digits + '_'
idTransTable = string.maketrans('-', '_')
idEmptyTransTable = string.maketrans('','')

def validIdentifier(idString):
    """Check whether a string is a valid identifier.
       Throws an IdentifierError if it is not a valid identifier,
       returns a backward-compatibility-fixed string"""
    global keywords
    global allowedIdFirstChars
    global allowedIdChars
    global idTransTable
    global idEmptyTransTable
    # the first MUST be a letter
    if not idString[0] in allowedIdFirstChars:
        raise IdentifierError(idString)
    # now fix the ID for backward compatibility
    idString=idString.translate(idTransTable)
    # and check the string for non-allowed characters, or whether it is a
    # keyword
    if ( not idString.translate(idEmptyTransTable, allowedIdChars)
         or idString in keywords):
        raise IdentifierError(idString)
    return idString

# an additional function for backward-compatibility: all IDs should have
# underscores, not dashes, and we force dashes to be underscores.
def fixID(idString):
    """an additional function for backward-compatibility: all IDs should have
       underscores, not dashes, and we force dashes to be underscores."""
    return idString.replace('-', '_')




