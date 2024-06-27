// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import java.io.File;

/**
 * Base class for method-objects which perform operations using com.nx.apidoc
 * mechanisms.
 */
public abstract class Executor
{
    public boolean verbose = false;
    public Params params;

    /**
     * Execute the task, using the object public fields as arguments - a kind of named arguments
     * design pattern.
     * @return Number of items (e.g. API functions) processed (can be used for tests).
     */
    public abstract int execute()
        throws Exception;

    //---------------------------------------------------------------------------------------------

    /**
     * Print file path to a vms source file, treated as a relative to the vms source directory.
     */
    protected static void printVmsFile(String filename)
    {
        final String relativePath;
        if (filename.charAt(0) == '/')
            relativePath = filename.substring(1); //< Remove leading '/'.
        else
            relativePath = filename;

        System.out.println(new File(relativePath));
    }
}
