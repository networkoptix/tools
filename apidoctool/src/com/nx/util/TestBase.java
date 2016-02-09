package com.nx.util;

import java.io.File;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Pattern;

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

    protected void run(String testName, Run runnable)
    {
        System.out.println();
        System.out.println("####### Running test: " + testName);
        try
        {
            runnable.run();
            System.out.println("####### Test PASSED");
        }
        catch (Throwable e)
        {
            ++failedTestsCount;
            System.err.println("");
            System.err.println("####### Test " + testName + " FAILED:");
            e.printStackTrace();
        }
    }

    protected void printFinalMessage()
    {
        System.out.println();
        if (failedTestsCount == 0)
        {
            System.out.println("All tests PASSED");
        }
        else
        {
            System.out.println("ATTENTION: " +
                (failedTestsCount == 1 ?
                "1 test" : failedTestsCount + " tests") + " FAILED");
            System.exit(3);
        }
    }

    /**
     * @throws RuntimeException If the result is negative.
     */
    public static void checkFileContentsEqual(File file1, File file2)
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

    /**
     * Check that two text files have equal lines, ignoring possible line break
     * method difference and indentation (possible whitespace at the beginning
     * of each line).
     * @throws RuntimeException If the result is negative.
     */
    public static void checkTextFilesEqualIgnoringIndents(File file1, File file2)
        throws Exception
    {
        List<String> lines1 = Utils.readAllLines(file1);
        List<String> lines2 = Utils.readAllLines(file2);

        if (lines1.size() != lines2.size())
        {
            throw new RuntimeException(
                "Text files have different number of lines:\n" +
                    file1.getAbsolutePath() + "\n" +
                    file2.getAbsolutePath());
        }

        for (int i = 0; i < lines1.size(); ++i)
        {
            final String[] line1Unindented = Utils.matchRegex(
                unindentedLineRegex, lines1.get(i));
            final String[] line2Unindented = Utils.matchRegex(
                unindentedLineRegex, lines2.get(i));

            if (!line1Unindented[0].equals(line2Unindented[0]))
            {
                throw new RuntimeException(
                    "Text files differ at line " + (i + 1) + ":\n" +
                        file1.getAbsolutePath() + "\n" +
                        file2.getAbsolutePath() + "\n" +
                        line1Unindented[0] + "\n" +
                        line2Unindented[0]);
            }
        }
    }

    //--------------------------------------------------------------------------

    private static final Pattern unindentedLineRegex = Pattern.compile(
        "\\s*(.*)");

    private int failedTestsCount = 0;
}
