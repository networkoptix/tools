package com.nx.apidoctool;

public final class PrintDepsExecutor
    extends Executor
{
    /**
     * Print paths to all C++ source code files to be accessed, relative to vms-path.
     */
    public int execute()
    {
        printVmsFile(params.templateRegistrationCpp());
        printVmsFile(params.handlerRegistrationCpp());
        return 1;
    }
}
