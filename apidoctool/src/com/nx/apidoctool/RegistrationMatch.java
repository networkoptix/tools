package com.nx.apidoctool;

public class RegistrationMatch
{
    public final String urlPrefix;

    public final String functionName;

    /**
     * Empty string if no input data structure is defined for this API function.
     */
    public final String inputDataType;

    /**
     * Empty string if no output data structure is defined for this API function.
     */
    public final String outputDataType;

    public final String method;

    public RegistrationMatch(
        String urlPrefix,
        String functionName,
        String inputDataType,
        String outputDataType,
        String method)
    {
        this.urlPrefix = urlPrefix;
        this.functionName = functionName;
        this.inputDataType = inputDataType;
        this.outputDataType = outputDataType;
        this.method = method;
    }
}
