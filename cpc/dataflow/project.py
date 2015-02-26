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
import threading
import os
import dill as pickle

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from pympler import muppy
    from pympler import summary
    from pympler import refbrowser
    profile=True
except:
    profile=False

import cpc.util
import apperror
import keywords
import task
import transaction
import lib
import value
import vtype
#import readxml
from cpc.dataflow.datanetwork import DataNetwork
from cpc.dataflow.function import Function, FunctionBase

log=logging.getLogger(__name__)

class ProjectError(apperror.ApplicationError):
    pass


class Project(object):
    """The top-level class describing a running function network together
       with all function definitions. """
    def __init__(self, name, basedir, conf, queue=None, cmdQueue=None):
        """Initializes an empty project

           name = the name of the project
           basedir = the full (existing) base directory of the project
           queue = an optional shared task queue
        """
        # The Update lock prevents multiple threads from updating values
        # in the same project. This probably has less impact on performance
        # than it sounds: Python is single-threaded at its core, and only
        # emulates multithreading. Also: this would only be a problem if
        # updating values & scheduling tasks is the rate-limiting step.
        self.updateLock=threading.RLock()
        self.conf=conf
        self.name=name
        self.basedir=basedir
        if not os.path.exists(self.basedir):
            os.mkdir(self.basedir)
        log.debug("Creating project %s"%name)
        if queue is None:
            log.debug("Creating new task queue %s"%name)
            self.queue=task.TaskQueue()
        else:
            self.queue=queue
        self.cmdQueue=cmdQueue
        # the file list
        #self.fileList=value.FileList(basedir)
        # create the active network (the top-level network)
        self.network=DataNetwork(project=self, taskQueue=self.queue, dirName="",
                                 lock=self.updateLock)
        # now take care of imports. First get the import path
        self.topLevelImport=lib.ImportLibrary("", None, self.network)
        # a list of available libraries
        self.availableLibraries=dict()
        # create a list of function definitions
        self.functions=dict()
        # create a list of already performed imports
        self.imports=lib.ImportList()
        # and this is where we can start importing builtins, etc.
        self.inputDir=os.path.join(self.basedir, "_inputs")
        if not os.path.exists(self.inputDir):
            os.mkdir(self.inputDir)
        self.inputNr=0
        # a list of scheduled changes and its lock
        self.transactionStackLock=threading.Lock()
        tl=transaction.Transaction(self, None, self.network,
                                   self.topLevelImport)
        self.transactionStack=[tl]

    def getName(self):
        """Return the project name. This is a const property"""
        return self.name
    def getBasedir(self):
        """Return the base directory. This is a const property"""
        return self.basedir
    def getNewInputSubDir(self):
        """Return the name of a new input subdir to store new externally
           set input files in.  NOTE: it won't be created."""
        with self.updateLock:
            newsub=os.path.join(self.inputDir, "%04d"%self.inputNr)
            self.inputNr+=1
            while os.path.exists(newsub):
                newsub=os.path.join(self.inputDir, "%04d"%self.inputNr)
                self.inputNr+=1
        return newsub

    #def getFileList(self):
        #"""Get the project's file list. This pointer is a const property,
           #and the file list has its own locking mechanism."""
        #return self.fileList

    def getTopLevelLib(self):
        """Get the top-level import library"""
        return self.topLevelImport

    def getFunction(self, fname):
        """Return the function object associated with a name."""
        with self.updateLock:
            try:
                return self.functions[fname]
            except KeyError:
                raise ProjectError("function with name %s is not defined."%
                                   fname)

    def addFunction(self, function):
        """Add a function to the project."""
        with self.updateLock:
            name=function.getName()
            if self.functions.has_key(name):
                raise ProjectError("function with name %s already exists."%name)
            self.functions[name]=function

    def getImportList(self):
        """Get the function import list."""
        return self.imports

    def getNamedValue(self, itemname):
        """Get a value for a specific name according to the rule
           [instance]:[instance].[ioitem]."""
        with self.updateLock:
            itemlist=vtype.parseItemList(itemname)
            item=self.getSubValue(itemlist)
            return item


    def _tryImmediateTransaction(self, outf):
        """Perform an immediate transaction, if the transaction stack has
           length 1 (i.e. the last operation was on the topmost level)..

           NOTE: assumes a locked tranactionStackLock"""
        if len(self.transactionStack) == 1:
            self.transactionStack[0].run(outf)
            # now replace the transaction with a fresh one.
            self.transactionStack[0] = transaction.Transaction(self, None,
                                                 self.network,
                                                 self.topLevelImport)
            return True
        return False

    def scheduleSet(self, itemname, literal, outf, sourceType=None,
                    printName=None):
        """Add an instance of a set in the transaction schedule."""
        itemname=keywords.fixID(itemname)
        with self.transactionStackLock:
            log.debug("ADD/SET: %s, %s, %s, %s" % (itemname, literal, sourceType, printName))
            sv=self.transactionStack[-1].addSetValue(itemname, literal,
                                                     sourceType, printName)
            if not self._tryImmediateTransaction(outf):
                sv.describe(outf)



    def beginTransaction(self, outf):
        """Create a new transaction list."""
        tl=transaction.Transaction(self, None, self.network,
                                   self.topLevelImport)
        with self.transactionStackLock:
            self.transactionStack.append(tl)
            level=len(self.transactionStack)-1
        outf.write("Beginning transaction level %d"%level)

    def commit(self, outf):
        """Commit a set of changes scheduled with scheduleSet()"""
        with self.transactionStackLock:
            if len(self.transactionStack) > 1:
                li=self.transactionStack.pop(-1)
                li.run(outf)
            else:
                raise ProjectError("No transactions to commit.")

    def rollback(self, outf):
        """Cancel a transaction."""
        with self.transactionStackLock:
            li=len(self.transactionStack) - 1
            if li > 0:
                outf.write("Canceling transaction level %d"%(li+1))
                self.transactionStack.pop(li)
            else:
                raise ProjectError("No transactions to cancel.")


    def getNamedInstance(self, instname):
        pathname=keywords.fixID(instname)
        with self.updateLock:
            itemlist=vtype.parseItemList(pathname)
            item=self.getSubValue(itemlist)
        if not isinstance(item, Function):
            raise ProjectError("%s is not an active instance"%instname)
        return item


    def getNamedItemList(self, pathname):
        """Get an list based on a path name according to the rule
           [instance]:[instance]"""
        pathname=keywords.fixID(pathname)
        with self.updateLock:
            itemlist=vtype.parseItemList(pathname)
            item=self.getSubValue(itemlist)
            log.debug('PATHNAME: %s, LIST: %s, item: %s' % (pathname, itemlist, item))
            ret=dict()
            if item is None:
                ret["type"]="Not found: "
                ret["name"]=pathname
            elif isinstance(item, value.Value):
                # it is an active I/O item
                ret["type"]="input/output value"
                ret["name"]=pathname
                ret["typename"]=item.getTypeString()
                # FIXME:
                #if tp.isSubtype(vtype.recordType):
                    #ret["subitems"]=[]
                    #keys=tp.getMemberKeys()
                    #for key in keys:
                        #mem=tp.getRecordMember(key)
                        #subi=dict()
                        #subi["name"]=key
                        #subi["type"]=mem.type.getName()
                        ##subi["value-type"]=mem.type.jsonDescribe()
                        #optstr=""
                        #conststr=""
                        #if mem.isOptional():
                            #subi["optional"]=1
                        #if mem.isConst():
                            #subi["const"]=1
                        #if mem.isComplete():
                            #subi["complete"]=1
                        #if mem.desc is not None:
                            #subi["desc"]=mem.desc.get()
                        #ret["subitems"].append( subi )
                if isinstance(item, (value.ListValue, value.DictValue)):
                    memType=item.dataType
                    subi={"type" : memType.getTypeString()}
                    ret["subitems"]=[ subi ]
            elif isinstance(item, Function):
                ret["type"]="instance"
                ret["state"]=item.state
                ret["name"]=item.name
                ret["fn_name"]=item.name
                ret["inputs" ]=item.getAllInputNames()
                ret["outputs" ]=item.getAllOutputNames()
                net=item.dataNetwork
                if net is not None:
                    ret["instances" ]=net.getActiveInstanceList(False, False)
                #FIXME:
                #ret["state"]=item.getPropagatedStateStr()
                #cputime=int(item.getCputime())
                #if cputime > 0:
                    #ret["cputime" ]=str(cputime)
                #cputime=int(item.getCumulativeCputime())
                #if cputime > 0:
                    #ret["cumulative-cputime" ]=str(cputime)
            elif isinstance(item, Project):
                ret["type"]="network"
                ret["name"]=pathname
                ret["instances"]=item.network.getActiveInstanceList(False, False)
                #cputime=int(item.network.getCumulativeCputime())
                #if cputime > 0:
                    #ret["cumulative-cputime" ]=str(cputime)
            else:
                ret["type"]="Unknown type of item: "
                ret["name"]=pathname
            return ret


    def getNamedDescription(self, pathname):
        """Get a description of a named function/type/lib"""
        pathname=keywords.fixID(pathname)
        with self.updateLock:
            ret=dict()
            item=self.imports.getItemByFullName(pathname)
            if item is not None:
                ret["name"]=pathname
                ret["desc"]=item.getDescription() or ""
                log.debug('Get description of: %s' % item)
                if isinstance(item, lib.ImportLibrary):
                    ret["type"]="library"
                    rfuncs=[]
                    for name, f in item.functions.items():
                        nf={ "name" : name }
                        nf["desc"] = f.getDescription() or ""
                        rfuncs.append(nf)
                    ret["functions"]=rfuncs
                    #FIXME:
                    #rtypes=[]
                    #types=item.getTypeList()
                    #for t in types:
                        #if not item.getType(t).isImplicit():
                            #nf={ "name" : t }
                            #desc=item.getType(t).getDescription()
                            #if desc is not None:
                                #nf["desc"] = desc.get()
                            #else:
                                #nf["desc"] = ""
                            #rtypes.append(nf)
                    #if len(rtypes)>0:
                        #ret["types"]=rtypes
                elif isinstance(item, FunctionBase):
                    ret["type"]="function"
                    log.debug("GET FUNCTION.")
                    ioitems=item.getInputs()
                    log.debug("IOITEMS: %s" % ioitems)
                    inps=[]
                    for key in ioitems.getMemberKeys():
                        retd=dict()
                        retd["name"]=key
                        retd["type"]=ioitems.getMember(key).getName()
                        retd["desc"]=ioitems.getRecordMember(key).getDescription() or ""
                        inps.append(retd)
                    ret["inputs"]=inps
                    ioitems=item.getOutputs()
                    outs=[]
                    for key in ioitems.getMemberKeys():
                        retd=dict()
                        retd["name"]=key
                        retd["type"]=ioitems.getMember(key).getName()
                        desc=ioitems.getRecordMember(key).getDescription()
                        if desc is not None:
                            retd["desc"]=desc.get()
                        else:
                            retd["desc"]=""
                        outs.append(retd)
                    ret["outputs"]=outs
                #FIXME:
                #elif isinstance(item, vtype.Type):
                    #ret["type"]="type"
                else:
                    ret["type"]=""
            else:
                ret["name"]="Not found: %s"%pathname
                ret["desc"]=""
            return ret

    def getDebugInfo(self, itemname):
        """Give debug info about a particular item."""
        global profile
        outf=StringIO()
        if itemname == "":
            outf.write("the item was empty")
            if profile:
                all_objects = muppy.get_objects()
                sum1 = summary.summarize(all_objects)
                summary.print_(sum1, 100)
                ib = refbrowser.InteractiveBrowser(self)
                ib.main()
            return outf.getvalue()
        itemname=keywords.fixID(itemname)
        itemlist=vtype.parseItemList(itemname)
        item=self.getSubValue(itemlist)
        item.writeDebug(outf)
        return outf.getvalue()

    #FIXME:
    #def getGraph(self, pathname):
        #"""Get an graph description based on a path name according to the rule
           #[instance]:[instance]."""
        #pathname=keywords.fixID(pathname)
        #with self.updateLock:
            #itemlist=vtype.parseItemList(pathname)
            #item=self.getSubValue(itemlist)
            #ret=dict()
            #if item is not None:
                #if isinstance(item, active_inst.ActiveInstance):
                    #net=item.network
                    #ret["name"]=pathname
                    #ret["instances"]=net.getActiveInstanceList(True, True)
                    #ret["connections"]=net.getConnectionList()
                #elif isinstance(item, Project):
                    #net=item.network
                    #ret["name"]=pathname
                    #ret["instances"]=net.getActiveInstanceList(True, True)
                    #ret["connections"]=net.getConnectionList()
                #else:
                    #ret["name"]=pathname
                    #ret["instances"]=[]
                    #ret["connections"]=[]
            #return ret

    #FIXME:
    def addInstance(self, name, functionName):
        """Add an instance with a name and function name to the top-level
           network."""
        name=keywords.fixID(name)
        functionName=keywords.fixID(functionName)
        with self.updateLock:
            func=self.imports.getFunctionByFullName(functionName,
                                                    self.topLevelImport)
            log.debug('FUNC: %s' % func)
            (net, instanceName)=self.network.getContainingNetwork(name)
            nm=""
            log.debug('NET: %s, instance name: %s' % (net, instanceName))
            if net.containingInstance is not None:
                nm=net.containingInstance.getCanonicalName()
            log.debug('NM: %s' % nm)
            ##log.debug("net=%s, instanceName=%s"%(nm, instanceName))
            #inst=instance.Instance(instanceName, func, functionName)
            net.newInstance(func, name)

    #FIXME:
    #def importTopLevelFile(self, fileObject, filename):
        #"""Read a source file as a top-level description."""
        #with self.updateLock:
            #reader=readxml.ProjectXMLReader(self.topLevelImport, self.imports,
                                            #self)
            #reader.readFile(fileObject, filename)

    def getLibrariesDict(self):

        return lib.getModulesDict()


    def importName(self, name):
        """Import a named module."""

        if not self.availableLibraries:
            self.availableLibraries = self.getLibrariesDict()

        name=keywords.fixID(name)

        with self.updateLock:
            if not name in self.availableLibraries:
                raise(ProjectError('Library "%s" not found' % name))

            if not self.imports.exists(name):
                try:
                    newLib = self.availableLibraries[name]()
                    impLib = lib.ImportLibrary(name, newLib, None)
                    impLib.functions = newLib.functions
                    self.imports.add(impLib)
                    return newLib
                except Exception as e:
                    log.debug('Cannot load library %s: %s' % name, e)
            else:
                return self.imports.get(name)

    def getAllTasks(self):
        """Get a list of all tasks to queue for execution."""
        taskList=[]
        self.network.getAllTasks(taskList)
        return taskList

    def cancel(self):
        """Delete all queued commands."""
        self.cmdQueue.deleteByProject(self)

    def activate(self, pathname):
        """Activate all active instances."""
        pathname=keywords.fixID(pathname)
        with self.updateLock:
            itemlist=vtype.parseItemList(pathname)
            item=self.getSubValue(itemlist)
            if isinstance(item, Function):
                item.unfreeze()
            elif isinstance(item, Project):
                item.network.activateAll()
            else:
                raise ProjectError("%s is not an instance"%pathname)

    def deactivate(self, pathname):
        """De-activate all active instances contained in pathname (or
           everything if pathname is empty)."""
        pathname=keywords.fixID(pathname)
        with self.updateLock:
            itemlist=vtype.parseItemList(pathname)
            item=self.getSubValue(itemlist)
            log.debug("%s"%str(item))
            if isinstance(item, Function):
                item.freeze()
            elif isinstance(item, Project):
                item.network.deactivateAll()
            else:
                raise ProjectError("%s is not an instance"%pathname)

    #FIXME:
    #def rerun(self, pathname, recursive, clearError, outf):
        #"""Re-run and optionally clear an error on an item."""
        #pathname=keywords.fixID(pathname)
        #with self.updateLock:
            #itemlist=vtype.parseItemList(pathname)
            #item=self.getSubValue(itemlist)
            #if isinstance(item, active_inst.ActiveInstance):
                #ret=item.rerun(recursive, clearError, outf)
                #if ret==0:
                    #if clearError:
                        #outf.write("No errors cleared.")
                    #else:
                        #outf.write("No reruns performed.")
            #else:
                #raise ProjectError("%s is not an instance"%pathname)

    def getQueue(self):
        """Get the task queue."""
        return self.queue

    def readState(self,stateFile="_state.pickle"):
        return
        fname=os.path.join(self.basedir, stateFile)
        if os.path.exists(fname):
            #confLock = self.conf.lock
            #queue = self.queue
            #cmdQueue = self.cmdQueue
            #transactionStackLock = self.transactionStackLock
            #libLock = self.imports.lock

            log.debug("Importing project state from %s"%fname)
            updateLock = self.updateLock
            #self.updateLock = None
            #self.conf.lock = None
            #self.queue = None
            #self.cmdQueue = None
            #self.transactionStackLock = None
            #self.imports.lock = None
            #self.network.lock = None
            #self.network.taskQueue = None
            with updateLock:
                fin=open(fname, 'r')
                self=pickle.load(fin)
            self.updateLock = updateLock
            #self.conf.lock = confLock
            #self.queue = queue
            #self.cmdQueue = cmdQueue
            #self.transactionStackLock = transactionStackLock
            #self.imports.lock = libLock
            #self.network.lock = updateLock
            #self.network.taskQueue = queue


    def writeState(self):
        #updateLock = self.updateLock
        #confLock = self.conf.lock
        #queue = self.queue
        #cmdQueue = self.cmdQueue
        #transactionStackLock = self.transactionStackLock
        #libLock = self.imports.lock
        #self.updateLock = None
        #self.conf.lock = None
        #self.queue = None
        #self.cmdQueue = None
        #self.transactionStackLock = None
        #self.imports.lock = None
        #self.network.lock = None
        #self.network.taskQueue = None
        with self.updateLock:
            fname=os.path.join(self.basedir, "_state.pickle")
            nfname=os.path.join(self.basedir, "_state.pickle.new")
            fout=open(nfname, 'w')
            pickle.dump(self, fout)
            fout.close()
            ## now we use POSIX file renaming  atomicity to make sure the state
            ## is always a consistent file.
            os.rename(nfname, fname)
        #self.updateLock = updateLock
        #self.conf.lock = confLock
        #self.queue = queue
        #self.cmdQueue = cmdQueue
        #self.transactionStackLock = transactionStackLock
        #self.imports.lock = libLock
        #self.network.lock = updateLock
        #self.network.taskQueue = queue

    ########################################################
    # Member functions from the ValueBase interface:
    ########################################################
    def _getSubVal(self, itemList):
        """Helper function"""
        subval=self.network.getInstance(itemList[0])
        return subval

    def getSubValue(self, itemList):
        """Get a specific subvalue through a list of subitems, or return None
           if not found.
           itemList = the path of the value to return"""
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        log.debug('SUBVAL: %s, %s' % (subval, itemList))
        if subval is not None:
            return subval.getSubValue(itemList[1:])
        return None

    def getCreateSubValue(self, itemList):
        """Get or create a specific subvalue through a list of subitems, or
           return None if not found.
           itemList = the path of the value to return/create.
        """
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.getCreateSubValue(itemList[1:])
        #raise ValError("Cannot create sub value of project")
        raise Exception("Cannot create sub value of project")

    def getClosestSubValue(self, itemList):
        """Get the closest relevant subvalue through a list of subitems,

           itemList = the path of the value to get the closest value for """
        log.debug('PROJECT SUBVAL path: %s' % itemList)
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        log.debug('PROJECT SUBVAL: %s' % subval)
        if subval is not None:
            return subval.getClosestSubValue(itemList[1:])
        return self

    def getSubValueList(self):
        """Return a list of addressable subvalues."""
        return self.network.getInstanceNameList()

    def getSubValueIterList(self):
        """Return an iterable list of addressable subvalues."""
        return self.getSubValueList()

    def hasSubValue(self, itemList):
        """Check whether a particular subvalue exists"""
        if len(itemList) == 0:
            return True
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.hasSubValue(itemList[1:])
        return False

    #def getType(self):
        #"""Return the type associated with this value"""
        #return vtype.instanceType

    def getDescription(self):
        """Return a 'description' of a value: an item that can be passed to
           the client describing the value."""
        ret=self.network.getActiveInstanceList(False, False)
        return ret

    ########################################################

