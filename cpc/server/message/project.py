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
import os
import tarfile
from cpc.util.conf.server_conf import ServerConf

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from server_command import ServerCommand

import cpc.dataflow
import cpc.util
import cpc.server.state.projectlist
from cpc.server.state.user_handler import UserHandler, UserError, UserLevel
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
import cpc.util.exception
from cpc.dataflow.vtype import instanceType
from cpc.network.node import Nodes, getSelfNode


log=logging.getLogger('cpc.server.projectcmd')


class ProjectServerCommandException(cpc.util.exception.CpcError):
    pass


class ProjectServerCommand(ServerCommand):
    """Base class for commands acting on projects.
        If only_explicit, then return explicit project or None"""
    def getProject(self, request, serverState, only_explicit=False):
        """Get a named or default project"""
        #get the user
        user = self.getUser(request)

        #is the project specified explicitly?
        if request.hasParam('project'):
            prjName=request.getParam('project')
        else:
            if only_explicit:
                return None
            prjName=request.session.get('default_project_name', None)
            if prjName is None:
                raise cpc.util.exception.CpcError("No project selected")

        #we check this at every command, as it may change
        project = serverState.getProjectList().get(prjName)
        if not UserHandler().userAccessToProject(user,prjName):
            raise UserError("You don't have access to this project")
        return project

    def getUser(self, request):
        if 'user' not in request.session:
            log.error("A command related to project was called with no user set")
            raise UserError("Unauthorized")
        return request.session['user']

class SCProjects(ProjectServerCommand):
    """List all projects for user, or all projects in system if user is
       superuser"""
    def __init__(self):
        ServerCommand.__init__(self, "projects")

    def run(self, serverState, request, response):
        user = self.getUser(request)
        if user.isSuperuser():
            lst = lst=serverState.getProjectList().list()
        else:
            lst = UserHandler().getProjectListForUser(user)
        response.add(lst)
        log.info("Listed %d projects"%(len(lst)))

class SCProjectStart(ProjectServerCommand):
    """Start a new project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-start")

    def run(self, serverState, request, response):
        name=request.getParam('name')
        user=self.getUser(request)
        serverState.getProjectList().add(name)
        request.session.set("default_project_name", name)
        UserHandler().addUserToProject(user, name)
        response.add("Project created: %s"%name)
        log.info("Started new project %s"%(name))

class SCProjectDelete(ProjectServerCommand):
    """Delete a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-delete")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        name=prj.getName()
        delDir = request.hasParam('delete-dir')
        msg = " and its directory %s"%prj.getBasedir() if delDir else ""
        serverState.getProjectList().delete(prj, delDir)
        UserHandler().wipeAccessToProject(name)
        if ( ( 'default_project_name' in request.session ) and 
             ( name == request.session['default_project_name'] ) ):
            request.session['default_project_name'] = None
        response.add("Project deleted: %s%s."%(name, msg))
        log.info("Deleted project %s"%(name))

class SCProjectSetDefault(ProjectServerCommand):
    """Set the default project ."""
    def __init__(self):
        ServerCommand.__init__(self, "project-set-default")

    def run(self, serverState, request, response):
        name=request.getParam('name')
        user=self.getUser(request)
        #serverState.getProjectList().setDefault(name)
        # get the project to check whether it exists
        project=serverState.getProjectList().get(name)
        if not UserHandler().userAccessToProject(user,name):
            raise UserError("You don't have access to this project")
        request.session.set("default_project_name", name)
        response.add("Changed to project: %s"%name)
        log.info("Changed to project: %s"%name)

class SCProjectGetDefault(ProjectServerCommand):
    """Get the default project ."""
    def __init__(self):
        ServerCommand.__init__(self, "project-get-default")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        name=prj.getName()
        response.add("Working project: %s"%name)
        log.info("Working project: %s"%name)

class SCProjectGrantAccess(ProjectServerCommand):
    """Grants access to the current project to a user"""
    def __init__(self):
        ServerCommand.__init__(self, "grant-access")

    def run(self, serverState, request, response):
        name=request.getParam('name')
        prj=self.getProject(request, serverState)
        prjName=prj.getName()
        usrhandler = UserHandler()
        target_user=usrhandler.getUserFromString(name)
        if target_user is None:
            raise ProjectServerCommandException("User %s doesn't exist"%name)
        usrhandler.addUserToProject(target_user, prjName)
        response.add("Granted access to user %s on project %s"%(name, prjName))
        log.info("Granted access to %s on project %s"%(name, prjName))

class SCProjectActivate(ProjectServerCommand):
    """Activate all elements in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-activate")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        prj.activate(item)
        if item == "":
            response.add("Activated all items in project %s"%prj.getName())
            log.info("Activated all items in project %s"%prj.getName())
        else:
            response.add("Activated: %s in project %s"%(item, prj.getName()))
            log.info("Activated: %s in project %s"%(item, prj.getName()))

class SCProjectDeactivate(ProjectServerCommand):
    """De-activate all elements in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-deactivate")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        prj.deactivate(item)
        if item == "":
            response.add("De-activated all items in project %s"%prj.getName())
            log.info("De-activated all items in project %s"%prj.getName())
        else:
            response.add("De-activated: %s in project %s"%(item, prj.getName()))
            log.info("De-activated: %s in project %s"%(item, prj.getName()))

class SCProjectRerun(ProjectServerCommand):
    """Force a rerun and optionally clear an error in an active instance."""
    def __init__(self):
        ServerCommand.__init__(self, "project-rerun")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        if ( request.hasParam('recursive') and 
             int(request.getParam('recursive')) == 1):
            recursive=True
        else:
            recursive=False
        if ( request.hasParam('clear-error') and 
             int(request.getParam('clear-error')) == 1):
            clearError=True
        else:
            clearError=False
        outf=StringIO()
        lst=prj.rerun(item, recursive, clearError, outf)
        response.add(outf.getvalue())
        log.info("Force rerun on %s: %s"%(prj.getName(), item))

class SCProjectList(ProjectServerCommand):
    """List named items in a project: instances or networks."""
    def __init__(self):
        ServerCommand.__init__(self, "project-list")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        lst=prj.getNamedItemList(item)
        response.add(lst)
        log.info("Project list on %s: %s"%(prj.getName(), item))

class SCProjectDebug(ProjectServerCommand):
    """Debug named items in a project - implementation dependent."""
    def __init__(self):
        ServerCommand.__init__(self, "project-debug")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        resp=prj.getDebugInfo(item)
        log.info("Debug request %s, response is '%s'"%(item, resp))
        response.add(resp)


class SCProjectInfo(ProjectServerCommand):
    """Get project item descriptions."""
    def __init__(self):
        ServerCommand.__init__(self, "project-info")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        desc=prj.getNamedDescription(item)
        response.add(desc)
        log.info("Project info on %s: %s"%(prj.getName(), item))

class SCProjectLog(ProjectServerCommand):
    """Get an active instance log."""
    def __init__(self):
        ServerCommand.__init__(self, "project-log")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        inst=prj.getNamedInstance(item)
        logf=inst.getLog()
        if logf is None:
            response.add('Instance %s has no log'%item, status="ERROR")
            return
        if not os.path.exists(logf.getFilename()):
            response.add("%s: log empty"%item)
        try:
            fob=open(logf.getFilename(), "r")
        except IOError:
            response.add("Instance %s: can't read log"%item, status="ERROR")
            return
        response.setFile(fob, 'application/text')
        log.info("Project log on %s: %s"%(prj.getName(), item))
       

class SCProjectGraph(ProjectServerCommand):
    """Get network graph."""
    def __init__(self):
        ServerCommand.__init__(self, "project-graph")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        if request.hasParam('item'):
            item=request.getParam('item')
        else:
            item=""
        lst=prj.getGraph(item)
        response.add(lst)
        log.info("Project graph on %s: %s"%(prj.getName(), item))


class SCProjectUpload(ProjectServerCommand):
    """Upload a project file."""
    def __init__(self):
        ServerCommand.__init__(self, "project-upload")
    def run(self, serverState, request, response):
        upfile=request.getFile('upload')
        prj=self.getProject(request, serverState)
        prj.importTopLevelFile(upfile, "uploaded file")
        response.add("Read file")
        log.info("Project upload on %s"%(prj.getName()))


class SCProjectAddInstance(ProjectServerCommand):
    """Add an instance to the top-level active network."""
    def __init__(self):
        ServerCommand.__init__(self, "project-add-instance")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        name=request.getParam('name')
        functionName=request.getParam('function')
        prj.addInstance(name, functionName)
        response.add("Added instance '%s' of function %s"%(name, functionName))
        log.info("Add-instance on %s: %s of %s"%(prj.getName(), name,
                                                 functionName))

class SCProjectConnect(ProjectServerCommand):
    """Add a connection to the top-level active network."""
    def __init__(self):
        ServerCommand.__init__(self, "project-connect")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        src=request.getParam('source')
        dst=request.getParam('destination')
        outf=StringIO()
        prj.scheduleConnect(src, dst, outf)
        response.add(outf.getvalue())
        log.info("Connected %s: %s -> %s"%(prj.getName(), src, dst))

class SCProjectImport(ProjectServerCommand):
    """Import a module (file/lib) to the project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-import")
    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        module=request.getParam('module')
        prj.importName(module)
        response.add("Imported module %s"%(module))
        log.info("Imported module %s: %s"%(prj.getName(), module))

class SCProjectGet(ProjectServerCommand):
    """Get an i/o item in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-get")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        itemname=request.getParam('item')
        if itemname is None:
            itemname=""
        itemname=itemname.strip()
        if not request.hasParam("getFile"):
            ret=dict()
            ret["name"]=itemname
            try:
                val=prj.getNamedValue(itemname)
                if val is not None:
                    ret["value"]=val.getDesc()
                else:
                    ret["value"]="not found"    
            #except cpc.dataflow.ApplicationError as e:
            #    ret["value"]="not found"    
            finally:
                pass
            response.add(ret)
        else:
            try:
                val=prj.getNamedValue(itemname)
                if (val is not None and 
                    val.getType().isSubtype(cpc.dataflow.fileType)):
                    if val.fileValue is not None:
                        fname=val.fileValue.getAbsoluteName()
                    else:
                        fname=val.value
                    if fname is None:
                        response.add('Item %s not set'%itemname)
                        return
                    fob=open(fname, 'r')
                    #response.add('%s'%itemname)
                    response.setFile(fob, 'application/text')
                else:
                    response.add('Item %s not a file'%itemname, status="ERROR")
            except cpc.dataflow.ApplicationError as e:
                response.add('Item %s not found'%itemname, status="ERROR")
            except IOError as e:
                response.add('Item %s not found'%itemname, status="ERROR")
        log.info("Project get %s: %s"%(prj.getName(), itemname))


class SCProjectSave(ProjectServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "project-save")

    def run(self, serverState, request, response):
        if request.hasParam('project'):
            project=request.getParam('project')
            try:
                tff = serverState.saveProject(project)
                response.setFile(tff,'application/x-tar')
                log.info("Project save %s"%project)
            except Exception as e:
                response.add(e.message,status="ERROR")

        else:
            response.add("No project specified for save",status="ERROR")


class SCProjectLoad(ProjectServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "project-load")

    def run(self, serverState, request, response):
        projectName = request.getParam("project")
        user = self.getUser(request)
        if(request.haveFile("projectFile")):
            projectBundle=request.getFile('projectFile')

            try:

                serverState.getProjectList().add(projectName)
                UserHandler().addUserToProject(user, projectName)
                extractPath = "%s/%s"%(ServerConf().getRunDir(),projectName)
                tar = tarfile.open(fileobj=projectBundle,mode="r")
                tar.extractall(path=extractPath)
                tar.close()
                serverState.readProjectState(projectName)

            except:
                response.add("No project file provided",status="ERROR")
                return

            response.add("Project restored as %s"%projectName)
            log.info("Project load %s"%(projectName))
        else:
            response.add("No project file provided",status="ERROR")
            log.info("Project load %s failed"%(projectName))



class SCProjectSet(ProjectServerCommand):
    """Set an i/o item in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-set")

    def run(self, serverState, request, response):
        upfile=None
        filename=None
        if request.haveFile('upload'):
            upfile=request.getFile('upload')
            filename=os.path.basename(request.getParam('filename'))
        setval=request.getParam('value')
        prj=self.getProject(request, serverState)
        itemname=request.getParam('item')
        try:
            outf=StringIO()
            if upfile is None:
                prj.scheduleSet(itemname, setval, outf)
            else:
                # write out the file 
                dir=prj.getNewInputSubDir()
                os.mkdir(dir)
                setval=os.path.join(dir, filename)
                #if not tp.isSubtype(cpc.dataflow.fileType):
                #    raise cpc.util.CpcError("%s does not expect a file"%
                #                            itemname)
                #outValue=cpc.dataflow.FileValue(setval)
                outFile=open(setval, "w")
                outFile.write(upfile.read())
                outFile.close()
                prj.scheduleSet(itemname, setval, outf, cpc.dataflow.fileType,
                                printName=filename)
            response.add(outf.getvalue())
        except cpc.dataflow.ApplicationError as e:
            response.add("Item not found: %s"%(str(e)))
        log.info("Project set %s: %s"%(prj.getName(), itemname))

class SCProjectTransact(ProjectServerCommand):
    """Start a transaction to be able to commit several project-set commands 
       in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-transact")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        outf=StringIO()
        prj.beginTransaction(outf)
        response.add(outf.getvalue())
        log.info("Project transact %s"%(prj.getName()))

class SCProjectCommit(ProjectServerCommand):
    """Commit several project-set commands in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-commit")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        outf=StringIO()
        prj.commit(outf)
        response.add(outf.getvalue())
        log.info("Project commit %s"%(prj.getName()))

class SCProjectRollback(ProjectServerCommand):
    """Cancel several project-set commands in a project."""
    def __init__(self):
        ServerCommand.__init__(self, "project-rollback")

    def run(self, serverState, request, response):
        prj=self.getProject(request, serverState)
        outf=StringIO()
        prj.rollback(outf)
        response.add(outf.getvalue())
        log.info("Project rollback %s"%(prj.getName()))

class SCStatus(ProjectServerCommand):
    """ Fetches general information about the server, network and projects """
    def __init__(self):
        ServerCommand.__init__(self, "status")

    def run(self, serverState, request, response):
        ret_dict = {}

        # handle project status
        user = self.getUser(request)
        explicit_project=self.getProject(request, serverState, only_explicit=True)
        if explicit_project is not None:
            projects = [explicit_project.getName()]
        else:
            if user.isSuperuser():
                projects = lst=serverState.getProjectList().list()
            else:
                projects = UserHandler().getProjectListForUser(user)
        ret_prj_dict = {}

        for prj_str in projects:
            ret_prj_dict[prj_str] = dict()
            queue = {'queue' : [], 'running': []}
            state_count = {}
            err_list=[]
            warn_list=[]
            prj_obj = serverState.getProjectList().get(prj_str)
            # we iterate over the childred rather than calling _traverseInstance
            # here to avoid the project itself being counted as an instance
            for child in prj_obj.getSubValueIterList():
                self._traverseInstance(prj_obj.getSubValue([child]), 
                                       state_count, queue, err_list, 
                                       warn_list)
            ret_prj_dict[prj_str]['states'] = state_count
            ret_prj_dict[prj_str]['queue']  = queue
            ret_prj_dict[prj_str]['errors'] = err_list
            ret_prj_dict[prj_str]['warnings'] = warn_list
            if prj_str == request.session.get('default_project_name', None):
                ret_prj_dict[prj_str]['default']=True
        ret_dict['projects'] = ret_prj_dict
        if explicit_project is not None:
            # client only want info for this project, return with that.
            response.add("", ret_dict)
            return

        # handle network
        topology = self._getTopology(serverState)
        num_workers = 0
        num_servers = 0
        num_local_workers = len(serverState.getWorkerStates())
        num_local_servers = len(ServerConf().getNodes().nodes)
        for name, node in topology.nodes.iteritems():
            num_workers += len(node.workerStates)
            num_servers += 1
        ret_dict['network'] = {
            'workers': num_workers,
            'servers': num_servers,
            'local_workers': num_local_workers,
            'local_servers': num_local_servers
        }

        response.add("", ret_dict)

    def _handle_instance(self, instance, state_count, queue, 
                         err_list, warn_list):
        """ Parse an instance: check for errors, state etc """
        stateStr=instance.getStateStr()
        if stateStr in state_count:
            state_count[stateStr] += 1
        else:
            state_count[stateStr] = 1
        if stateStr == "error":
            err_list.append(instance.getCanonicalName())
        elif stateStr == "warning":
            warn_list.append(instance.getCanonicalName())
        for task in instance.getTasks():
            for cmd in task.getCommands():
                if cmd.getRunning():
                    queue['running'].append(cmd.toJSON())
                else:
                    queue['queue'].append(cmd.toJSON())

    def _traverseInstance(self, instance, state_count, queue, 
                          err_list, warn_list):
        """Recursively traverse the instance tree, depth first search"""
        self._handle_instance(instance, state_count, queue, err_list, warn_list)
        for child_str in instance.getSubValueIterList():
            child_obj = instance.getSubValue([child_str])
            if child_obj is not None:
                if child_obj.getType() == instanceType:
                    self._traverseInstance(child_obj,state_count, queue, 
                                           err_list, warn_list)

    def _getTopology(self, serverState):
        """ Fetches topology information about the network """
        # TODO Caching
        conf = ServerConf()
        topology = Nodes()
        thisNode = getSelfNode(conf)
        thisNode.nodes = conf.getNodes()
        thisNode.workerStates = serverState.getWorkerStates()
        topology.addNode(thisNode)
        for node in thisNode.nodes.nodes.itervalues():
            if not topology.exists(node.getId()):
                #connect to correct node
                clnt = ClientMessage(node.host, node.verified_https_port,
                                     conf=conf, use_verified_https=True)
                #send along the current topology
                rawresp = clnt.networkTopology(topology)
                processedResponse = ProcessedResponse(rawresp)
                topology = processedResponse.getData()
        return topology

