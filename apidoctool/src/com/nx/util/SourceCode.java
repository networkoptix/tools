package com.nx.util;

import java.io.*;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Represents a source code file (e.g. cpp) as a list of lines, and allows to
 * load and search (parse) it. Line numbers start with 1.
 */
public class SourceCode
{
    public static final class Error
        extends Exception
    {
        private static String makeMessage(File file, int line, String message)
        {
            String fileRef = "";
            if (file != null)
                fileRef = " file " + file.getAbsolutePath() + ",";

            return "Error in" + fileRef + " line " + line + ": " + message;
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
     * Try to match the line with the specified regexes as follows: first test
     * whether the line matches lineRegex (if not - return null); then, if the
     * the line does not match lineTerminationRegex, concatenate (replacing line
     * breaks with spaces) the line with the following consecutive lines up to
     * (and including) a line which does not match lineTerminationRegex, and try
     * to match the concatenated text with groupRegex (no match - throw Error),
     * extracting group values.
     * @throw Error if groupRegex is not matched.
     * @return Matched groups, or null If the text does not match lineRegex.
     */
    public final String[] matchLine(
        final int line, Pattern lineRegex, Pattern groupRegex,
        Pattern lineTerminationRegex) throws Error
    {
        assert line > 0;
        assert line <= lines.size();

        int index = line - 1;
        String text = lines.get(index);
        if (!lineRegex.matcher(text).matches())
            return null;

        if (!lineTerminationRegex.matcher(text).matches())
        {
            ++index;
            while (index < lines.size())
            {
                text = text + " " + lines.get(index);
                if (lineTerminationRegex.matcher(lines.get(index)).matches())
                    break;
                ++index;
            }
        }

        String[] result = Utils.matchRegex(groupRegex, text);
        if (result == null)
        {
            throw new Error(file, line, "No match for regex: " +
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

    public int getLineCount()
    {
        return lines.size();
    }

    public String getLineBreak()
    {
        return lineBreak;
    }

    public int getLineIndent(int line)
    {
        assert line > 0;
        assert line <= lines.size();

        final String s = lines.get(line - 1);
        int indent = 0;
        while (indent < s.length() && s.charAt(indent) == ' ')
            ++indent;

        return indent;
    }

    //--------------------------------------------------------------------------

    protected final File file;
    protected final List<String> lines;
    protected final String lineBreak;
}
