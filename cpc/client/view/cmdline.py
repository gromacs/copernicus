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


'''
Created on Mar 18, 2011

@author: iman
'''

import textwrap
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



class CmdLine(object):
    '''
    classdocs
    '''

    @staticmethod
    def listProject(messageStr):
        projectDict = messageStr['message']               
        co=StringIO()
        co.write("Projects:\n")
        for project in projectDict:            
            co.write("project %s (%s):\n"%(project['id'], project['state']))
            reports=project['reports']
            for report in reports:
                co.write("  report %s (%s)\n"%(report['id'], report['state']))
                tasks=report['tasks']
                for task in tasks:                        
                    co.write("    %s (%s)\n"%(task['id'], task['state']))
        return co.getvalue()

    @staticmethod
    def listQueue(messageStr):
        queueList = messageStr['message']     
        co=StringIO()
        co.write("Queue:\n")
        for cmd in queueList:                
            co.write("%3d %s: %s\n"%(cmd['priority'], cmd['taskID'], 
                                     cmd['executable']))
        return co.getvalue()

    @staticmethod
    def listRunning(messageStr):
        queueList = messageStr['message']
        co=StringIO()
        co.write("Running:\n")
        for cmd in queueList:                
            co.write("task %s\n\tcmd id %s\n\t%s\n"%\
                     (cmd['taskID'], cmd['id'], cmd['executable'] ))
        return co.getvalue()

    @staticmethod
    def listHeartbeats(messageStr):
        list=messageStr['message']
        co=StringIO()
        co.write("Heartbeat items:\n")
        for worker in list['workers']:
            co.write("Worker id=%s\n"%worker['worker_id'])
            for item in worker['items']:
                if item['data_accessible']:
                    accessible="accessible"
                else:
                    accessible="not accessible"
                co.write("    Command id=%s\n"%(item['cmd_id']))
                co.write("\tserver=%s, data %s\n"%(item['server_name'], 
                                                   accessible))
        return co.getvalue()

    @staticmethod
    def listProjects(messageStr):
        list=messageStr['message']
        co=StringIO()
        co.write("Projects:\n")
        for prj in list:
            co.write('  %s\n'%prj)
        return co.getvalue()

    @staticmethod
    def countValues(val):
        """Count the minimum number of characters of a value description."""
        if isinstance(val, list):
            ret=len(val)
            for i in val:
                ret+=CmdLine.countValues(i)+6
        elif isinstance(val, dict):
            ret=len(val)
            for i in val.itervalues():
                ret+=CmdLine.countValues(i)+6
        else:
            ret=len(val)
        return ret

    maxlen=40
    @staticmethod
    def printVal(co, val, indent=0):
        """Print a value description."""
        istr="  "*indent
        iistr="  "*(indent+1)
        if isinstance(val, list):
            cv=CmdLine.countValues(val)
            if cv>CmdLine.maxlen:
                co.write("[\n%s"%(iistr))
            else:
                co.write("[ ")
            first=True
            for v in val:
                if not first:
                    if cv>CmdLine.maxlen:
                        co.write(",\n%s"%iistr)
                    else:
                        co.write(", ")
                CmdLine.printVal(co, v, indent+1)
                first=False
            #co.write(" ]"%istr)
            if cv>CmdLine.maxlen:
                co.write('\n%s]'%(istr))
            else:
                co.write(' ]')
        elif isinstance(val, dict):
            cv=CmdLine.countValues(val)
            if cv>CmdLine.maxlen:
                co.write("{\n%s"%(iistr))
            else:
                co.write("{ ")
            first=True
            for name, v in val.iteritems():
                if not first:
                    if cv>CmdLine.maxlen:
                        co.write(",\n%s"%iistr)
                    else:
                        co.write(", ")
                co.write("%s : "%name)
                CmdLine.printVal(co, v, indent+1)
                first=False
            if cv>CmdLine.maxlen:
                co.write('\n%s}'%(istr))
            else:
                co.write(' }')
        else:
            co.write("%s"%(str(val)))

    @staticmethod
    def getItem(messageStr):
        """Handle output for the 'get' command."""
        list=messageStr['message']
        co=StringIO()
        co.write("%s"%list["name"])
        if "type" in list:
            co.write(" (%s)"%list["type"])
        co.write(": ")
        if "value" in list:
            CmdLine.printVal(co, list["value"], 0)
        else:
            co.write("Not found")
        return co.getvalue()

        

    @staticmethod
    def listActiveItems(messageStr):
        """Handle output for the 'list' command."""
        list=messageStr['message']
        co=StringIO()
        #co.write("List items:\n")
        co.write("%s '%s':\n"%(list['type'], list['name']))
        if 'typename' in list:
            co.write("Type: %s\n"%list['typename'])
        if 'state' in list:
            co.write("State: %s\n"%list['state'])
        if 'subitems' in list:
            co.write('Sub-items:\n')
            for item in list['subitems']:
                if "name" in item:
                    co.write('    %s: %s'% (item["name"], item["type"])) 
                else:
                    co.write('    %s'%(item["type"]))
                if "optional" in item:
                    co.write(", optional")
                if "const" in item:
                    co.write(", const")
                #if "desc" in item:
                #    co.write("\n         %s"%item["desc"])
                co.write('\n')
        if 'inputs' in list:
            co.write('Inputs:\n')
            for item in list['inputs']:
                co.write('    %s\n'%item)
        if 'outputs' in list:
            co.write('Outputs:\n')
            for item in list['outputs']:
                co.write('    %s\n'%item)
        if 'instances' in list:
            if 'state' in list:
                co.write('Subnet function instances:\n')
            else:
                co.write('Network function instances:\n')
            for name, item in list['instances'].iteritems():
                co.write('    %s (%s)\n'%(name, item))
        return co.getvalue()

    @staticmethod
    def writeInfo(messageStr):
        """Handle output for the 'info' command."""
        lst=messageStr['message']
        co=StringIO()
        co.write("%s %s \n"%(lst["type"], lst["name"]))
        tw=textwrap.TextWrapper(initial_indent=" ", subsequent_indent=" ",
                                replace_whitespace=True)
        st=tw.wrap(lst["desc"])
        for line in st:
            co.write("%s\n"%line)
        tw.subsequent_indent="        "
        tw.initial_indent="        "
        if "inputs" in lst:
            co.write(" inputs:\n")
            for item in lst["inputs"]:
                co.write("    %s (%s)\n"%(item["name"], item["type"]))
                st=tw.wrap(item["desc"])
                for line in st:
                    co.write("%s\n"%line)
                #co.write("\n")
        if "outputs" in lst:
            co.write(" outputs:\n")
            for item in lst["outputs"]:
                co.write("    %s (%s)\n"%(item["name"], item["type"]))
                st=tw.wrap(item["desc"])
                for line in st:
                    co.write("%s\n"%line)
                #co.write("\n")
        #co.write("%s"%(type(lst["desc"])))
        if "functions" in lst:
            co.write(" functions:\n")
            for item in lst["functions"]:
                co.write("    %s\n"%(item["name"]))
                st=tw.wrap(item["desc"])
                for line in st:
                    co.write("%s\n"%line)
        if "types" in lst:
            co.write(" types:\n")
            for item in lst["types"]:
                co.write("    %s\n"%(item["name"]))
                st=tw.wrap(item["desc"])
                for line in st:
                    co.write("%s\n"%line)
        return co.getvalue()

    @staticmethod 
    def writeDotInstance(co, name, fname, inputs, outputs):
        co.write('    %s [ shape="record" label="%s | { '%(name, fname))
        last=False
        co.write(' { ')
        if inputs is not None:
            for io in inputs:
                if last:
                    co.write(' | ')
                co.write('<%s_in> %s'%(io, io))
                last=True
        co.write(' } | { ')
        last=False
        if outputs is not None:
            for io in outputs:
                if last:
                    co.write(' | ')
                co.write('<%s_out> %s'%(io, io))
                last=True
        co.write(' } ')
        co.write('}"  ]\n')


    @staticmethod
    def makeDotGraph(messageStr):
        list=messageStr['message']
        co=StringIO()
        co.write('digraph f {\n')
        # first write out instances
        for name, inst in list['instances'].iteritems():
            if name != "self":
                CmdLine.writeDotInstance(co, name, name, inst['inputs'], 
                                 inst['outputs'])
            else:
                CmdLine.writeDotInstance(co, "self_in", list['name'], 
                                         inst['subnet_inputs'], 
                                         inst['inputs']) 
                CmdLine.writeDotInstance(co, "self_out", list['name'],  
                                         inst['outputs'], 
                                         inst['subnet_outputs'] )
        # then write values/connections
        for conn in list['connections']:
            if not (conn[0] == "self" and conn[3] == "self"):
                dst="%s:%s_in"%(conn[3], conn[4])
                dsti="%s_%s_in"%(conn[3], conn[4])
                if conn[3] == "self":
                    dst="self_in:%s_in"%conn[4]
                    dsti="self_in_%s_in"%conn[4]
                if conn[0] == None:
                    tmpinst="%s_%s_val"%(dsti, conn[4])
                    co.write('    %s [ style="invisible" ];\n'%(tmpinst))
                    co.write('    %s -> %s [ label="%s" ];\n'%
                             (tmpinst, dst, conn[6]))
                else:
                    src="%s:%s_out"%(conn[0], conn[1])
                    if conn[0] == "self":
                        src="self_out:%s_out"%(conn[1])
                    co.write('    %s -> %s;\n'%(src,dst))
        co.write('}\n')
        return co.getvalue()

    
    @staticmethod   
    def addNodeRequest(message):
        nodeConnectRequest = message['data']        
        co = StringIO()
        co.write("Node connect request sent to %s:%s "%(nodeConnectRequest.host,nodeConnectRequest.https_port))
        return co.getvalue()
    
    @staticmethod
    def listSentNodeConnectRequests(message):
        nodes = message['data']
        co = StringIO()
        co.write("Sent connection requests to:\n")
        for node in nodes.nodes.itervalues():
            co.write("%s\n"%node.getId())
        
        return co.getvalue()
        
    @staticmethod
    def listNodeConnectRequests(message):
        nodes = message['data']
        co = StringIO()
        co.write("Connection requests received from:\n")
        for node in nodes.nodes.itervalues():
            co.write("%s\n"%node.getId())
        
        return co.getvalue()
    
    @staticmethod
    def listNodes(message):
        nodes = message['data']
        co = StringIO()
        co.write("Connected nodes:\n")              
        for node in nodes:
            co.write("%s %s\n"%(node.priority,node.getId()))
        
        return co.getvalue()
    
    @staticmethod
    def grantAllNodeConnectRequests(message):
        nodes = message['data']
        connected=nodes['connected']
       # notConnected = nodes['notConnected']
        
        co = StringIO()
        co.write("Following nodes are now trusted:\n")
        for node in connected:
            co.write("%s\n"%node)
        
#        if len(notConnected) >0:
#            co.write("Following nodes was not trusted:\n")    
#            for node in notConnected:
#                co.write("%s %s\n"%(node.host,node.https_port))
        return co.getvalue() 
    
    @staticmethod
    def networkTopology(message):
        topology = message['data']
        
        co = StringIO()
        co.write("graph topology{\n")
        for node in topology.nodes.itervalues():                                    
            for neighbour in node.nodes.nodes.itervalues():
                co.write('\"%s\"--\"%s\"\n'%(node.host,neighbour.host)) 
            for worker in node.workerStates.itervalues():                
                co.write('\"%s\" [shape=polygon,sides=5,peripheries=3,color=lightblue,style=filled];\n'%node.host)
                co.write('\"%s\"--\"worker_%s\"\n'%(node.host,worker.host))                    
                #co.write("worker %s status:%s\n"%(worker.host,worker.status))
        
        co.write("}")    
        return co.getvalue()
    @staticmethod     
    def getTopologyGraphString(message):
        str = ''
        topology = message['data']
        str+="graph topology{\n"
        for node in topology.nodes.itervalues():                                    
            for neighbour in node.nodes.nodes.itervalues():
                str+='\"%s\"--\"%s\"\n'%(node.host,neighbour.host) 
            for worker in node.workerStates.itervalues():                
                str+='\"%s\" [shape=polygon,sides=5,peripheries=3,color=lightblue,style=filled];\n'%node.host
                str+='\"%s\"--\"worker_%s\"\n'%(node.host,worker.host)                    
                #co.write("worker %s status:%s\n"%(worker.host,worker.status))
        
        str+="}"    
        return str
       
       
        
