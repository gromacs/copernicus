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


import os
import xml.sax
import xml.sax.saxutils
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import logging

import operator


log=logging.getLogger('cpc.dataflow.readxml')

import cpc.util
import apperror
import keywords
import description
import function
import atomic
import network
import network_function
import function_io
import instance
import connection
import external
import value
import active_value
import vtype
import active
import active_inst
import task
import run
import cpc.server.command

class ProjectError(apperror.ApplicationError):
    pass

class ProjectXMLError(apperror.ApplicationXMLError):
    def __init__(self, msg, reader):
        loc=reader.getLocator()
        self.str = "%s (line %d, column %d): %s"%(reader.getFilename(),
                                                  loc.getLineNumber(), 
                                                  loc.getColumnNumber(), 
                                                  msg)

curVersion=1

class ProjectXMLReader(xml.sax.handler.ContentHandler):
    """XML reader for a project and function definitions."""
    def __init__(self, thisImport, importList, project):
        """Initialize based on import library.
           
           thisImport = the library to read into
           importList = the list of currenlty imported libraries.
           project = the projecct associated with this read """
        self.thisImport=thisImport
        self.importList=importList
        self.project=project
        # the reading context (which function we're defining at the moment).
        self.function=None
        self.functionType=None
        # subcontext is where we're at within in a function definition 
        self.network=None # the top of the networkStack
        self.networkStack=[] # the stack of previous networks
        # list of local imports with their name mappings
        self.localImports=dict()
        self.inController=False
        # in type definition
        #self.inType=None
        self.type=None
        self.typeStack=[] # the stack of tuples of types and their field names 
        self.ioitem=None # the I/O item type we're in
        # in instance
        self.instance=None
        # stack of active instances (an active instance can be in the network
        # of an active instance):
        self.activeInst=None
        self.activeInstStack=[]
        self.curTask=None
        self.fnInputReader=None # task's function inputs
        self.fninputReaderEndTag=None
        self.cmdReader=None
        self.valueReader=None
        self.valueReaderEndTag=None # end tag to look for when valueReader!=None
        self.curValue=None
        self.taskList=[]
        self.fileVersion=None
        self.descReader=None # the description reader
        self.descReaderEndTag=None
        self.descContext=None # a describable context
        self.fileList=project.getFileList()


    def getTaskList(self):
        return self.taskList

    def setDocumentLocator(self, locator):
        #log.debug("Setting main locator")
        if self.fnInputReader is not None:
            self.fnInputReader.setDocumentLocator(locator)
        if self.cmdReader is not None:
            self.cmdReader.setDocumentLocator(locator)
        if self.valueReader is not None:
            self.valueReader.setDocumentLocator(locator)
        self.loc=locator

    def read(self, filename):
        """Read a file with import library definitions."""
        try:
            self.filename=filename
            self.dirName=os.path.split(filename)[0]
            parser=xml.sax.make_parser()
            parser.setContentHandler(self)
            inf=open(filename, 'r')
            parser.parse(inf)
            inf.close()
        except ProjectXMLError as e:
            raise e
        except apperror.ApplicationError as e:
            raise ProjectXMLError(str(e), self)

    def readFile(self, file, reportFilename):
        """Read a file object with import library definitions."""
        try:
            self.filename=reportFilename
            self.dirName=None
            parser=xml.sax.make_parser()
            parser.setContentHandler(self)
            parser.parse(file)
        except ProjectXMLError as e:
            raise e
        except apperror.ApplicationError as e:
            raise ProjectXMLError(str(e), self)

    def getFilename(self):
        return self.filename
    def getLocator(self):
        return self.loc


    def setCmdReader(self, cmdReader):
        self.cmdReader=cmdReader
        if cmdReader is not None:
            cmdReader.setDocumentLocator(self.loc)
    def setFnInputReader(self, fnInputReader, endTag):
        self.fnInputReader=fnInputReader
        self.fnInputReaderEndTag=endTag
        if fnInputReader is not None:
            fnInputReader.setDocumentLocator(self.loc)
    def setValueReader(self, valueReader, endTag):
        self.valueReader=valueReader
        self.valueReaderEndTag=endTag
        if valueReader is not None:
            valueReader.setDocumentLocator(self.loc)
    def setDescReader(self, descReader, endTag):
        self.descReader=descReader
        self.descReaderEndTag=endTag
        if descReader is not None:
            descReader.setDocumentLocator(self.loc)

    def startElement(self, name, attrs):
        # first handle all the sub-readers
        if self.cmdReader is not None:
            self.cmdReader.startElement(name, attrs)
        elif self.fnInputReader is not None:
            self.fnInputReader.startElement(name, attrs)
        elif self.valueReader is not None:
            self.valueReader.startElement(name, attrs)
        elif self.descReader is not None:
            self.descReader.startElement(name, attrs)
        # and then actual elements
        elif name == "cpc":
            # top-level element
            if attrs.has_key('version'):
                self.fileVersion=int(attrs.getValue("version"))
            else:
                self.fileVersion=0
            if self.fileVersion > curVersion:
                raise ProjectXMLError("Can't read file from the future.")
        elif name == "import":
            if not attrs.has_key('name'):
                raise ProjectXMLError("import has no name", self)
            name=attrs.getValue('name')
            nimport=self.importList.get(name)
            if nimport is None:
                # we don't have it yet. Read it.
                nimport=self.project.importName(name)
                # and try again
                nimport=self.importList.get(name)
                if nimport is None:
                    raise ProjectXMLError("Failed to import %s"%name,
                                          self)
            self.localImports[name] = nimport    
        elif name == "function":
            if self.function is not None:
                raise ProjectXMLError(
                        "function-in-function definitions not supported", 
                        self)
            if not attrs.has_key("type"):
                raise ProjectXMLError("function has no type", 
                                            self)
            if not attrs.has_key("id"):
                raise ProjectXMLError("function has no id", self)
            fntype=attrs.getValue("type") 
            id=attrs.getValue("id")
            #if type == "command":
            #    tsk=atomic.CommandFunction(id, [], [], None, None, None)
            if fntype == "python":
                tsk=atomic.SimpleFunctionFunction(id, lib=self.thisImport)
            elif fntype == "python-extended":
                tsk=atomic.ExtendedFunctionFunction(id, lib=self.thisImport)
            elif fntype == "network":
                tsk=network_function.NetworkFunction(id, lib=self.thisImport)
            elif fntype == "external":
                if self.dirName is None:
                    raise ProjectXMLError(
                                    "external function without directory",
                                    self)
                tsk=external.ExternalFunction(id, basedir=self.dirName, 
                                              lib=self.thisImport)
            else:
                raise ProjectXMLError("function type '%s' not recognized"%
                                      (fntype), self)
            self.function=tsk
            self.functionType=fntype
        elif name=="type":
            if self.function is not None:
                raise ProjectXMLError(
                        "type-in-function definitions not supported", self)
            if self.type is not None:
                 raise ProjectXMLError(
                        "type-in-type definitions not supported", self)
            if not attrs.has_key("id"):
                raise ProjectXMLError("type has no id", self)
            if not attrs.has_key("base"):
                raise ProjectXMLError("type has no base", self)
            name=attrs.getValue("id")
            basetype=self.importList.getTypeByFullName(attrs.getValue("base"), 
                                                     self.thisImport)
            #basetype=self.project.getType(attrs.getValue("base"))
            self.type=basetype.inherit(name, self.thisImport)
            self.typeStack.append( (self.type, None) )
            if basetype.isSubtype(vtype.arrayType):
                if attrs.has_key("member-type"):
                    tnm=attrs.getValue("member-type")
                    members=self.importList.getTypeByFullName(tnm, 
                                                              self.thisImport)
                    #members=self.project.getType(attrs.getValue("members"))
                    self.type.setMembers(members)
                    log.debug("new array(%s) type %s"%(members.name, name))
            elif basetype.isSubtype(vtype.fileType):
                if attrs.has_key("extension"):
                    self.type.setExtension(attrs.getValue("extension"))
                if attrs.has_key("mime-type"):
                    self.type.setExtension(attrs.getValue("mime-type"))
        elif name == "inputs":
            if self.type is not None:
                raise ProjectXMLError("nested inputs", self)
            self.ioitem="inputs"
            if self.instance is not None:
                self.type=self.instance.getInputs()
                self.typeStack.append( (self.type, None) )
            elif self.function is not None:
                self.type=self.function.getInputs()
                self.typeStack.append( (self.type, None) )
            elif self.activeInst is not None:
                curValue=self.activeInst.getInputs()
                self.setValueReader(value.ValueReader(self.filename, curValue, 
                                                 importList=self.importList,
                                                 currentImport=self.thisImport),
                                    name)
            else:
                raise ProjectXMLError("inputs without function/instance", self)
        elif name == "outputs":
            if self.type is not None:
                raise ProjectXMLError("nested outputs", self)
            self.ioitem="outputs"
            if self.instance is not None:
                self.type=self.instance.getOutputs()
                self.typeStack.append( (self.type, None) )
            elif self.function is not None:
                self.type=self.function.getOutputs()
                self.typeStack.append( (self.type, None) )
            elif self.activeInst is not None:
                curValue=self.activeInst.getOutputs()
                self.setValueReader(value.ValueReader(self.filename, curValue, 
                                                 importList=self.importList,
                                                 currentImport=self.thisImport),
                                    name)
            else:
                raise ProjectXMLError("outputs without function/instance", self)
        elif name == "subnet-inputs":
            if self.type is not None:
                raise ProjectXMLError("nested subnet-inputs", self)
            self.ioitem="subnet-inputs"
            if self.instance is not None:
                self.type=self.instance.getSubnetInputs()
                self.typeStack.append( (self.type, None) )
            elif self.function is not None:
                self.type=self.function.getSubnetInputs()
                self.typeStack.append( (self.type, None) )
            elif self.activeInst is not None:
                curValue=self.activeInst.getSubnetInputs()
                self.setValueReader(value.ValueReader(self.filename, curValue, 
                                                 importList=self.importList,
                                                 currentImport=self.thisImport),
                                    name)
            else:
                raise ProjectXMLError(
                                "subnet-inputs without function/instance", self)
        elif name == "subnet-outputs":
            if self.type is not None:
                raise ProjectXMLError("nested subnet-outputs", self)
            self.ioitem="subnet-outputs"
            if self.instance is not None:
                self.type=self.instance.getSubnetOutputs()
                self.typeStack.append((self.type, None))
            elif self.function is not None:
                self.type=self.function.getSubnetOutputs()
                self.typeStack.append((self.type, None))
            elif self.activeInst is not None:
                curValue=self.activeInst.getSubnetOutputs()
                self.setValueReader(value.ValueReader(self.filename, curValue, 
                                                 importList=self.importList,
                                                 currentImport=self.thisImport),
                                    name)
            else:
                raise ProjectXMLError(
                            "subnet-outputs without function/instance", self)
        elif name == "field":
            if self.type is None and self.ioitem is None:
                raise ProjectXMLError("Field without type context", self)
            if not attrs.has_key("type"):
                raise ProjectXMLError("No type in field", self)
            tpnm=attrs.getValue("type")
            if self.type is not None and self.type.isCompound():
                tp=self.importList.getTypeByFullName(tpnm, self.thisImport)
                nm=None
                #basetype=self.importList.getTypeByFullName(tpnm,
                #                                           self.thisImport)
                if self.type.isSubtype(vtype.arrayType):
                    self.type.setMembers(tp)
                elif self.type.isSubtype(vtype.dictType):
                    self.type.setMembers(tp)
                elif self.type.isSubtype(vtype.listType):
                    if not attrs.has_key("id"):
                        raise ProjectXMLError("No id in list field", self)
                    const=cpc.util.getBooleanAttribute(attrs,"const")
                    opt=cpc.util.getBooleanAttribute(attrs,"opt")
                    nm=attrs.getValue("id")
                    self.type.addMember(nm, tp, opt, const)
                # add it to the stack
                self.type=tp
                self.typeStack.append((tp, nm))
            else:
                raise ProjectXMLError("Non-compound type %s can't have fields"%
                                      self.type.getName(), self)
        elif name == "network":
            #if len(self.networkStack) < 1:
            #    raise ProjectXMLError("network in network definition", self)
            if self.function is None:
                # there is no function, check whether we're in an active
                # network:
                if len(self.activeInstStack) < 1:
                    # we're not. Get the top level
                    if len(self.networkStack)>0:
                        raise ProjectXMLError("network in network definition", 
                                              self)
                    self.networkStack.append(self.thisImport.getNetwork())
                else:
                    self.networkStack.append(self.activeInst.getNet())
            else:
                # this is a function network
                if len(self.networkStack)>0:
                    raise ProjectXMLError("network in network definition", self)
                self.networkStack.append(self.function.getSubnet())
            self.network=self.networkStack[-1]
        elif name == "instance":
            if self.network is None:
                raise ProjectXMLError("instance without network", self)
            if not attrs.has_key("id"):
                raise ProjectXMLError("instance has no id", self)
            if not attrs.has_key("function"):
                raise ProjectXMLError("instance has no function", self)
            id=attrs.getValue('id')
            fn=attrs.getValue('function')
            func=self.importList.getFunctionByFullName(fn, self.thisImport)
            self.instance=instance.Instance(id, func, fn, self.thisImport)
        elif name == "assign":
            if not 'value' in attrs:
                raise ProjectXMLError("assign has no value", self)
            if not attrs.has_key('type'):
                raise ProjectXMLError("assign has no type", self)
            if not attrs.has_key('dest'):
                raise ProjectXMLError("assign has no destination", self)
            valueString=attrs.getValue('value')
            typestr=attrs.getValue('type')
            dst=attrs.getValue('dest')
            # get the type object
            #tp=self.project.getType(typestr)
            tp=self.importList.getTypeByFullName(typestr, self.thisImport)
            # get the value from the type object
            val=active_value.ActiveValue(value.interpretLiteral(valueString,tp),
                                         tp)
            log.debug("value is %s"%str(val))
            # get the destination
            dstInstName,dstDir,dstItemName=(connection.splitIOName(dst, 
                                                                   keywords.In))
            cn=connection.makeInitialValue(self.network, 
                                           dstInstName, dstDir, 
                                           dstItemName, val)
            self.network.addConnection(cn)
        elif name == "connection":
            if self.network is None:
                raise ProjectXMLError("connection without network", self)
            if not attrs.has_key('src') and not attrs.has_key('value'):
                raise ProjectXMLError("connection has no source", self)
            if not attrs.has_key('dest'):
                raise ProjectXMLError("connection has no destination", self)

            dst=attrs.getValue('dest')
            dstInstName,dstDir,dstItemName=(connection.splitIOName(dst, None))
            if attrs.has_key('src'):
                src=attrs.getValue('src')
                # now check the source
                srcInstName,srcDir,srcItemName=(connection.splitIOName(src,
                                                                       None))
                cn=connection.makeConnection(self.network, 
                                             srcInstName, srcDir, srcItemName, 
                                             dstInstName, dstDir, dstItemName)

            else:
                if not attrs.has_key("type"):
                    raise ProjectXMLError("connection has no type", self)
                typestr=attrs.getValue('type')
                valueString=attrs.getValue('value')
                tp=self.importList.getTypeByFullName(typestr, self.thisImport)
                #tp=self.project.getType(typestr)
                # get the value from the type object
                val=value.interpetLiteral(valueString, tp)
                cn=connection.makeInitialValue(self.network,
                                               dstInstName, dstDir, dstItemName,
                                               val)
            self.network.addConnection(cn)
        elif name=="controller":
            # generic items
            if cpc.util.getBooleanAttribute(attrs,"persistent_dir"):
                # a persistent scratch dir is needed
                log.debug("Setting persistent dir for %s"%
                          self.function.getName())
                self.function.setPersistentDir(True)
            if cpc.util.getBooleanAttribute(attrs,"output_dir"):
                log.debug("Setting output dir always on for %s"%
                          self.function.getName())
                # a run dir is needed even if there's no file output
                self.function.setOutputDirWithoutFiles(True)
            if cpc.util.getBooleanAttribute(attrs, "log"):
                log.debug("Turning on logging for %s"%(self.function.getName()))
                self.function.setLog(True)
            if cpc.util.getBooleanAttribute(attrs, "access_outputs"):
                log.debug("Controller uses current outputs for %s"%
                          (self.function.getName()))
                self.function.setAccessOutputs(True)
            if cpc.util.getBooleanAttribute(attrs, "access_subnet_outputs"):
                log.debug("Controller uses current subnet outputs for %s"%
                          (self.function.getName()))
                self.function.setAccessSubnetOutputs(True)
            # type-specific items
            if (self.functionType == "python" or 
                self.functionType == "python-extended"):
                importName=None
                if attrs.has_key("import"):
                    importName=attrs.getValue('import')
                if not attrs.has_key('function'):
                    raise ProjectXMLError("python controller has no function",
                                          self)
                fnName=attrs.getValue("function")
                self.function.setFunction(fnName, importName)
            elif self.functionType == "command":
                pass
            elif self.functionType == "external":
                if not attrs.has_key('executable'):
                    raise ProjectXMLError(
                                         "command controller has no executable",
                                         self)
                executable=attrs.getValue("executable")
                self.function.setExecutable(executable)
                self.inController=True
        elif name=="stdin":
            if self.inController and self.functionType == "command":
                if not atts.has_key('value'):
                    raise ProjectXMLError("stdin has no value", self)
                self.function.setStdin(attrs.getValue('value'))
            else:
                raise ProjectXMLError("stdin tag, without command controller", 
                                      self)
        elif name=="arg":
            if self.inController and self.functionType == "command":
                pass
            else:
                raise ProjectXMLError("arg tag, without command controller", 
                                      self)
        elif name == "active":
            # read in a description of an active network + active instances
            if not isinstance(self.network, active.ActiveNetwork): 
                raise ProjectXMLError("active instance without active network",
                                      self)
            if not attrs.has_key("id"):
                raise ProjectXMLError("active instance has no id", self)
            if not attrs.has_key("state"):
                raise ProjectXMLError("active instance has no state", self)
            if not attrs.has_key("seqnr"):
                raise ProjectXMLError("active instance has no seqnr", self)
            name=attrs.getValue("id")
            stStr=attrs.getValue("state")
            # now get the actual state
            state=None
            for st in active_inst.ActiveInstance.states:
                if st.str == stStr:
                    state=st
            if state is None:
                raise ProjectXMLError("active instance state %s invalid"%stStr,
                                      self)
            seqnr=int(attrs.getValue("seqnr"))
            ai=self.network.getActiveInstance(name)
            ai.setState(state)
            ai.setSeqNr(seqnr)
            if attrs.has_key('errmsg'):
                ai.setErrmsg(xml.sax.saxutils.unescape(attrs.
                                                       getValue('errmsg')))
            self.activeInstStack.append(ai)
            self.activeInst=ai
        elif name == "active-connection":
            # any value associated with active connection points
            if self.activeInst is None:
                raise ProjectXMLError(
                                "active connection without active instance", 
                                self)
            if not attrs.has_key("id"):
                raise ProjectXMLError("active conn field has no id", self)
            #if not attrs.has_key("seqnr"):
            #    raise ProjectXMLError("active conn field has no seqnr", self)
            if not attrs.has_key("type"):
                raise ProjectXMLError("active conn field has no type", self)
            tpnm=attrs.getValue("type")
            tp=self.importList.getTypeByFullName(tpnm, self.thisImport)
            if attrs.has_key("seqnr"):
                seqnr=int(attrs.getValue("seqnr"))
            else:
                seqnr=0
            name=attrs.getValue("id")
            # TODO fix this for new type struct.
            val=None
            if attrs.has_key("value"):
                if not attrs.has_key("value_type"):
                    raise ProjectXMLError(
                        "active connection value without value_type", 
                        self)
                #vtp=self.project.getType(attrs.getValue("value_type"))
                vtpnm=attrs.getValue("value_type")
                vtp=self.importList.getTypeByFullName(vtpnm, self.thisImport)
                valnm=attrs.getValue("value")
                val=value.interpetLiteral(valueString, tp) 
            if self.ioitem == "inputs":
                self.activeInst.setInput(name, tp, val, seqnr)
            elif self.ioitem == "outputs":
                self.activeInst.setOutput(name, tp, val, seqnr)
            elif self.ioitem == "subnet-inputs":
                self.activeInst.setSubnetInput(name, tp, val, seqnr)
            elif self.ioitem == "subnet-outputs":
                self.activeInst.setSubnetOutput(name, tp, val, seqnr)
            else:
                raise ProjectXMLError(
                                "unknown active connection ioitem '%s'"%
                                (self.ioitem), self)
        elif name == "tasks":
            pass # just ignore it; we deal with tasks when they come
        elif name == "task":
            if self.curTask is not None:
                raise ProjectXMLError("task within task", self)
            if self.activeInst is None:
                raise ProjectXMLError("task without active instance", self)
            if not attrs.has_key("seqnr"):
                raise ProjectXMLError("task has no seqnr", self)
            if not attrs.has_key("priority"):
                raise ProjectXMLError("task has no priority", self)
            priority=int(attrs.getValue("priority"))
            seqnr=int(attrs.getValue("seqnr"))
            self.curTask=task.Task(self.project, self.activeInst, 
                                   self.activeInst.getFunction(),
                                   None, priority, seqnr)
        elif name == "function-input":
            if self.curTask is None:
                raise ProjectXMLError("function-input without task", self)
            self.setFnInputReader(run.IOReader(True), name)
            self.fnInputReader.setReportFilename(self.filename)
            self.fnInputReader.startElement(name, attrs)
        elif name == "command-list":
            if self.curTask is None:
                raise ProjectXMLError("commands without task", self)
            self.cmdReader=cpc.server.command.CommandReader()
            #self.cmdReader.setReportFilename(self.filename)
        elif name == "desc":
            # A description. First find out what it describes.
            if self.type is not None:
                if ( len(self.typeStack) > 1 and 
                     self.typeStack[-2][0].isSubtype(vtype.listType)):
                    # if it is a field, describe it as a field
                    tp=self.typeStack[-2][0]
                    field=self.typeStack[-1][1]
                    lstm=tp.getListMember(field)
                    self.setDescReader(description.DescriptionReader(lstm,
                                                             self.filename),
                                       name)
                elif not self.type.isBuiltin() and len(self.typeStack)==1:
                    # it is a custom, describable type
                    self.setDescReader(description.DescriptionReader(self.type,
                                                             self.filename),
                                       name)
                else:
                    raise ProjectXMLError("description of a builtin type.",
                                          self)
            elif self.function is not None:
                self.setDescReader(description.DescriptionReader(self.function,
                                                                 self.filename),
                                   name)
            elif self.curTask is None and self.network is None:
                self.setDescReader(description.DescriptionReader(
                                                            self.thisImport,
                                                            self.filename),
                                   name)
               # raise ProjectXMLError("Unknown item to describe.")
                
        else:
            raise ProjectXMLError("Unknown tag %s"%name, self)


    def endElement(self, name):
        # first handle sub-input-readers:
        #if self.fnInputReader is not None:
        #    self.fnInputReader.endElement(name)
        #    if name == "function-input":
        #        fni=self.fnInputReader.getFunctionRunInput()
        #        fni.setMissing(self.activeInst, self.project)
        #        self.curTask.setFnInput(fni)
        #        self.fnInputReader=None
        if self.cmdReader is not None:
            self.cmdReader.endElement(name)
            if name == "command-list":
                self.curTask.addCommands(self.cmdReader.getCommands())
                self.cmdReader=None
        elif self.valueReader is not None:
            self.valueReader.endElement(name)
            if name == self.valueReaderEndTag:
                # do something with the data
                self.setValueReader(None,None)
        # then handle literals
        elif self.descReader is not None:
            self.descReader.endElement(name)
            if name == self.descReaderEndTag:
                self.descReader.finish()
                self.setDescReader(None, None)
        elif self.fnInputReader is not None:
            self.fnInputReader.endElement(name)
            if name == self.fnInputReaderEndTag:
                fni=self.fnInputReader.getFunctionRunInput()
                fni.setMissing(self.activeInst, self.project)
                self.curTask.setFnInput(fni)
                self.fnInputReader=None
        elif name == "function":
            self.function.check()
            self.thisImport.addFunction(self.function)
            self.function=None
            self.functionType=None
        elif name == "instance":
            #self.network.addInstance(self.instance)
            self.network.addInstance(self.instance)
            self.instance=None
        elif name == "network":
            self.networkStack.pop()
            if len(self.networkStack) > 0:
                self.network=self.networkStack[-1]
            else:
                self.network=None
        elif name == "controller":
            self.inController=False
        elif name == "type":
            # TODO: add types to the libs
            #self.project.getTypeCollection().add(self.type)
            self.thisImport.addType(self.type)
            self.typeStack.pop()
            if len(self.typeStack) > 0:
                self.type=self.typeStack[-1][0]
            else:
                self.type=None
        elif name == "field":
            #if self.type is not None:
            self.typeStack.pop()
            if len(self.typeStack) > 0:
                self.type=self.typeStack[-1][0]
            else:
                self.type=None
        elif (name == "inputs" or name == "outputs" or 
              name == "subnet-inputs" or name == "subnet-outputs"):
            self.ioitem=None
            self.typeStack.pop()
            if len(self.typeStack) > 0:
                self.type=self.typeStack[-1][0]
            else:
                self.type=None
        elif name == "active":
            self.activeInstStack.pop()
            if len(self.activeInstStack) > 0:
                self.activeInst=self.activeInstStack[-1]
            else:
                self.activeInst=None
        elif name == "task":
            if self.curTask.getFnInput() is None:
                raise ProjectXMLError("can't make task", self)
            self.taskList.append(self.curTask)
            self.activeInst.addTask(self.curTask)
            self.curTask=None

    def characters(self, content):
        if self.descReader is not None:
            self.descReader.characters(content)


