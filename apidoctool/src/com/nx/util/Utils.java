package com.nx.util;

import java.io.*;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Generic low-level utils, not using any other project classes.
 */
public final class Utils
{
    private Utils() {}

    public static String toCamelCase(String s)
    {
        final StringBuilder sb = new StringBuilder();
        boolean first = true;
        for (String segment: s.split("_"))
        {
            if (first)
            {
                sb.append(segment.toLowerCase());
                first = false;
            }
            else
            {
                sb.append(segment.charAt(0));
                sb.append(segment.substring(1).toLowerCase());
            }
        }
        return sb.toString();
    }

    public static List<File> getHeaderFileList(File rootPath, String fileList)
        throws Exception
    {
        final List<File> headers = new ArrayList<File>();
        final String[] tokens = fileList.split(",");
        for (String token: tokens)
        {
            final File file = new File(rootPath, token.trim());
            if (!file.exists())
                throw new Exception("File not exists: " + file);

            if (file.isDirectory())
            {
                final File[] directoryListing = file.listFiles();
                for (File entry: directoryListing)
                {
                    if (entry.isFile() && entry.getName().endsWith(".h"))
                        headers.add(entry);
                }
            }
            if (file.isFile() && file.getName().endsWith(".h"))
                headers.add(file);
        }
        return headers;
    }

    public static int substringCount(String str, String substring)
    {
        return str.length() - str.replace(substring, "").length();
    }

    public static String removeCppNamespaces(String str)
    {
        String[] namespaces = str.split("::");
        return  namespaces[namespaces.length - 1];
    }

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

    public static String trimRight(String value)
    {
        int length = value.length();
        while (length > 0 && value.charAt(length - 1) == ' ')
            --length;
        return (length == value.length()) ? value : value.substring(0, length);
    }

    public static String cleanupDescription(String description) throws Exception
    {
        if (description == null)
            return "";
        String result = description.trim();
        while (true)
        {
            final int beginCdata = result.indexOf("<![CDATA[", 0);
            if (beginCdata == -1)
                break;
            final int endCdata = result.indexOf("]]>", beginCdata + "<![CDATA[".length());
            if (endCdata == -1)
            {
                throw new Exception(
                    "Unterminated CDATA section in description:\n```\n" + description + "\n```\n");
            }
            final int beginPre = result.indexOf("<pre>", 0);
            final int endPre = result.indexOf("</pre>", endCdata + "]]>".length());
            if (beginPre == -1 || beginPre > beginCdata || endPre == -1)
            {
                throw new Exception(
                    "Found CDATA not inside <pre></pre> element in description:\n```\n"
                        + description + "\n```\n");
            }
            result = result.substring(0, beginCdata)
                + result.substring(beginCdata + "<![CDATA[".length(), endCdata)
                + result.substring(endCdata + "]]>".length());
        }
        return result;
    }

    /**
     * @return Matched groups (strings may be empty but never null), or null if the line does not
     * match lineRegex.
     */
    public static String[] matchRegex(Pattern pattern, String text)
    {
        final Matcher matcher = pattern.matcher(text);
        if (!matcher.matches())
            return null;

        String[] groups = new String[matcher.groupCount()];

        for (int i = 0; i < groups.length; ++i)
        {
            groups[i] = matcher.group(i + 1);
            if (groups[i] == null)
                groups[i] = "";
        }

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

    /**
     * Overrites the specified file if it exists. Creates dirs in the path if they do not exist.
     */
    public static void writeStringListToFile(File file, List<String> lines, String lineBreak)
        throws IOException
    {
        file.getParentFile().mkdirs();
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

    public static void writeStringToFile(File file, String s)
        throws IOException
    {
        if (s == null)
        {
            throw new IllegalStateException("INTERNAL ERROR: " +
                "null string found");
        }
        FileWriter writer = new FileWriter(file);
        try
        {
            writer.write(s);
        }
        finally
        {
            writer.close();
        }
    }

    /**
     * Insert the specified suffix before the file extension (if any).
     */
    public static File insertSuffix(File file, String suffix)
    {
        final String[] pathAndExtension = matchRegex(pathAndExtensionPattern, file.getPath());

        if (pathAndExtension == null) //< The file has no extension.
            return new File(file + suffix);

        return new File(pathAndExtension[0] + suffix + pathAndExtension[1]);
    }

    /**
     * Change (or add, if there was none) the extension.
     * @param newExtension Should include leading dot.
     */
    public static File replaceExtension(File file, String newExtension)
    {
        final String[] pathAndExtension = matchRegex(pathAndExtensionPattern, file.getPath());

        if (pathAndExtension == null) //< The file has no extension.
            return new File(file + newExtension);

        return new File(pathAndExtension[0] + newExtension);
    }

    public static <T> T createObject(Class<T> objClass)
    {
        try
        {
            return objClass.newInstance();
        }
        catch (InstantiationException e)
        {
            throw new IllegalStateException(e);
        }
        catch (IllegalAccessException e)
        {
            throw new IllegalStateException(e);
        }
    }

    //---------------------------------------------------------------------------------------------

    private static final Pattern pathAndExtensionPattern = Pattern.compile(
        "(.*)(\\.[^./\\\\]+)");
}
