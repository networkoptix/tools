// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.utils;

import java.io.File;
import java.util.Arrays;

/**
 * Simple unit test framework. Just inherit and write a constructor:
 * <pre>
    public Tests(args)
    {
        this.args = args;

        run("myTest", new Run() { public void run() throws Exception {
            myTest(); } });

        printFinalMessage();
    }
 * </pre>
 */
public abstract class TestBase
{
    protected interface Run
    {
        void run() throws Exception;
    }

    private void print()
    {
        System.out.println();
    }

    private void print(String message)
    {
        System.out.println("[TEST] " + message);
    }

    protected void run(String testName, Run runnable)
    {
        print();
        print("Running test: " + testName);
        try
        {
            runnable.run();
            print("Test PASSED");
        }
        catch (Throwable e)
        {
            ++failedTestsCount;
            System.err.println("\n[TEST] Test " + testName + " FAILED:");
            e.printStackTrace();
        }
    }

    protected final void printFinalMessage()
    {
        System.out.println();
        if (failedTestsCount == 0)
        {
            print("All tests PASSED");
        }
        else
        {
            print("ATTENTION: " +
                (failedTestsCount == 1 ?
                "1 test" : failedTestsCount + " tests") + " FAILED");
            System.exit(3);
        }
    }

    public static void assertEquals(String expected, String actual)
    {
        if (!expected.equals(actual))
        {
            throw new RuntimeException("Expected [" + expected
                + "] but got [" + actual + "]");
        }
    }

    /**
     * @throws RuntimeException If the result is negative.
     */
    public static final void assertFileContentsEqual(File file1, File file2)
        throws Exception
    {
        if (!Arrays.equals(
            Utils.readAllBytes(file1),
            Utils.readAllBytes(file2)))
        {
            throw new RuntimeException("File contents is not equal:\n" +
                file1.getAbsolutePath() + "\n" +
                file2.getAbsolutePath());
        }
    }

    //---------------------------------------------------------------------------------------------

    private int failedTestsCount = 0;
}
