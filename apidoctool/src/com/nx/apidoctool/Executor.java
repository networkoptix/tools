package com.nx.apidoctool;

import java.io.File;

/**
 * Base class for method-objects which perform operations using com.nx.apidoc
 * mechanisms.
 */
public abstract class Executor
{
    public boolean verbose = false;

    /**
     * Execute the task, using the object public fields as arguments - a kind of named arguments
     * design pattern.
     * @return Number of items (e.g. API functions) processed (can be used for tests).
     */
    public abstract int execute()
        throws Exception;

    /**
     * Print paths to all C++ source code files to be accessed, relative to vms-path.
     */
    public static void printDeps()
    {
        printDep(CONNECTION_FACTORY_CPP);
    }

    //---------------------------------------------------------------------------------------------

    /**
     * Generated source code files have the name of the original source code file with this suffix
     * inserted before the extension.
     */
    protected static final String OUTPUT_FILE_EXTRA_SUFFIX = ".OUT";

    protected static final String SYSTEM_API_GROUP_NAME = "System API";

    protected static final String CONNECTION_FACTORY_CPP =
        "/appserver2/src/connection_factory.cpp";

    //---------------------------------------------------------------------------------------------

    private static void printDep(String filename)
    {
        final String relativePath;
        if (filename.charAt(0) == '/')
            relativePath = filename.substring(1); //< Remove leading '/'.
        else
            relativePath = filename;

        System.out.println(new File(relativePath));
    }
}
