// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.SourceCode;

/**
 * Parses SourceCode to find a registration line (like "reg()") of an API function, and then
 * returns data captured from this registration line.
 */
public interface RegistrationMatcher
{
    /**
     * @return Null if the line is not a registration line.
     */
    RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
        throws SourceCode.Error;
}
