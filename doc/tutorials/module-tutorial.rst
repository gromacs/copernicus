.. _moduletutorial:

***************
Module Tutorial
***************

This tutorial will walk through the steps required to create a simple copernicus module

Tutorial files can be found `here <https://github.com/gromacs/copernicus/tree/master/examples/module_tutorial_files>`_

The components of a module
^^^^^^^^^^^^^^^^^^^^^^^^^^

The components you need to create a copernicus module is

- An xml definition describing the inputs and outputs of the module.
- A run method that contains the logic of the module.
- A plugin for the executable that runs on the worker.


Defining the xml and the run method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We will create a module that takes integer and doubles their values

We first create a directory under cpc/lib that will hold these two files.

Create the directory cpc/lib/double

Create a file named _import.xml in this directory. The import xml is a shell that describes the input and output values
and their types.


.. code-block:: xml

    <?xml version="1.0"?>
    <cpc>
        <!--
         A simple copernicus function that takes in an array of integers and doubles
         their values.
        -->

        <!--Inputs and outputs of our function will be Integer arrays
        Here we define the a type called int_array, and we specify that the
        member-type(contents) of the array should be ints
        -->
        <type id="int_array" base="array" member-type="int"/>

        <function id="double_value" type="python-extended">
            <desc></desc>
            <inputs>
                <!--each field has a unique id and a type-->
                <field type="int_array" id="integer_inputs">
                    <desc>Integer inputs</desc>
                </field>
            </inputs>
            <outputs>
                <field type="int_array" id="integer_outputs">
                    <desc>Integer outpus</desc>
                </field>
            </outputs>
            <!-- when this function is called it will call the python function
                 defined below. The path is the same as when one imports a module in python
                 we also specify that we want to create a persistent directory for this module
                 we will use this to keep track of states.
                -->
            <controller
                    function="cpc.lib.math.double_script.run"
                    import="cpc.lib.math.double_script"
                    persistent_dir="true"/>
        </function>
    </cpc>

The xml contains comments that describes the different tags; type and function.
There are 5 basic types; int, float, file, array, string. For our module we only want to have arrays of integers as inputs
and outputs so we have created a custom type called int_array. You see that it's base type is defined as array and it's
member-type is defined as int.

The function tag describes the input and output values of the module as well as a controller which links it to the
actual method that will be executed.
The controller contains two attributes

1. function, which points to the method that will be executed
2. import, which is the python file that contains the method

The function attribute is set to cpc.lib.double.run. notice the the method in run.py is also called run
the import attribute is set to cpc.lib.double as it the python package holding the method.
functions and imports are defined the same way as you import packages and files in python.

Now create a file name run.py under the same directory. It will contain the logic that will be executed once input
values are added or updated.
In this method we can:

- Create commands to send to workers
- Define logic for what happens when inputs are set or updated
- Create new module instances


.. code-block:: python

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

        # only one command is finished per call
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
        commandName = "demo/double"

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




the run method does three things. First it grabs the input value, it uses this input value to create a command that will
be put on the copernicus queue and sent to a worker. Lastly it handles the returned data from the worker and sets
it to the output.

Defining the worker plugin
^^^^^^^^^^^^^^^^^^^^^^^^^^

We will also need to create a plugin which is what the worker runs
The plugin is just an xml which defines a list of executables that this plugin can run.
An executable can be anything that can be run on the command line.

There are two ways two create the xml. You can either define a static one named executable.xml or a dynamic using a python script
both have the same output and should be located in cpc/plugins/executables.

create a folder called double under cpc/plugins/executables.
And add the executables.xml file under it.

.. code-block:: xml

    <?xml version="1.0"?>
    <executable-list>

        <!--the executable has a name which it matches to the command name on the queue, an executable might have support for -->
        <!--different types of platforms, for example smp or mpi. A version of the executable can be defined. This can be used -->
        <!--when creating a command to specify the minimum version required-->
        <executable name="math/double" platform="smp" arch="" version="1.0">
            <!--the command that the executable will call is defined here. you can define a command, script -->
            <!--or a program in the same way that you call it on the command line-->
            <run in_path="yes" cmdline="double.py"/>
        </executable>
    </executable-list>


this xml calls the command double which is a python script that we have created.
to make this runnable by a worker,
either change the cmdline attribute to specifiy the absolute path to where the script is located, or add the path to your
PATH environment variable.


We know have everything ready for our first module!
Start up the copernicus server.
To see if the module has loaded properly call cpcc list-modules. You should see a module name double.

Now you can create a project and start using the module. this premade script will create an instance of the module
and start adding values.


