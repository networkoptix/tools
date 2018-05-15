package com.nx.util;

import com.nx.apidoc.ApidocTagParser;

import java.io.*;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Represents a source code file (e.g. cpp) as a list of lines, and allows to
 * load and search (parse) it. Line numbers start with 1.
 */
public class SourceCode
{
    public String getFilename()
    {
        return file.getAbsolutePath();
    }

    public static final class Error
        extends Exception
    {
        private static String makeMessage(File file, int line, String message)
        {
            final String fileLineRef;
            if (file != null)
                fileLineRef = file.getAbsolutePath() + ":" + line;
            else
                fileLineRef = "line " + line;
            return "Error in " + fileLineRef + ": " + message;
        }

        public Error(File file, int line, String message, Throwable cause)
        {
            super(makeMessage(file, line, message), cause);
        }

        public Error(File file, int line, String message)
        {
            super(makeMessage(file, line, message));
        }
    }

    //--------------------------------------------------------------------------

    public SourceCode(File file)
        throws IOException
    {
        this.file = file;
        lines = Utils.readAllLines(file);
        lineBreak = Utils.determineLineBreak(file);
    }

    /**
     * Identify a multiline block of text starting from the specified line and lasting up to and
     * including the line matching lastLineRegex. After the block of lines is identified, the lines
     * are concatenated replacing line breaks with spaces, and the result is matched with
     * groupRegex.
     * @param firstLineRegex Should match the first line of the block, otherwise, null is returned.
     * @param lastLineRegex Defines the last line of the block. The last line can be the first line
     *     if it matches both firstLineRegex and lastLineRegex.
     * @return Matched groups in groupRegex (strings may be enpty but never null), or null if the
     *     first line does not match firstLineRegex.
     * @throw Error if groupRegex is not matched.
     */
    public final String[] matchMultiline(
        final int firstLine,
        Pattern firstLineRegex,
        Pattern groupRegex,
        Pattern lastLineRegex)
        throws Error
    {
        assert firstLine > 0;
        assert firstLine <= lines.size();

        int index = firstLine - 1;
        String text = lines.get(index);
        if (!firstLineRegex.matcher(text).matches())
            return null;

        if (!lastLineRegex.matcher(text).matches())
        {
            ++index;
            while (index < lines.size())
            {
                text = text + " " + lines.get(index);
                if (lastLineRegex.matcher(lines.get(index)).matches())
                    break;
                ++index;
            }
        }

        String[] result = Utils.matchRegex(groupRegex, text);
        if (result == null)
        {
            throw new Error(file, firstLine, "No match for regex: " +
                groupRegex.pattern() + "\n" +
                "Text:\n" +
                text);
        }
        return result;
    }

    /**
     * @return Matched groups, or null If the line does not match lineRegex.
     */
    public final String[] matchLine(int line, Pattern regex)
    {
        assert line > 0;
        assert line <= lines.size();

        return Utils.matchRegex(regex, lines.get(line - 1));
    }

    public final boolean lineMatches(int line, Pattern regex)
    {
        assert line > 0;
        assert line <= lines.size();

        return regex.matcher(lines.get(line - 1)).matches();
    }

    public String getLine(int line)
    {
        assert line > 0;
        assert line <= lines.size();

        return lines.get(line - 1);
    }

    public final List<String> getPreviousLines(int startLine, Pattern startRegex, Pattern endRegex)
    {
        int line = startLine;

        // Look for an end pattern directly above the line.
        if (line == 0 || !lineMatches(line, endRegex))
            return null;

        // Now line points to the line preceding the end line.
        while (line > 0 && !lineMatches(line, startRegex))
            --line;

        if (line == 0) //< Did not find start.
            return null;

        final List<String> matchingLines = new ArrayList<String>(startLine - line + 1);
        for (int i = line; i <= startLine; ++i)
            matchingLines.add(getLine(i));

        return matchingLines;
    }

    public int getLineCount()
    {
        return lines.size();
    }

    public String getLineBreak()
    {
        return lineBreak;
    }

    //------------------------------------------------------------------------------------------------------------------

    protected final File file;
    protected final List<String> lines;
    protected final String lineBreak;


}
