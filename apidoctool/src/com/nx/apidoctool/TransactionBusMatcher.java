// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses the registration for Transaction Bus transactions.
 */
public final class TransactionBusMatcher implements RegistrationMatcher
{
    /**
     * @return Null if the line is not a registration line.
     */
    public RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
        throws SourceCode.Error
    {
        String[] params;

        params = sourceCode.matchLine(
            line, applyLineRegex);
        if (params != null)
        {
            return createMatch(
                /*transactionCode*/ params[0],
                /*transactionName*/ params[1],
                /*dataType*/ params[2]);
        }

        return null;
    }

    //---------------------------------------------------------------------------------------------

    private static RegistrationMatch createMatch(
        String transactionCode,
        String transactionName,
        String dataType)
    {
        assert transactionCode != null;
        assert !transactionCode.isEmpty();
        assert transactionName != null;
        assert !transactionName.isEmpty();
        assert dataType != null;

        return new RegistrationMatch(
            transactionName + " #" + transactionCode,
            dataType,
            /*outputDataType*/ "",
            /*method*/ "TRACE"); //< TRACE is used for Transactions just as a stub for the method.
    }

    //---------------------------------------------------------------------------------------------

    private static final Pattern applyLineRegex = Pattern.compile(
        "\\s*APPLY\\(\\s*" +
        /*transactionCode*/ "([0-9]+)" +
        "\\s*,\\s*" +
        /*transactionName*/ "(\\w+)" +
        "\\s*,\\s*" +
        /*dataType*/ "([a-zA-Z_0-9:]+)" +
        ".*");
}
