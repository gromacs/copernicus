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
import collections
import os
import os.path
import xml.sax


log=logging.getLogger('cpc.dataflow.value')


import cpc.util
import apperror
import vtype

class ValError(apperror.ApplicationError):
    pass

class ValXMLError(apperror.ApplicationXMLError):
    def __init__(self, msg, reader):
        loc=reader.getLocator()
        if loc is not None:
            self.str = "%s (line %d, column %d): %s"%(reader.getFilename(),
                                                      loc.getLineNumber(),
                                                      loc.getColumnNumber(),
                                                      msg)
        else:
            self.str=" %s: %s"%(reader.getFilename(), msg)


def interpretLiteral(literal, destType, sourceType=None, fileList=None):
    """Try to interpret a literal given a result type and a source type. 
       Returns a value object.

       literal = the literal to interpret
       destType = the type the value should become
       sourceType = an optional (base)type that this literal has
       fileList = an optional file list to choose file objects from
       """
    if sourceType is not None:
        # get the most specific type
        if destType.isSubtype(sourceType):
            tp=destType
        elif sourceType.isSubtype(destType):
            tp=sourceType
        else:
            raise ValError(
                    "Source type %s is not compatible with resulting type %s for literal '%s'."%
                    (sourceType.getName(), destType.getName(), literal))
    else:
        tp=destType
    if tp.getBaseType().simpleLiteral:
        # if it's a simple literal just make the value
        retval=Value(None, tp, fileList=fileList)
        retval._set(tp.valueFromLiteral(literal), tp)
        return retval
    raise ValError("Non-simple literals not yet implemented.")

class Value(object):
    """The class describing a data value. Value classes hold function input 
       and output data, and are used to transmit external i/o data."""
    def __init__(self, value, tp, parent=None, selfName=None, 
                 createObject=None, fileList=None, sourceTag=None):
        """Initializes an new value, with no references
    
           val = an original value
           tp = the actual type
           parent = the parent in which this value is a sub-item
           selfName = the name in the parent's collection
           createObject = the object type to create when creating subitems
        """
        self.type=tp
        self.basetype=tp.getBaseType()
        if createObject is None:
            self.createObject=Value
        else:
            self.createObject=createObject
        self.parent=parent
        self.fileValue=None
        self.fileList=fileList
        self.updated=False # whether this value has been updated
        self.copy(value)
        self.selfName=selfName
        self.seqNr=0
        self.sourceTag=sourceTag

    def _create(self, value, tp, selfName, sourceTag):
        """create a new subvalue using a value or None (in which case tp
           is used as a type)."""
        if value is not None:
            tp=value.type
        return self.createObject(value, tp, parent=self, selfName=selfName, 
                                 createObject=self.createObject,
                                 fileList=self.fileList, sourceTag=sourceTag)

    #def getFullName(self):
    #    if self.parent is not None:
    #        ret=self.parent.getFullName()
    #        return "%s.%s"%(ret, self.selfName)
    #    else:
    #        return self.selfName

    def copy(self, val):
        """Copy a value object or None"""
        # now do something for composites
        # copy this value for later
        rmref=self.fileValue
        self.fileValue=None
        #if newSeqNr is not None:
        #    self.seqNr=newSeqNr
        if not self.type.isCompound():
            if val is not None:
                self.updated=val.updated
                # now handle files.
                if val.fileValue is not None:
                    # copy the file value if we have one
                    val.fileValue.addRef()
                    self.fileValue=val.fileValue
                    self.value=val.value
                else:
                    self._set(val.value, val.basetype)
            else:
                self.value=None
        else:
            if val is None: 
                oval=None
                valtp=None
            else:
                oval=val.value
                valtp=val.type
                self.updated=val.updated
            if self.type.isSubtype(vtype.recordType):
                # create all list elements as sub-values
                self.value=dict()
                mems=self.type.getMemberKeys()
                updated=False
                for name in mems:
                    #self.type.getMembers().iteritems():
                    memtp=self.type.getMember(name)
                    if oval is None:
                        subval=None
                    else:
                        if name in oval:
                            subval = oval[name]
                        else:
                            subval = None
                    self.value[name] = self._create(subval, memtp, name, None)
            elif self.type.isSubtype(vtype.arrayType):
                # create an array. 
                self.value=[]
                if oval is not None:
                    if isinstance(oval, list):
                        index=0
                        for item in oval:
                            self.value.append(self._create(item, 
                                                           item.type, index,
                                                           item.sourceTag))
                            index+=1
                    elif oval is not None:
                        raise ValError("Trying to assign array from non-array")
            elif self.type.isSubtype(vtype.dictType):
                # create a dict
                self.value=dict()
                if oval is not None:
                    if isinstance(oval, dict):
                        for index, item in oval.iteritems():
                            self.value[index]=self._create(item, 
                                                    self.type.getMembers(),
                                                    index,
                                                    None)
            else:
                raise ValError("Unknown compound type %s."%tp.getName())
        if rmref is not None:
            rmref.rmRef()

    def destroy(self):
        """Destroy the contents of this value. Only relevant for values
           that keep File objects."""
        if self.fileValue is not None:
            self.fileValue.rmRef()
        if isinstance(self.value, dict):
            for val in self.value.itervalues():
                val.destroy()
        elif isinstance(self.value, list):
            for val in self.value:
                val.destroy()

    def _set(self, value, basetype=None):
        """Set a value: a value without subtypes."""
        self.value=value
        if ( (self.fileList is not None ) and 
             (value is not None ) and
             (basetype is not None) and
             (basetype.isSubtype(vtype.fileType) ) ):
            if os.path.isabs(value):
                self.fileValue=self.fileList.getAbsoluteFile(value)
                self.value=self.fileValue.getName()
            else:
                self.fileValue=self.fileList.getFile(value)

    def get(self):
        """Set a literal value: a value without subtypes."""
        return self.value

    def getType(self):
        return self.type

    def getBasetype(self):
        """Get the base type."""
        return self.basetype

    def hasSubValue(self, itemList):
        """Check whether a particular subvalue exists"""
        if len(itemList)==0:
            return (self.value is not None)
        if not (isinstance(self.value,dict) or isinstance(self.value,list)):
            return False
        if itemList[0] not in self.value:
            return False
        subVal=self.value[itemList[0]]
        return subVal.hasSubValue(itemList[1:])

    def getSubValue(self, itemList, create=False, createType=None, 
                    setCreateSourceTag=None, closestValue=False):
        """Get or create (if create==True) a specific subvalue through a 
           list of subitems, or return None if not found.
           
           If create==true, a subitem will be created for arrays/dicts
           if createType == a type, a subitem will be created with the given 
                            type
           if setCreateSourceTag = not None, the source tag will be set for
                                   any items that are created.
           if closestValue is true, the closest relevant value will be
                                    returned """

        #log.debug("getSubValue on on %s"%(self.getFullName()))
        if len(itemList)==0:
            return self
        # now get the first subitem
        if not (isinstance(self.value,dict) or isinstance(self.value,list)):
            #raise ValError("Trying to find sub-item in primitive value.")
            return None
        if isinstance(self.value, list):
            if self.type.isSubtype(vtype.arrayType):
                if (itemList[0] == "+") or (len(self.value) == itemList[0]):
                    if not create:
                        if closestValue:
                            return self
                        else:
                            return None
                    # choose the most specific type
                    ntp=self.type.getMembers()
                    #log.debug("ntp=%s"%ntp)
                    #log.debug("type=%s, name=%s"%(self.type, self.type.name))
                    if createType is not None and createType.isSubtype(ntp):
                        ntp=createType
                    # and make it
                    itemList[0]=len(self.value)
                    nval=self._create(None, ntp, len(self.value), 
                                      setCreateSourceTag)
                    self.value.append(nval)
                elif (itemList[0] > len(self.value)):
                    # the list is too long, but in the context of a transaction
                    # might be OK
                    if closestValue:
                        return self
                    else:
                        return None
            else:
                raise ValError("Array type not a list.")
        else:
            if itemList[0] not in self.value:
                #log.debug("%s not in %s"%(itemList[0], self.value))
                if not create:
                    if closestValue:
                        if ( (createType is not None) or 
                             (self.type.isSubtype(vtype.dictType) ) ):
                            # only return a closest value if we can actually
                            # create one if needed.
                            return self
                    return None
                else:
                    if self.type.isSubtype(vtype.dictType):
                        # choose the most specific type
                        ntp=self.type.getMembers()
                        if createType is not None:
                            if createType.isSubtype(ntp):
                                ntp=createType
                        # and make it
                        nval=self._create(None, ntp, itemList[0], 
                                          setCreateSourceTag)
                        self.value[itemList[0]] = nval
                    else:
                        # it is a list. Only create a subitem if we know what
                        # type it should be (i.e. createType is set).
                        if createType is not None:
                            nval=self._create(None, createType, itemList[0],
                                              setCreateSourceTag)
                            self.value[itemList[0]] = nval
                        else:
                            return None
        # try to find the child value
        subVal=self.value[itemList[0]]
        return subVal.getSubValue(itemList[1:], create=create, 
                                  setCreateSourceTag=setCreateSourceTag,
                                  closestValue=closestValue)

    def getSubType(self, itemList):
        """Determine the type of a sub-item (even if it doesn't exist yet)."""
        if len(itemList)==0:
            return self.type
        if not isinstance(self.value, dict) or isinstance(self.value, list):
            # we're asking for a subitem of a non-compound item.
            return None
        if itemList[0] not in self.value:
            if (self.type.isSubtype(vtype.arrayType) or 
                self.type.isSubtype(vtype.dictType)):
                stp=self.type
                # it's an array. Follow the subtypes to the end
                try:
                    for item in itemList:
                        stp=stp.getSubItem(item)
                        if stp is None:
                            return None
                except vtype.TypeErr:
                    return None
                return stp
            elif self.type.isSubtype(vtype.recordType):
                return None # we don't know what it is
        return self.value[itemList[0]].getSubType(itemList[1:])

    def getSubValueList(self):
        """Return a list of addressable subvalues."""
        if self.type.isSubtype(vtype.recordType):
            return self.type.getMemberKeys()
        elif self.type.isSubtype(vtype.arrayType):
            return self.val.keys()
        elif self.type.isSubtype(vtype.dictType):
            return self.val.keys()
        else:
            return []

    def getSubValueIterList(self):
        """Return an iterable list of addressable subvalues."""
        if self.type.isSubtype(vtype.recordType):
            return self.type.getMemberKeys()
        elif self.type.isSubtype(vtype.arrayType):
            return self.val.iterkeys()
        elif self.type.isSubtype(vtype.dictType):
            return self.val.iterkeys()
        else:
            return []

    def haveAllRequiredValues(self):
        """Return a boolean indicating whether this value and all of its
           subvalues are present (if they're not optional)."""
        if self.type.isSubtype(vtype.recordType):
            kv=self.type.getMemberKeys()
            for item in kv:
                if not self.type.getRecordMember(item).opt:
                    if (not item in self.value) or (self.value[item].value 
                                                    is None):
                        #log.debug('%s: missing record value %s'%
                        #          (self.getFullName(), item))
                        return False
                    if not self.value[item].haveAllRequiredValues():
                        #log.debug('%s: * missing record value %s'%
                        #          (self.getFullName(), item))
                        return False
                    #if self.value[item].type.isSubtype(vtype.recordType):
                    #    # check whether it's a list: then check the list
                    #elif (isinstance(self.value[item].value, list) or
                    #      isinstance(self.value[item].value, dict)):
                    #    # and if it's not optional, arrays and dicts
                    #    # must have more than 0 items.
                    #    if len(self.value[item].value) == 0:
                    #        return False
            return True
        elif (isinstance(self.value, list) or isinstance(self.value, dict)):
            # and if it's not optional, arrays and dicts
            # must have more than 0 items.
            return len(self.value) > 0
        else:
            # if it's a simple value, just check whether it's not None
            return (self.value is not None)

    def remove(self):
        """Remove the actual object."""
        self.type.remove(self)

    def getFullName(self):
        """Get the full name of the subitems of this value."""
        if self.parent is None:
            return self.selfName
        else:
            parentName=self.parent.getFullName()
            if parentName is None:
                parentName=""
            if self.parent.basetype == vtype.recordType:
                return "%s.%s"%(parentName, self.selfName)
            elif (self.parent.basetype == vtype.dictType or
                  self.parent.basetype == vtype.arrayType):
                return "%s[%s]"%(parentName, self.selfName)
            raise ValError("Unknown parent/child relationship.")

    def setUpdated(self, updated):
        """Set the updated field for this value, and all its subvalues
           to 'updated'"""
        self.updated=updated
        if isinstance(self.value, list):
            for val in self.value:
                val.setUpdated(updated)
        elif isinstance(self.value, dict):
            for val in self.value.itervalues():
                val.setUpdated(updated)

    def markUpdated(self, updated):
        """Set the updated field for this value and its parents."""
        self.updated=updated
        if self.parent is not None:
            self.parent.markUpdated(updated)

    def isUpdated(self):
        return self.updated
   
    def writeXML(self, outf, indent=0, fieldName=None):
        """Write out this value as XML"""
        indstr=cpc.util.indStr*indent
        if fieldName is not None:
            fieldstr=' field="%s"'%(fieldName)
        else:
            fieldstr=''
        if self.seqNr > 0:
            seqnrstr=' seqnr="%d"'%(self.seqNr)
        else:
            seqnrstr=''
        if self.updated:
            updatedstr=' updated="1"'
        else:
            updatedstr=''
        basetypeName=self.type.getBaseType().getName()
        if not self.type.isCompound():
            if self.value is not None:
                valuestr=' value="%s"'%(self.type.valueToLiteral(self.value))
            else:
                valuestr=''
            outf.write('%s<%s type="%s" %s%s%s%s />\n'%
                       (indstr, basetypeName,
                        self.type.getFullName(), 
                        fieldstr, seqnrstr, updatedstr, valuestr))
        else:
            outf.write('%s<%s type="%s" %s%s%s>\n'%(indstr, basetypeName,
                                                self.type.getFullName(), 
                                                fieldstr, seqnrstr,
                                                updatedstr))
            if self.type.isSubtype(vtype.arrayType):
                for val in self.value:
                    val.writeXML(outf, indent+1)
            else:
                for name, val in self.value.iteritems():
                    if val is not None:
                        val.writeXML(outf, indent+1, fieldName=name)
            outf.write('%s</%s>\n'%(indstr, basetypeName))

    def writeContentsXML(self, outf, indent=0):
        """Write out this value's subvalues as XML"""
        if not self.type.isCompound():
            raise ValError("Can't write contents of non-compound type.")
        if self.type.isSubtype(vtype.arrayType):
            for val in self.value:
                val.writeXML(outf, indent)
        else:
            for name, val in self.value.iteritems():
                if val is not None:
                    val.writeXML(outf, indent, fieldName=name)


    def itervalues(self):
        """Iterate the values of a compound type"""
        if isinstance(self.value, dict):
            return self.value.itervalues()
        elif isinstance(self.value, list):
            return self.value
        else:
            return [self.value]

    def getDesc(self):
        """Return a 'description' of a value: an item that can be passed to 
           the client describing the value."""
        if not self.type.isCompound():
            if self.value is not None:
                if self.fileValue is not None:
                    return self.fileValue.getName()
                return self.type.valueToLiteral(self.value)
            else:
                return "None"
        # it's a compound type.
        if isinstance(self.value, list):
            ret=[]
            for i in self.value:
                ret.append(i.getDesc())
        elif isinstance(self.value, dict):
            ret=dict()
            for name, i in self.value.iteritems():
                ret[name]=i.getDesc()
        else:
            log.error("Uknown compound type %s"%type(self.value))
            raise ValError("Uknown compound type.")
        return ret

class File(object):
    """Keeps track of a file."""
    def __init__(self, name, fileList):
        self.refs=1
        self.name=name
        self.fileList=fileList
    def getName(self):
        return self.name
    def getAbsoluteName(self):
        """Get the absolute name of this file."""
        return os.path.join(self.fileList.root, self.name)
    def addRef(self):
        """Add a reference to the file."""
        self.refs += 1
    def rmRef(self):
        """Remove a reference to the file. Delete when the nubmer falls 
           below 0"""
        self.refs -= 1
        if self.refs <= 0:
            log.debug("Removing %s because it is no longer in use."%self.name)
            os.remove( os.path.join(self.fileList.root, self.name ) )

class FileList(object):
    """Contains a list of all files referenced in a project."""
    def __init__(self, projectRoot):
        """Initialize a list given a project root directory."""
        self.files=dict()
        self.root=projectRoot

    def getFile(self, name):
        """Get a file object by a file name relative to the project root.
           Returns a File object."""
        if name not in self.files:
            ret=File(name, self)
            self.files[name]=ret
        else:
            ret=self.files[name]
            ret.addRef()
        return ret

    def getAbsoluteFile(self, name):
        """Get a file object by an absolute file name relative to the 
           project root.  Returns a File object."""
        relnm=os.path.relpath(name, self.root)
        return self.getFile(relnm)


           
class ValueReader(xml.sax.handler.ContentHandler):
    """XML reader for values."""
    def __init__(self, filename, startValue, importList=None, 
                 currentImport=None, implicitTopItem=True,
                 allowUnknownTypes=False, valueType=Value,
                 sourceTag=None):
        """Initialize based on
           filename = the filename to report in error messages
           importList = the ImportList object of the project. If None, 
                        knowledge about the type is not neccesarly 
           startValue = a pre-initialized value to read into.
           currentImport = the import being  currently imported.
           implicitTopItem = whether the top item of the start value is 
                             implicit.
           allowUnknownTypes = whether to allow unknown list types
           valueType = the value class to allocate if startValue is none
           sourceTag =  the source tag to set"""
        self.value=startValue
        self.valueType=valueType
        self.importList=importList
        self.currentImport=currentImport
        self.filename=filename
        self.subStack=[] # stack of subvalue we're in
        self.subCounters=[] # stack of item counters. 
        self.typeStack=[] # type stack
        self.depth=0        # depth in subitem stack
        self.lastDepth=-1   # depth in subitem stack of last item
        if implicitTopItem:
            self.subStack.append(startValue) # stack of subvalue we're in
            self.subCounters.append(0) # stack of item counters. 
            self.typeStack.append(startValue.basetype) # type stack
            self.lastDepth=0
        self.loc=None
        self.allowUnknownTypes = allowUnknownTypes
        self.sourceTag=sourceTag

    def setDocumentLocator(self, locator):
        self.loc=locator

    def getFilename(self):
        return self.filename
    def getLocator(self):
        return self.loc

    def startElement(self, name, attrs):
        #if name == "value" or name == "data":
        if name in vtype.basicTypes:
            basicType=vtype.basicTypes[name]
            if 'type' in attrs:
                tpnm=attrs.getValue('type')
                if self.importList is not None:
                    tp=self.importList.getTypeByFullName(tpnm,
                                                         self.currentImport)
                else:
                    tp=basicType
            else:
                tp=basicType
            # determine the numerical location in the subitem tree
            if self.depth == self.lastDepth:
                self.subCounters[self.depth] += 1
            elif self.depth > self.lastDepth:
                if len(self.subCounters) < self.depth+1:
                    self.subCounters.append(0)
                else:
                    self.subCounters[self.depth] = 0
            else:
                self.subCounters[self.depth] += 1
            # now determine the sub-item context
            itemStackAdd=None  # the item to add to the item stack at the end
            if len(self.subStack) > 0:
                subVal=self.subStack[-1] # subVal is the current value to read
                if 'field' in attrs:
                    if (len(self.typeStack)>0 
                        and self.typeStack[-1].isCompound()):
                        # if it's a field, it's named.
                        itemStackAdd=attrs.getValue('field')
                        createType=None
                        if self.allowUnknownTypes:
                            createType=tp
                        subVal=subVal.getSubValue([itemStackAdd], create=True,
                                            createType=createType,
                                            setCreateSourceTag=self.sourceTag)
                        if subVal is None:
                            raise ValXMLError("Did not find field '%s'"%
                                              attrs.getValue('field'), self)
                    else:
                        raise ValXMLError("field '%s' inside non-compound type"%
                                          attrs.getValue('field'), self)
                elif 'subitem' in attrs:
                    # this is a single, directly addressed sub-item
                    subitems=vtype.parseItemList(attrs.getValue('subitem'))
                    subVal=subVal.getSubValue(subitems, create=True,
                                              setCreateSourceTag=self.sourceTag)
                elif ( len(self.typeStack) > 0 and 
                       (self.typeStack[-1] == vtype.arrayType) ):
                    itemStackAdd=self.subCounters[self.depth]
                    createType=None
                    if self.allowUnknownTypes:
                        createType=tp
                    subVal=subVal.getSubValue([itemStackAdd], create=True,
                                              createType=createType,
                                              setCreateSourceTag=self.sourceTag)
            else:
                # this is the top-level value
                self.value=self.valueType(None, tp)
                subVal=self.value

            if tp is not None:
                # check the type 
                if not tp.isSubtype(subVal.getType()):
                    raise ValXMLError("%s not a subtype of %s."%
                                      (tp.getName(), 
                                       subVal.getType().getName()), 
                                      self)
            else:
                tp=subVal.getType()
            if not subVal.getType().isCompound():
                if 'value' in attrs:
                    # this means that the type is a literal and can be parsed 
                    nval=interpretLiteral(attrs.getValue('value'), tp)
                    subVal.copy(nval)
                    #subVal._set(tp.valueFromLiteral(attrs.getValue('value')))
            else:
                if 'value' in attrs:
                    raise ValXMLError("Literal value for compound type", self)
            # increment depth
            if 'seqnr' in attrs:
                subVal.seqNr=int(attrs.getValue('seqnr'))
            if 'updated' in attrs:
                updated=cpc.util.getBooleanAttribute(attrs, "updated")
                if updated:
                    subVal.markUpdated(updated)
            subVal.sourceTag=self.sourceTag
            self.lastDepth=self.depth
            self.depth+=1
            self.typeStack.append(basicType)
            #self.itemStack.append(itemStackAdd) 
            self.subStack.append(subVal)
                
    def endElement(self, name):
        #if name == "value" or name == "data":
        if name in vtype.basicTypes:
            #self.lastSubItem=self.subList.pop()
            #self.lastSubItemNr=len(self.subList)
            self.depth-=1
            self.typeStack.pop()
            self.subStack.pop()

