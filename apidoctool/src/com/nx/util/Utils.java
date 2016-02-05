package com.nx.util;

import java.io.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Scanner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Generic low-level utils, not using any other project classes.
 */
public final class Utils
{
    private Utils() {}

    public static String stringOfSpaces(int numberOfSpaces)
    {
        char[] chars = new char[numberOfSpaces];
        Arrays.fill(chars, ' ');
        return new String(chars);
    }

    public static String determineLineBreak(File file)
        throws IOException
    {
        // Read the file backwards byte-after-byte.
        RandomAccessFile f = new RandomAccessFile(file, "r");
        long pos = f.length() - 1;
        while (pos >= 0)
        {
            f.seek(pos);
            switch (f.readByte())
            {
                case '\n':
                    if (pos > 0)
                    {
                        f.seek(pos - 1);
                        if (f.readByte() == '\r')
                            return "\r\n";
                    }
                    return "\n";
                case '\r':
                    return "\r";
                default:
                    --pos;
            }
        }

        // Return default value if there is no line breaks in the file.
        return "\n";
    }

    public static void indentStrings(List<String> strings, int indent)
    {
        final String indentString = stringOfSpaces(indent);

        for (int i = 0; i < strings.size(); ++i)
            strings.set(i, indentString + strings.get(i));
    }

    /**
     * @return Matched groups, or null If the line does not match lineRegex.
     */
    public static String[] matchRegex(Pattern pattern, String text)
    {
        final Matcher matcher = pattern.matcher(text);
        if (!matcher.matches())
            return null;

        String[] groups = new String[matcher.groupCount()];

        for (int i = 0; i < groups.length; ++i)
            groups[i] = matcher.group(i + 1);

        return groups;
    }

    public static List<String> readAllLines(File file)
        throws IOException
    {
        List<String> list = new ArrayList<String>();

        BufferedReader br = new BufferedReader(new FileReader(file));
        try
        {
            String line;
            while ((line = br.readLine()) != null)
                list.add(line);
        }
        finally
        {
            br.close();
        }

        return list;
    }

    public static byte[] readAllBytes(File file)
        throws IOException
    {
        byte[] buffer = new byte[(int) file.length()];

        InputStream s = new FileInputStream(file);
        try
        {
            s.read(buffer);
        }
        finally
        {
            s.close();
        }

        return buffer;
    }

    public static void saveStringListToFile(
        File file, List<String> lines, String lineBreak)
        throws IOException
    {
        FileWriter writer = new FileWriter(file);
        try
        {
            for (int i = 0; i < lines.size(); ++i)
            {
                final String s = lines.get(i);
                if (s == null)
                {
                    throw new IllegalStateException("INTERNAL ERROR: " +
                        "null string found in line " + (i + 1) +
                        " of file: " + file);
                }
                writer.write(s);
                writer.write(lineBreak);
            }
        }
        finally
        {
            writer.close();
        }
    }
}
