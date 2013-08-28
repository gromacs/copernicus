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



import logging
import copy

try:
    from collections import OrderedDict
except ImportError:
    from cpc.util.ordered_dict import OrderedDict

log=logging.getLogger('cpc.dataflow.vtype')

import cpc.util
import keywords
import apperror
import description


class TypeErr(apperror.ApplicationError):
    pass


def parseItemList(itemStr, startDotted=True):
    """Parse a string into a list of items + subitems. Returns a list
       of subitems"""
    global itemListTransTable
    ret=[]
    inSquareBrackets=False
    inDottedItem=startDotted
    cur=""
    for c in itemStr:
        if inSquareBrackets:
            if c==']':
                if cur.strip() == '+':
                    ret.append('+')
                else:
                    ret.append(int(cur))
                cur=""
                inSquareBrackets=False
            else:
                #cur.append(c)
                cur+=c
        elif inDottedItem:
            if c==keywords.SubTypeSep or c==keywords.InstSep:
                ret.append(cur)
                cur=""
            elif c=='[':
                ret.append(cur)
                cur=""
                inSquareBrackets=True
                inDottedItem=False
            else:
                #cur.append(c)
                cur+=c
        else:
            if c==keywords.SubTypeSep or c==keywords.InstSep:
                inDottedItem=True
                cur=""
            elif c=='[':
                inSquareBrackets=True
                cur=""
            else:
                raise TypeErr("Couldn't parse '%s'."%itemStr)
    if inDottedItem:
        if cur!="":
            ret.append(cur)
    if inSquareBrackets:
        raise TypeErr("Couldn't parse '%s': unclosed square bracket."%itemStr)
    return ret

def itemListStr(items):
    """Convert an item list into a string"""
    subItemStr=""
    for item in items:
        if isinstance(item, int):
            subItemStr+="[%d]"%(item)
        else:
            subItemStr+=".%s"%(item)
    return subItemStr


class Type(description.Describable):
    """The class describing a data type."""
    __slots__=['name', 'parent', 'compound', 'lib', 'implicit',
               'builtin', 'simpleLiteral']
    def __init__(self, name, parent, lib=None):
        """Initializes an empty type

           name = the type name
           name = the type's parent in its inheritance tree 
        """
        self.name=name
        self.parent=parent
        # whether it is a compound type
        self.compound=False
        self.lib=lib
        self.implicit=False
        self.builtin=False
        # whether the type has a single simple literal (like a number):
        self.simpleLiteral=False 
        description.Describable.__init__(self)

    def getName(self):
        return self.name
    def isAnonymous(self):
        return (self.name is None)
    def isBuiltin(self):
        """Returns whether the type is built-in"""
        return self.builtin
    def getParent(self):
        return self.parent

    def hasMembers(self):
        """Returns whether the type has member variables"""
        return False
    def getMembers(self):
        return None

    def isCompound(self):
        """Whether the type consists of several items."""
        return self.compound

    def valueFromLiteral(self, string):
        """Convert a value from a string."""
        return None
    def valueToLiteral(self, value):
        """Convert a value to a string."""
        return None
    def isSubtype(self, type):
        """Check whether this type is an instance (i.e. inherited from) of the
           given type. Any type is a subtype of itself."""
        cur=self
        while cur is not None:
            if cur == type:
                return True
            cur=cur.parent
        return False
    def remove(self, value):
        """Perform a clean-up of a value"""
        pass
    def getLib(self):
        """Get the library this type is in."""
        return self.lib
    def setLib(self, lib):
        """Set the library this type is in."""
        self.lib=lib
    def getFullName(self):
        if self.lib is not None and self.lib.getName() != "":
            return "%s%s%s"%(self.lib.getName(), keywords.ModSep, self.name)
        else:
            return self.name
    def inherit(self, newName, lib):
        ret=type(self)(newName, self, lib)
        ret.builtin=False
        ret.implicit=False
        return ret

    def writeXML(self, outf, indent=0):
        """Describe the type."""
        indstr=cpc.util.indStr*indent
        name=self.getFullName()
        outf.write('%s<type id="%s" base="%s">\n'%(indstr, name,
                                                   self.getParent().name))
        if self.desc is not None:
            self.desc.writeXML(outf, indent+1)
        self.writePartsXML(outf, indent+1)
        outf.write('%s</type>\n'%(indstr))

    def writePartsXML(self, outf, indent=0):
        """Write the xml of the constituent parts of the type for compound
            types."""
        pass
    def getSubItem(self, item):
        """Get a specific sub-item."""
        raise TypeErr("No subitem to get")

    def getBaseType(self):
        """Get the base type of this type."""
        ret=self
        while ret not in basicTypeList:
            ret=ret.parent
        return ret

    def getBaseTypeName(self):
        """Get the base type of this type."""
        ret=self
        while ret not in basicTypeList:
            ret=ret.parent
        return ret.name

    def jsonDescribe(self):
        """Get a description of a type in a JSON-serializable format."""
        return { "name" : self.name,
                 "base-type" : self.getBaseTypeName() }

    def containsBasetype(self, basetype):
        """Check whether the type or one of its members contains a subtype
           of basetype."""
        return self.isSubtype(basetype)


    def isImplicit(self):
        """Whether the type is implicit (i.e. does not need to be written
           out with the state)"""
        return self.implicit
    def markImplicit(self):
        """Mark the type as implicit."""
        self.implicit=True

class BoolType(Type):
    """The class describing a boolean type."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.simpleLiteral=True 
    def valueFromLiteral(self, string):
        if string.lower()=="true" or string=="1":
            return True
        elif string.lower()=="false" or string=="0":
            return False
        else:
            raise TypeErr('%s is neither true nor false'%string)
    def valueToLiteral(self, value):
        if value:
            return 'true'
        else:
            return 'false'

class IntType(Type):
    """The class describing an int type."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.simpleLiteral=True 
    def valueFromLiteral(self, string):
        try:
            return int(string)
        except ValueError:
            raise TypeErr('%s is not an integer'%string)
    def valueToLiteral(self, value):
        return "%d"%value

class FloatType(Type):
    """The class describing a float type."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.simpleLiteral=True 
    def valueFromLiteral(self, string):
        try:
            return float(string)
        except ValueError:
            raise TypeErr('%s is not a float number'%string)
    def valueToLiteral(self, value):
        return "%g"%value


class StringType(Type):
    """The class describing a string type."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.simpleLiteral=True 
    def valueFromLiteral(self, string):
        return string
    def valueToLiteral(self, value):
        return value

class FileType(Type):
    """The class describing a file."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.ext=None
        self.mimeType=None
        self.simpleLiteral=True 
    def valueFromLiteral(self, string):
        return string
    def valueToLiteral(self, value):
        return value
    def remove(self, value):
        log.debug("Removing file %s"%(value.val))
        os.remove(value.val)
    def setExtension(self, ext):
        self.ext=ext
    def getExtension(self):
        return self.ext
    def setMimeType(self, mimeType):
        self.mimeType=mimeType
    def getMimeType(self):
        return self.mimeType


class RecordMember(description.Describable):
    """Class containing information about a record member."""
    def __init__(self, tp, name, opt=False, const=False, complete=False):
        """Initialize based on type, name, description.
           tp = the type
           name = the name
           opt = whether this member is optional
           const = whether this member is const
           complete = whether this member's sub-items must not be None """
        self.type=tp
        self.name=name
        self.opt=opt
        self.const=const
        self.complete=complete
        description.Describable.__init__(self)

    def isOptional(self):
        """Return whether the field is optional."""
        return self.opt

    def isConst(self):
        """Return whether the field is constant."""
        return self.const

    def isComplete(self):
        """Return whether all sub-items of this item must be non-None"""
        return self.complete

    def jsonDescribe(self):
        """Return a json-serializable description of the record member."""
        return self.type.jsonDescribe()


class RecordType(Type):
    """Base class describing a named list with fixed membership."""
    def __init__(self, name, parent, lib=None):
        Type.__init__(self, name, parent, lib=lib)
        self.compound=True
        self.recordMembers=OrderedDict()  #ordered dict of RecordMembers
    def hasMembers(self):
        """Returns whether the type has member variables"""
        if self.parent.isSubtype(recordType) and self.parent.hasMembers():
            return True
        return len(self.recordMembers) > 0
    def iterMembers(self):
        """Generate an iterable list of tuples: (key, member)"""
        if self.parent.isSubtype(recordType) and self.parent.hasMembers():
            for (key, item) in self.parent.iterMembers():
                yield (key, item)
        for (key, item) in self.recordMembers.iteritems():
            yield (key, item)
    def iterMemberKeys(self):
        """Generate an iterable list of the names of members"""
        if self.parent.isSubtype(recordType) and self.parent.hasMembers():
            for key in self.parent.iterMemberKeys():
                yield key
        for key in self.recordMembers.iterkeys():
            yield key
    def getMemberKeys(self):
        """Get a list with the member keys of the record."""
        if self.parent.isSubtype(recordType) and self.parent.hasMembers():
            ret=self.parent.getMemberKeys()
        else:
            ret=[]
        ret.extend(self.recordMembers.keys())
        return ret
    def getMember(self, name):
        """Get a specific member type."""
        if name in self.recordMembers:
            return self.recordMembers[name].type
        return self.parent.getMember(name)
    def getRecordMember(self, name):
        """Get a specific RecordMember object"""
        if name in self.recordMembers:
            return self.recordMembers[name]
        return self.parent.recordMembers[name]
    def copyMembers(self, recordType):
        """Set the members of the record according to a another record type."""
        for name, mem in recordType.recordMembers.iteritems():
            self.recordMembers[name] = copy.copy(mem)
    def hasMember(self, name):
        """Return whether the member with name 'name' exists."""
        if name in self.recordMembers:
            return True
        if self.parent.isSubtype(recordType):
            return self.parent.hasMember(name) 
    def addMember(self, name, vtype, opt, const, complete):
        """Add/override a new member to the record.
           name = the name of the new member item
           vtype = the type of the new member item
           opt = whether the member is optional
           const = hwehter the member is const
           complete = whether the member's subvalues must be non-None"""
        if name in self.recordMembers:
            self.recordMembers[name].type=vtype
            self.recordMembers[name].opt=opt
            self.recordMembers[name].const=const
            self.recordMembers[name].complete=complete
        else:
            self.recordMembers[name]=RecordMember(vtype, name, opt, const, 
                                                  complete)
    def addDescription(self, name, desc):
        """Add a description of a member to the record"""
        self.descs[name]=desc
    def getMemberDesc(self, name):
        """Get a specific member description."""
        return self.recordMembers[name].desc
    def setMemberDesc(self, name, desc):
        """Get a specific member description."""
        self.recordMembers[name].desc=desc

    def jsonDescribe(self):
        """Get a description of a type in a JSON-serializable format."""
        ret = { "name" : self.name,
                "base-type" : self.getBaseTypeName() }
        mems={}
        for (key, item) in self.iterMembers():
            mems[key] = item.jsonDescribe()
        ret["members"]=mems
        return ret

    def writePartsXML(self, outf, indent=0):
        """Write the xml of the constituent parts of the type for compound
            types."""
        indstr=cpc.util.indStr*indent
        for name, mem in self.recordMembers.iteritems():
            tp=mem.type
            if tp.lib is None:
                tpname=tp.name
            else:
                #tpname="%s::%s"%(tp.lib.getName(), tp.name)
                tpname=tp.getFullName()
            attrstr=' '
            if mem.opt:
                attrstr=' opt="true"'
            if mem.const:
                attrstr=' const="true"%s'%attrstr
            if mem.complete:
                attrstr=' complete="true"%s'%attrstr
            if tp.hasMembers() and tp.isAnonymous():
                outf.write('%s<field id="%s"%s type="%s">\n'%
                           (indstr, name, attrstr, tpname))
                tp.writePartsXML(outf, indent+1)
                if mem.desc is not None:
                    mem.desc.writeXML(outf, indent+1)
                outf.write('%s</field>\n'%indstr)
            else:
                if mem.desc is None:
                    outf.write('%s<field id="%s"%s type="%s" />\n'%
                               (indstr, name, attrstr, tpname))
                else:
                    outf.write('%s<field id="%s"%s type="%s">\n'%
                               (indstr, name, attrstr, tpname))
                    mem.desc.writeXML(outf, indent+1)
                    outf.write('%s</field>\n'%indstr)

    def getSubItem(self, item):
        """Get a specific sub-item."""
        return self.members[item]

    def containsBasetype(self, basetype):
        """Check whether the type or one of its members contains an instance
           of basetype."""
        for subtype in self.recordMembers.itervalues():
            if subtype.type.containsBasetype(basetype):
                return True
        return False



class ArrayType(Type):
    """Base class describing an array."""
    def __init__(self, name, parent, lib=None, memberType=None):
        Type.__init__(self, name, parent, lib=lib)
        self.compound=True
        self.memberType=memberType
    def hasMembers(self):
        """Returns whether the type has member variables"""
        return not (self.memberType is None)
    def getMembers(self):
        """Get the type of the array's members"""
        return self.memberType
    def setMembers(self, type):
        """Set the type of the array's members"""
        self.memberType=type
    def jsonDescribe(self):
        """Get a description of a type in a JSON-serializable format."""
        ret = { "name" : self.name,
                "base-type" : self.getBaseTypeName() }
        ret["members"]=self.memberType.jsonDescribe()
        return ret
    def writePartsXML(self, outf, indent=0):
        """Write the xml of the constituent parts of the type for compound
            types."""
        indstr=cpc.util.indStr*indent
        if self.memberType.hasMembers() and self.memberType.isAnonymous():
            outf.write('%s<field type="%s">\n'%(indstr, 
                                                self.memberType.getFullName()))
            self.memberType.writePartsXML(outf, indent+1)
            if self.memberType.desc is not None:
                self.memberType.desc.writeXML(outf, indent+1)
            outf.write('%s</field>\n'%indstr)
        else:
            if self.memberType.desc is None:
                outf.write('%s<field type="%s" />\n'%(indstr, 
                                                 self.memberType.getFullName()))
            else:
                outf.write('%s<field type="%s">\n'%(indstr, 
                                                 self.memberType.getFullName()))
                self.memberType.desc.writeXML(outf, indent+1)
                outf.write('%s</field>\n'%indstr)

    def getSubItem(self, item):
        """Get a specific sub-item from a list of subitems."""
        if not isinstance(item, int):
            raise TypeErr("Subitem to of wrong type for array")
        return self.memberType

    def containsBasetype(self, basetype):
        """Check whether the type or one of its members contains an instance
           of basetype."""
        return self.memberType.containsBasetype(basetype) 


class DictType(Type):
    """Base class describing a dict object: an associative array."""
    def __init__(self, name, parent, lib=None, memberType=None):
        Type.__init__(self, name, parent, lib=lib)
        self.compound=True
        self.memberType=memberType

    def hasMembers(self):
        """Returns whether the type has member variables"""
        return not (self.memberType is None)
    def getMembers(self):
        """Get the type of the dict's members"""
        return self.memberType
    def setMembers(self, type):
        """Set the type of the dict's members"""
        self.memberType=type
    def jsonDescribe(self):
        """Get a description of a type in a JSON-serializable format."""
        ret = { "name" : self.name,
                "base-type" : self.getBaseTypeName() }
        ret["members"]=self.memberType.jsonDescribe()
        return ret
    def writePartsXML(self, outf, indent=0):
        """Write the xml of the constituent parts of the type for compound
            types."""
        indstr=cpc.util.indStr*indent
        if self.memberType.hasMembers() and self.memberType.isAnonymous():
            outf.write('%s<field type="%s">\n'%(indstr, 
                                                self.memberType.getFullName()))
            if self.memberType.desc is not None:
                self.memberType.desc.writeXML(outf, indent+1)
            self.memberType.writePartsXML(outf, indent+1)
            outf.write('%s</field>\n'%indstr)
        else:
            if self.memberType.desc is None:
                outf.write('%s<field type="%s" />\n'%(indstr, 
                                                 self.memberType.getFullName()))
            else:
                outf.write('%s<field type="%s">\n'%(indstr, 
                                                 self.memberType.getFullName()))
                self.memberType.desc.writeXML(outf, indent+1)
                outf.write('%s</field>\n'%indstr)
            #outf.write('%s<field type="%s" />\n'%(indstr, 
            #                                   self.memberType.getFullName()))

    def getSubItem(self, item):
        """Get a specific sub-item from a list of subitems."""
        if not isinstance(item, int):
            raise TypeErr("Subitem to of wrong type for dict")
        return self.memberType

    def containsBasetype(self, basetype):
        """Check whether the type or one of its members contains an instance
           of basetype."""
        return self.memberType.containsBasetype(basetype) 


# these are global variables, so things can be checked against them
valueType   = Type('value', None)
nullType    = Type("null", valueType)
boolType    = BoolType("bool", valueType)
intType     = IntType("int", valueType)
floatType    = FloatType("float", valueType)
stringType  = StringType("string", valueType)
fileType    = FileType("file", valueType)
# compound types
recordType    = RecordType("record", valueType)
arrayType   = ArrayType("array", valueType, memberType=valueType)
dictType    = DictType("dict", valueType, memberType=valueType)
# other types
instanceType    = Type("instance", valueType)
msgType    = Type("msg", valueType)

valueType.builtin=True
nullType.builtin=True
boolType.builtin=True
intType.builtin=True
floatType.builtin=True
stringType.builtin=True
recordType.builtin=True
arrayType.builtin=True
dictType.builtin=True

instanceType.builtin=True
msgType.builtin=True

# the primitives
primitives = [ valueType, boolType, intType, floatType, stringType, fileType ]

basicTypes = { valueType.getName() : valueType,
               nullType.getName() : nullType,
               boolType.getName() : boolType,
               intType.getName() : intType,
               floatType.getName() : floatType,
               stringType.getName() : stringType,
               fileType.getName() : fileType,
               recordType.getName() : recordType,
               arrayType.getName() : arrayType,
               dictType.getName() : dictType }

basicTypeList = [valueType,  nullType,  boolType, intType,  floatType,
                 stringType, fileType, recordType, arrayType, dictType ]


