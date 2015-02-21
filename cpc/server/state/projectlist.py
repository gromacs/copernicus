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
import re

import threading
import xml.sax
import logging
import os
import shutil

#import cpc.server.project
from cpc.dataflow.task import TaskQueue
import cpc.dataflow.project
from cpc.util.conf.server_conf import ServerConf
import cpc.util.file
import cpc.util

log=logging.getLogger(__name__)

class ProjectListError(cpc.util.CpcError):
    pass


class ProjectListExistsError(ProjectListError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Project '%s' already in project list" % self.name


class ProjectListNotFoundError(ProjectListError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Project '%s' not found in project list" % self.name

class ProjectList(object):
    """Synchronized project list."""

    def __init__(self, conf, cmdQueue):
        self.lock = threading.RLock()
        self.projects = dict()
        self.cmdQueue = cmdQueue
        # the shared task queue.
        self.taskQueue = TaskQueue(cmdQueue)
        self.conf = conf

    def get(self, name):
        """get a project by its name"""
        with self.lock:
            try:
                return self.projects[name]
            except KeyError:
                raise ProjectListNotFoundError(name)

    def add(self, name):
        """add a project with a specific name"""
        with self.lock:
            if name in self.projects:
                raise ProjectListExistsError(name)
            dirname = os.path.join(self.conf.getRunDir(), name)
            try:
                os.makedirs(dirname)
            except OSError as e:
                raise ProjectListError("Error creating project directory: %s" %
                                       str(e))
            project = cpc.dataflow.project.Project(name, dirname, self.conf,
                self.taskQueue, self.cmdQueue)
            self.projects[name] = project

    def getTaskQueue(self):
        return self.taskQueue

    def getCmdQueue(self):
        return self.cmdQueue

    def list(self):
        """Return a list of project IDs"""
        ret = []
        with self.lock:
            for project in self.projects.itervalues():
                ret.append(project.getName())
        return ret

    def delete(self, project, delDir=False):
        """Delete a project."""
        dirname = None
        with self.lock:
            project.cancel()
            del self.projects[project.getName()]
            dirname = project.getBasedir()
        if delDir and (dirname is not None):
            shutil.rmtree(dirname)

    def _writeState(self, filename):
        """Write the project list out."""
        cpc.util.file.backupFile(filename)
        outf = open(filename, "w")
        outf.write(u'<?xml version="1.0"?>\n')
        outf.write(u'<project-list>\n')
        for proj in self.projects.itervalues():
            name = proj.getName()
            outf.write(u'<project id="%s" dir="%s"/>\n' % (name,
                                                           proj.getBasedir()))
        outf.write(u'</project-list>\n')
        outf.close()

    def writeState(self, filename):
        """Write the project list out."""
        with self.lock:
            self._writeState(filename)

    def writeFullState(self, projectListFilename):
        """Write out each project's state."""
        with self.lock:
            self._writeState(projectListFilename)
            for proj in self.projects.itervalues():
                proj.writeState()

    #def writeProjectTasks(self, serverState):
    #    with self.lock:
    #        for prj in self.projects.itervalues():
    #            try:
    #                prj.writeTasks()
    #            except EnvironmentError as e:
    #                fn=""
    #                if e.filename is not None:
    #                    fn=e.filename
    #                log.error("Error writing tasks for project %s: %s %s"%
    #                          (prj.getName(), e.strerror, fn))
    #                prj.setState(cpc.server.project.Project.error)
    #                serverState.queue.deleteByProject(prj)

    def readState(self, serverState, filename):
        """Read the full state of the project list by reading the project.xml
           file and the individual tasks files."""
        # first read project list
        write = False
        try:
            rd = ProjectListReader(self, serverState)
            rd.read(filename)
            log.debug("Read project list from %s:" % filename)
        except IOError as e:
            log.info("Can't read project list from %s: %s" % (filename, str(e)))
        except xml.sax._exceptions.SAXParseException:
            log.debug("project list xml error (%s):" % filename)
        for prj in rd.getProjects():
            self.projects[prj.getName()] = prj
            prj.readState()

    #reads in the project state of a project state that has been restored from backup
    def readProjectState(self, projectName):
        prj = self.projects[projectName]

        conf = ServerConf()
        projectBaseDir= "%s/%s"%(conf.getRunDir(),projectName)


        #We have a couple of hardcoded paths that might not be valid anymore
        # Think of the case when we are moving projects to another server
        # here we replace those old paths with new valid paths

        stateBakXML = "%s/%s"%(projectBaseDir,"_state.bak.xml")
        #/get the state_bak.xml
        file = open(stateBakXML, 'r')
        content = file.read()
        file.close()

        #find first occurence of <env ..... base_dir=<BASE_DIR>
        m = re.search('<env .* base_dir="(.*)".*>', content)
        if m != None:  #only if we have a project with active tasks
            oldBaseDir= m.group(1)

            new_content = re.sub(oldBaseDir, projectBaseDir, content)

            file = open(stateBakXML,"w")
            file.write(new_content)
            file.close()

        #reread project state
        prj.readState(stateFile="_state.bak.xml")

class ProjectListReaderError(cpc.util.CpcXMLError):
    pass


class ProjectListReader(xml.sax.handler.ContentHandler):
    def __init__(self, projectList, serverState):
        self.projectList = projectList
        self.serverState = serverState
        self.projects = []


    def getProjects(self):
        return self.projects

    def read(self, filename):
        self.filename = filename
        prs = xml.sax.make_parser()
        prs.setContentHandler(self)
        inf = open(filename, 'r')
        prs.parse(inf)
        inf.close()

    def setDocumentLocator(self, locator):
        self.loc = locator

    def startElement(self, name, attrs):
        if name == "project-list":
            pass
        elif name == "project":
            if not attrs.has_key("id"):
                raise ProjectListReaderError("No id in project", self.loc)
            if not attrs.has_key("dir"):
                raise ProjectListReaderError("No dir in project", self.loc)
            id = attrs.getValue("id")
            basedir = attrs.getValue("dir")
            isDefault = cpc.util.getBooleanAttribute(attrs, "default")
            if isDefault:
                log.debug("setting %s to default project" % id)
                self.default = id
            p = cpc.dataflow.project.Project(id, basedir,
                self.projectList.conf,
                self.projectList.getTaskQueue(),
                self.projectList.getCmdQueue())
            self.projects.append(p)

    def endElement(self, name):
        pass

