'''
Created on Aug 16, 2011

@author: iman
'''

#A messaging system intended to be used for communication between copernicus servers
#class Message(object):
#    
#    #Send a asynchronous message 
#    #@input request:ServerRequest    
#    def send(self,request,endNode,endNodePort):        
#        pass
#    
#    #Send a synchronous message
#    #@param request:ServerRequest
#    #@param endNode:String
#    #@param endNodePort:int
#    #@return response:ClientResponse
#    def call(self,request,endNode,endNodePort):
#        
#        serverToServerMessage = ServerToServerMessage(endNode,endNodePort)
#        serverToServerMessage.connect()
#        return serverToServerMessage.putRequest(request)
#    
#    #returns the connected nodes in priority order
#    #@return nodes:Nodes
#    def getNeighborNodes(self):
#        conf = ServerConf()
#        nodes = conf.getNodes()
#        return nodes.getNodesByPriority()
#    
