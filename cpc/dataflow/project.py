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
import os.path
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from pympler import muppy
    from pympler import summary
    profile=True
except:
    profile=False

import cpc.util
import apperror
import keywords
import function_io
import instance
import connection
import network
import vtype
import function
import value
import active_value
import active_inst
import active_network
import task
import transaction
import lib
import readxml
import connection
import run

log=logging.getLogger('cpc.dataflow.project')

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
        # the network lock is to prevent multiple threads from updating the 
        # dataflow layout. 
        # Only when this lock is locked, are updates such as ActiveNetwork's 
        # addConnection allowed. 
        # See the active_inst.py's documentation for detailed of all the locks
        # and how they can interact.
        self.networkLock=threading.RLock()
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
        self.fileList=value.FileList(basedir) 
        # create the active network (the top-level network)
        affectedInputAIs=set()
        self.active=active_network.ActiveNetwork(self, None, self.queue, 
                                                 "", self.networkLock) 
        if len(affectedInputAIs)!=0:
            raise ProjectError("Top-level active network has initial elements!")
        
        # now take care of imports. First get the import path
        self.topLevelImport=lib.ImportLibrary("", "", self.active)
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
        self.transactionListStackLock=threading.Lock()
        tl=transaction.TransactionList(self.networkLock, True)
        self.transactionListStack=[tl]


    def getName(self):
        """Return the project name. This is a const property"""
        return self.name
    def getBasedir(self):
        """Return the base directory. This is a const property"""
        return self.basedir
    def getNewInputSubDir(self):
        """Return the name of a new input subdir to store new externally 
           set input files in.  NOTE: it won't be created."""
        with self.networkLock:
            newsub=os.path.join(self.inputDir, "%04d"%self.inputNr)
            self.inputNr+=1
            while os.path.exists(newsub):
                newsub=os.path.join(self.inputDir, "%04d"%self.inputNr)
                self.inputNr+=1
        return newsub

    def getFileList(self):
        """Get the project's file list. This pointer is a const property, 
           and the file list has its own locking mechanism."""
        return self.fileList

    def getTopLevelLib(self):
        """Get the top-level import library"""
        return self.topLevelImport

    def getFunction(self, fname):
        """Return the function object associated with a name."""
        with self.networkLock:
            try:
                return self.functions[fname]
            except KeyError:
                raise ProjectError("function with name %s is not defined."%
                                   fname)

    def addFunction(self, function):
        """Add a function to the project."""
        with self.networkLock:
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
        #with self.updateLock:
        itemname=keywords.fixID(itemname)
        instanceName,direction,ioItemList=connection.splitIOName(itemname, None)
        instance=self.active.getNamedActiveInstance(instanceName)
        return instance.getNamedValue(direction, ioItemList)

    def scheduleSet(self, itemname, literal, outf, sourceType=None,
                    printName=None):
        """Add an instance of a set in the transaction schedule."""
        itemname=keywords.fixID(itemname)
        instanceName,direction,ioItemList=connection.splitIOName(itemname, None)
        instanceName,direction,ioItemList=connection.splitIOName(itemname, None)
        instance=self.active.getNamedActiveInstance(instanceName)
        lstItem=transaction.Set(self, itemname, instance, direction, 
                                ioItemList, literal, sourceType, printName)
        with self.transactionListStackLock:
            self.transactionListStack[-1].addItem(lstItem, self, outf)

    def scheduleConnect(self, src, dst, outf):
        """Add an instance of a connect in the transaction schedule."""
        src=keywords.fixID(src)
        dst=keywords.fixID(dst)
        lstItem=transaction.Connect(self, src, dst)
        with self.transactionListStackLock:
            self.transactionListStack[-1].addItem(lstItem, self, outf)


    def beginTransaction(self, outf):
        """Create a new transaction list."""
        tl=transaction.TransactionList(self.networkLock, False)
        with self.transactionListStackLock:
            self.transactionListStack.append(tl)
            outf.write("Beginning transaction level %d"%
                       (len(self.transactionListStack)-1))

    def commit(self, outf):
        """Commit a set of changes scheduled with scheduleSet()"""
        with self.transactionListStackLock:
            li=len(self.transactionListStack) - 1
            if li > 0:
                self.transactionListStack[li].commit(self, outf)
                self.transactionListStack.pop(li)
            else:
                raise ProjectError("No transactions to commit.")

    def rollback(self, outf):
        """Cancel a transaction."""
        with self.transactionListStackLock:
            li=len(self.transactionListStack) - 1
            if li > 0:
                outf.write("Canceling transaction level %d"%(li+1))
                self.transactionListStack.pop(li)
            else:
                raise ProjectError("No transactions to cancel.")


    def getNamedInstance(self, instname):
        item=self.active.getNamedActiveInstance(instname)
        if not isinstance(item, active_inst.ActiveInstance):
            raise ProjectError("%s is not an active instance"%instname)
        return item

    def _isIOItem(self, pathname):
        """Return true if the pathname is an IO item, rather than an instance
           item."""
        return ( (keywords.SubTypeSep in pathname) or 
                 (keywords.ArraySepStart in pathname) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.In)) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.Out)) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.SubIn)) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.SubOut)) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.ExtIn)) or
                 pathname.endswith("%s%s"%(keywords.InstSep,keywords.ExtOut)))

    def getNamedItemList(self, pathname):
        """Get an list based on a path name according to the rule
           [instance]:[instance]"""
        pathname=keywords.fixID(pathname)
        with self.networkLock:
            ret=dict()
            if self._isIOItem(pathname):
                # it is an active I/O item
                instName,direction,itemlist=connection.splitIOName(pathname, 
                                                                   None)
                try:
                    item=self.active.getNamedActiveInstance(instName)
                except active_network.ActiveError:
                    item=None
                if item is not None:
                    tp=item.getNamedType(direction, itemlist)
                    ret["type"]="input/output value"
                    ret["name"]=pathname
                    if tp is not None:
                        ret["typename"]=tp.getName()
                    else:
                        ret["typename"]="Not found"
                    if tp.isSubtype(vtype.recordType):
                        ret["subitems"]=[]
                        keys=tp.getMemberKeys()
                        for key in keys:
                            mem=tp.getRecordMember(key)
                            subi=dict()
                            subi["name"]=key
                            subi["type"]=mem.type.getName()

                            optstr=""
                            conststr=""
                            if mem.isOptional():
                                subi["optional"]=1
                            if mem.isConst():
                                subi["const"]=1
                            if mem.isComplete():
                                subi["complete"]=1
                            if mem.desc is not None:
                                subi["desc"]=mem.desc.get()
                            ret["subitems"].append( subi )
                    elif (tp.isSubtype(vtype.arrayType) or 
                          tp.isSubtype(vtype.dictType)):
                        mem=tp.getMembers()
                        subi=dict()
                        subi.type=mem.getName()
                        ret["subitems"]=[ subi ]
            else:
                try:
                    item=self.active.getNamedActiveInstance(pathname)
                except active_network.ActiveError:
                    item=None
                if item is not None:
                    if isinstance(item, active_network.ActiveNetwork):
                        ret["type"]="network"
                        ret["name"]=pathname
                        ret["instances"]=item.getActiveInstanceList(False, 
                                                                    False)
                        cputime=int(item.getCumulativeCputime())
                        if cputime > 0:
                            ret["cumulative-cputime" ]=str(cputime)
                    else:
                        ret["type"]="instance"
                        ret["name"]=item.getCanonicalName()
                        ret["fn_name"]=item.function.getFullName()
                        ret["inputs" ]=item.getInputs().getSubValueList()
                        ret["outputs" ]=item.getOutputs().getSubValueList()
                        net=item.getNet()
                        if net is not None:
                            ret["instances" ]=net.getActiveInstanceList(False,
                                                                        False)
                        ret["state"]=item.getPropagatedStateStr()
                        cputime=int(item.getCputime())
                        if cputime > 0:
                            ret["cputime" ]=str(cputime)
                        cputime=int(item.getCumulativeCputime())
                        if cputime > 0:
                            ret["cumulative-cputime" ]=str(cputime)
            if item is None:
                ret["type"]="Not found: "
                ret["name"]=pathname
            return ret


    def getNamedDescription(self, pathname):
        """Get a description of a named function/type/lib"""
        pathname=keywords.fixID(pathname)
        #with self.updateLock:
        ret=dict()
        item=self.imports.getItemByFullName(pathname)
        if item is not None:
            ret["name"]=pathname
            desc=item.getDescription()
            if desc is not None:
                ret["desc"]=desc.get()
            else:
                ret["desc"]=""
            if isinstance(item, lib.ImportLibrary):
                ret["type"]="library"
                rfuncs=[]
                funcs=item.getFunctionList()
                for f in funcs:
                    nf={ "name" : f }
                    desc=item.getFunction(f).getDescription()
                    if desc is not None:
                        nf["desc"] = desc.get()
                    else:
                        nf["desc"] = ""
                    rfuncs.append(nf)
                ret["functions"]=rfuncs
                rtypes=[]
                types=item.getTypeList()
                for t in types:
                    if not item.getType(t).isImplicit():
                        nf={ "name" : t }
                        desc=item.getType(t).getDescription()
                        if desc is not None:
                            nf["desc"] = desc.get()
                        else:
                            nf["desc"] = ""
                        rtypes.append(nf)
                if len(rtypes)>0:
                    ret["types"]=rtypes
            elif isinstance(item, function.Function):
                ret["type"]="function"
                ioitems=item.getInputs()
                inps=[]
                for key in ioitems.getMemberKeys():
                    retd=dict()
                    retd["name"]=key
                    retd["type"]=ioitems.getMember(key).getName()
                    desc=ioitems.getRecordMember(key).getDescription()
                    if desc is not None:
                        retd["desc"]=desc.get()
                    else:
                        retd["desc"]=""
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
            elif isinstance(item, vtype.Type):
                ret["type"]="type"
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
                summary.print_(sum1)
            return outf.getvalue()
        itemname=keywords.fixID(itemname)
        if self._isIOItem(itemname):
            instName,direction,ioItemList=connection.splitIOName(itemname, None)
            instance=self.active.getNamedActiveInstance(instName)
            instance.getNamedValue(direction, ioItemList).writeDebug(outf)
        else:
            #outf.write("No debug info for active instance %s\n"%itemname)
            instance=self.active.getNamedActiveInstance(itemname)
            instance.writeDebug(outf)
        return outf.getvalue()


    def getGraph(self, pathname):
        """Get an graph description based on a path name according to the rule
           [instance]:[instance]."""
        pathname=keywords.fixID(pathname)
        with self.networkLock:
            item=self.active.getNamedActiveInstance(pathname)
            ret=dict()
            if item is not None:
                if isinstance(item, active_network.ActiveNetwork):
                    ret["name"]=pathname
                    ret["instances"]=item.getActiveInstanceList(True, True)
                    ret["connections"]=item.getConnectionList()
                else:
                    net=item.getNet()
                    ret["name"]=pathname
                    ret["instances"]=net.getActiveInstanceList(True, True)
                    ret["connections"]=net.getConnectionList()
            return ret

    def addInstance(self, name, functionName):
        """Add an instance with a name and function name to the top-level
           network."""
        name=keywords.fixID(name)
        functionName=keywords.fixID(functionName)
        with self.networkLock:
            func=self.imports.getFunctionByFullName(functionName, 
                                                    self.topLevelImport)
            (net, instanceName)=self.active.getContainingNetwork(name)
            nm=""
            if net.inActiveInstance is not None:
                nm=net.inActiveInstance.getCanonicalName()
            log.debug("net=%s, instanceName=%s"%(nm, instanceName))
            inst=instance.Instance(instanceName, func, functionName)
            #self.active.addInstance(inst)
            net.addInstance(inst)

    def importTopLevelFile(self, fileObject, filename):
        """Read a source file as a top-level description."""
        with self.networkLock:
            reader=readxml.ProjectXMLReader(self.topLevelImport, self.imports,
                                            self)
            reader.readFile(fileObject, filename)

    def importName(self, name):
        """Import a named module."""
        name=keywords.fixID(name)
        with self.networkLock:
            if not self.imports.exists(name):
                baseFilename="%s.xml"%name.replace(keywords.ModSep, '/')
                baseFilename2="%s/_import.xml"%name.replace(keywords.ModSep, 
                                                            '/')
                filename=None
                for pathItem in self.conf.getImportPaths():
                    nfilename=os.path.join(pathItem, baseFilename)
                    if os.path.exists(nfilename):
                        filename=nfilename
                        break
                    nfilename=os.path.join(pathItem, baseFilename2)
                    if os.path.exists(nfilename):
                        filename=nfilename
                        break
                if filename is None:
                    raise ProjectError("Library %s not found"%name)
                log.debug("Importing library %s with file name %s"% (name, 
                                                                     filename))
                newlib=lib.ImportLibrary(name, filename, None)
                reader=readxml.ProjectXMLReader(newlib, self.imports, self)
                reader.read(filename)
                self.imports.add(newlib)
                return newlib
            else:
                return self.imports.get(name)

    def getAllTasks(self):
        """Get a list of all tasks to queue for execution."""
        taskList=[]
        self.active.getAllTasks(taskList)
        return taskList

    def cancel(self):
        """Delete all queued commands."""
        self.cmdQueue.deleteByProject(self)

    def activate(self, pathname):
        """Activate all active instances."""
        pathname=keywords.fixID(pathname)
        with self.networkLock:
            if pathname.strip() == "":
                self.active.activateAll()
            else:
                item=self.active.getNamedActiveInstance(pathname)
                item.activate()

    def deactivate(self, pathname):
        """De-activate all active instances contained in pathname (or 
           everything if pathname is empty)."""
        pathname=keywords.fixID(pathname)
        with self.networkLock:
            if pathname.strip() == "":
                self.active.deactivateAll()
            else:
                item=self.active.getNamedActiveInstance(pathname)
                item.deactivate()

    def rerun(self, pathname, recursive, clearError, outf):
        """Re-run and optionally clear an error on an item."""
        pathname=keywords.fixID(pathname)
        with self.networkLock:
            item=self.active.getNamedActiveInstance(pathname)
            ret=item.rerun(recursive, clearError, outf)
            if ret==0:
                if clearError:
                    outf.write("No errors cleared.")
                else:
                    outf.write("No reruns performed.")

    def getQueue(self):
        """Get the task queue."""
        return self.queue

    def writeXML(self, outf, indent=0):
        """Write the function definitions and top-level network description 
           in XML to outf."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outf.write('%s<cpc version="%d">\n'%(indstr, readxml.curVersion))
        for name in self.imports.getLibNames():
            outf.write('%s<import name="%s" />\n'%(iindstr,name))
        outf.write('\n')
        self.topLevelImport.writeXML(outf, indent+1)
        outf.write('%s</cpc>\n'%indstr)

    def writeXMLPointer(self, outFile):
        """Write a short pointer to where information can be found to an
           XML file."""
        outFile.write('  <cpc-project id="%s" dir=""/>\n'%(self.name))

    def readState(self,stateFile="_state.xml"):
        fname=os.path.join(self.basedir, stateFile)
        if os.path.exists(fname):
            log.debug("Importing project state from %s"%fname)
            with self.networkLock:
                reader=readxml.ProjectXMLReader(self.topLevelImport, 
                                                self.imports,
                                                self)
                reader.readFile(fname, fname)
                tasks=reader.getTaskList()
                for tsk in tasks:
                    cmds=tsk.getCommands()
                    if len(cmds) < 1:
                        log.debug("Queuing task")
                        self.queue.put(tsk)
                    else:
                        log.debug("Queuing command")
                        for cmd in cmds:
                            self.cmdQueue.add(cmd)


    def writeState(self):
        with self.networkLock:
            fname=os.path.join(self.basedir, "_state.xml")
            nfname=os.path.join(self.basedir, "_state.xml.new")
            fout=open(nfname, 'w')
            fout.write('<?xml version="1.0"?>\n')
            self.writeXML(fout, 0)
            fout.close()
            # now we use POSIX file renaming  atomicity to make sure the state 
            # is always a consistent file.
            os.rename(nfname, fname)

