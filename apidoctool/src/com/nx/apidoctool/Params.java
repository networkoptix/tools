package com.nx.apidoctool;

import com.nx.util.ParamsBase;

/**
 * Parameters that allow apidoctool to find necessary places in C++ code: file names, etc.
 */
public class Params
    extends ParamsBase
{
    public String ec2RegistrationCpp() { return ec2RegistrationCpp.toString(); }
    private final StringBuilder ec2RegistrationCpp = regStringParam("ec2RegistrationCpp",
        "/appserver2/src/connection_factory.cpp",
        "A cpp file where /ec2 methods are registered.");
}
