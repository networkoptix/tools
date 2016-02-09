package com.nx.apidoctool;

/**
 * Base class for method-objects which perform operations using com.nx.apidoc
 * mechanisms.
 */
public abstract class Executor
{
    /**
     * Execute the task, using the object public fields as arguments - a kind of
     * named arguments design pattern.
     */
    public abstract void execute()
        throws Exception;

    //--------------------------------------------------------------------------

    /**
     * Generated source code files have the name of the original source code
     * file with this suffix inserted before the extension.
     */
    protected static final String OUTPUT_FILE_EXTRA_SUFFIX = ".OUT";

    protected static final String SYSTEM_API_GROUP_NAME = "System API";

    protected static final String CONNECTION_FACTORY_CPP =
        "/appserver2/src/connection_factory.cpp";
}
