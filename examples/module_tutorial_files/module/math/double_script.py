import cpc
from cpc.dataflow import IntValue, Resources

__author__ = 'iman'

import logging


log=logging.getLogger(__name__)

#our run functions
#the incoming value is of type cpc.dataflow.run.FunctionRunInput
def run(inp):
    if inp.testing():
        ''' When an instance of a function is first created a test call is performed
        here you can test to see if certain prerequisites are met.
         for example if this function is ran on the server only it might need to access some binaries'''
        return

    fo = inp.getFunctionOutput()
    #get hold of the inputs
    # the name that is provided must match the id of the input in the xml file
    #find what changed or was added in the array
    val = inp.getInputValue('integer_inputs')
    updatedIndices = [ i for i,val in enumerate(val.value) if val.isUpdated()]

    log.debug(updatedIndices)

    # only one command is finished per call, we have to check for finished commands first
    if inp.cmd:
        runResultLogic(inp,updatedIndices[0])
        return

    #run some login on the changes
    for i in updatedIndices:
        #THIS IS WHERE WE SHOULD PUT OUR LOGIC
        runLogic(inp,i)

    return fo


def runLogic(inp,i):

    #Sending a job for a worker to compute
    val = inp.getInputValue('integer_inputs')
    arr = inp.getInput('integer_inputs')
    #1 create command
    storageDir = "%s/%s"%(inp.getPersistentDir(),i)

    #the command name should match the executable name of the plugin
    commandName = "math/double"

    args = [arr[i].get()]

    cmd =cpc.command.Command(storageDir
                             ,commandName
                             ,args)


    #2 define how many cores we want for this job
    resources = Resources()
    resources.min.set('cores',1)
    resources.max.set('cores',1)
    resources.updateCmd(cmd)


    #2 add the command to the function output --> will be added to the queue
    fo = inp.getFunctionOutput()
    fo.addCommand(cmd)



def runResultLogic(inp,index):

    #in this case we are getting the result directly from stdout
    # stdout = "%s/%s/stdout"%(inp.getBaseDir(),inp.cmd.dir)
    stdout = "%s/stdout"%(inp.cmd.getDir())
    with open(stdout,"r") as f:
        result = int(f.readline().strip())
        log.debug("result is %s"%result)
        fo = inp.getFunctionOutput()
        fo.setOut("integer_outputs[%s]"%index,IntValue(result))

    return fo



