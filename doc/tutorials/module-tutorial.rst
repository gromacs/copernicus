.. _moduletutorial:

***************
Module Tutorial
***************

This tutorial will walk through the steps required to create a simple copernicus module

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
        <!--we can define custom types, here we want to have arrays of integers-->
        <type id="int_array" base="array" member-type="int"/>

        <!--the function should have a unique id-->
        <function id="double" type="python-extended">
            <desc>Doubles the input value</desc>

            <!--all input fields are defined in the input tag, you can define as many fields as you like-->
            <inputs>
                <!--each field has a unique id and a type-->
                <field type="int_array" id="digits">
                    <desc>Input values that will be doubled</desc>
                </field>
            </inputs>
            <outputs>
                <field type="int_array" id="double_digits">
                    <desc>The doubled output values</desc>
                </field>
            </outputs>

            <!--the controller defines the module method that will be run-->
            <controller function="cpc.lib.double.run"
                        import="cpc.lib.double"
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

    from cpc.dataflow import IntValue, FloatValue, StringValue
    import cpc.command


    #this method is triggered as soon as an input is set,updated or when a command is finished
    def run(inp):

        #First we check so we have not received a finished command
        if inp.cmd is None:

            #we create a new command and add it to the queue

            #get hold of the input value. the name n_samples matches id attribute of the input field defined in the xml
            n_samples = inp.getInput('n_samples')

            #create a command, we need a persistent directory to save results to later, a unique name (pi/gen_samples)
            #for the command that is used when matching jobs to a worker, and an array of arguments which in this case is
            #the input value that we set
            cmd = Command(cmd = cpc.command.Command(inp.getPersistentDir(), "double",
                                                    [n_samples]))

            #the output is what holds the command
            fo = inp.getFunctionOutput()
            fo.addCommand(cmd)


        else:
            #we have a finished command, lets grab the results and set it to the output
            #results from the worker is persisted in files
            #we grab the files,
            #TODO how do we grab a result?
            #Todo How do we add an integer to the output array?
            fo = inp.getFunctionOutput()
            fo.setOut("double_digits", IntValue(endTime))

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
        <executable name="double" platform="smp" arch="" version="1.0">
            <!--the command that the executable will call is defined here. you can define a command, script -->
            <!--or a program in the same way that you call it on the command line
            $ARGS is the arguments that you have passed along in the command
            -->
            <run in_path="yes" cmdline="double $ARGS" />
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


