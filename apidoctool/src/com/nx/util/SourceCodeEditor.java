package com.nx.util;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/**
 * Allows to edit and save modified SourceCode to file.
 */
public final class SourceCodeEditor
    extends SourceCode
{
    public SourceCodeEditor(File file)
        throws IOException
    {
        super(file);
    }

    public void saveToFile(File file)
        throws IOException, Error
    {
        Utils.writeStringListToFile(file, lines, lineBreak);
    }

    /**
     * Insert the given lines before the specified line, breaking each String
     * at inner line breaks (if any).
     * @param beforeLine Can point after the last line.
     * @return Number of lines inserted. May not equal lines.size() due to
     * possible inner line breaks.
     */
    public int insertLines(int beforeLine, List<String> linesToInsert)
    {
        assert beforeLine > 0;
        assert beforeLine <= lines.size() + 1;

        int index = beforeLine - 1;
        int count = 0;
        for (String s: linesToInsert)
        {
            final String[] strings = s.split("\\r?\\n");
            lines.addAll(index, Arrays.asList(strings));
            index += strings.length;
            count += strings.length;
        }
        return count;
    }

    /**
     * Equivalent of insertLines(beforeLine, Arrays.asList(text)).
     * @return Number of lines inserted. May not equal 1 due to possible inner
     * line breaks.
     */
    public int insertLine(int beforeLine, String text)
    {
        return insertLines(beforeLine, Arrays.asList(text));
    }

    public void deleteLine(int line)
    {
        assert line > 0;
        assert line <= lines.size();

        lines.remove(line - 1);
    }

    /**
     * @param line May not contain line breaks.
     */
    public void setLine(int line, String text)
    {
        assert line > 0;
        assert line <= lines.size();
        if (text.contains("\\r") || text.contains("\\n"))
        {
            throw new IllegalStateException("SourceCode.setLine(" +
                line + ", \"" + text + "\"): " +
                "Line breaks are not allowed in text.");
        }

        lines.set(line - 1, text);
    }
}
