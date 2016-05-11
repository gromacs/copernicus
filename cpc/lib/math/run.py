from cpc.dataflow import IntValue, FloatValue, StringValue
import cpc.command


# this method is triggered as soon as an input is set,updated or when a command is finished
def run(inp):
    if (inp.testing()):
        return

    # First we check so we have not received a finished command
    if inp.cmd is None:
        # we create a new command and add it to the queue

        # get hold of the input value. the name n_samples matches id attribute of the input field defined in the xml
        val= inp.getInputValue('digits')

        updatedIndices = [i for i,val in enumerate(val.value) if val.isUpdated() ]

        print n_samples
        # create a command, we need a persistent directory to save results to later, a unique name (pi/gen_samples)
        # for the command that is used when matching jobs to a worker, and an array of arguments which in this case is
        # the input value that we set
        cmd = cpc.command.Command(inp.getPersistentDir(), "math/double", [n_samples])  # the output is what holds the command
        fo = inp.getFunctionOutput()
        fo.addCommand(cmd)

    else:
        # we have a finished command, lets grab the results and set it to the output
        # results from the worker is persisted in files
        # we grab the files,
        # TODO how do we grab a result?
        # Todo How do we add an integer to the output array?
        fo = inp.getFunctionOutput()
        # fo.setOut("double_digits", IntValue(endTime))

    return fo
