package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.ArrayList;
import java.util.List;

/**
 * Generator of Apidoc Comments from Apidoc structure elements from XML.
 */
public final class ApidocCommentGenerator
    extends ApidocComment
{
    private ApidocCommentGenerator() {}

    public static String makeCommentedOutTagLine(String commentText)
    {
        return " * " + TAG_COMMENTED_OUT + " " + commentText;
    }

    public static List<String> makeMainCommentFrom(Apidoc.Function function,
        Apidoc.Group group, int indent)
    {
        List<String> lines = new ArrayList<String>();

        StringBuilder b = new StringBuilder();
        b.append(COMMENT_START);
        if (function.proprietary)
            b.append(ATTR_PROPRIETARY);
        if (!function.method.isEmpty())
            b.append(" ").append(function.method);
        b.append(" ");
        if (!group.urlPrefix.isEmpty())
            b.append(group.urlPrefix).append("/");
        b.append(function.name);
        lines.add(b.toString());

        if (!function.description.isEmpty())
            addTextToComment(lines, 0, 0, function.description);

        if (!function.caption.isEmpty())
            addTextToComment(lines, 0, INNER_INDENT, TAG_CAPTION + " " + function.caption);

        if (!function.permissions.isEmpty())
            addTextToComment(lines, 0, INNER_INDENT, TAG_PERMISSIONS + " " + function.permissions);

        addParamsToComment(lines, function);

        addResultToComment(lines, function.result);

        lines.add(COMMENT_END);

        Utils.indentStrings(lines, indent);

        return lines;
    }

    //--------------------------------------------------------------------------

    private static void addParamsToComment(
        List<String> lines, Apidoc.Function function)
    {
        for (Apidoc.Param param: function.params)
        {
            if (PARAM_FORMAT.equals(param.name) &&
                DEFAULT_FORMAT_DESCRIPTION.equals(param.description))
            {
                lines.add(COMMENT_PREFIX + TAG_PARAM + ATTR_DEFAULT + " " +
                    PARAM_FORMAT);
            }
            else
            {
                final String attribute;
                if (param.proprietary)
                    attribute = ATTR_PROPRIETARY;
                else if (param.optional)
                    attribute = ATTR_OPT;
                else
                    attribute = "";

                addTextToComment(lines, 0, INNER_INDENT,
                    TAG_PARAM + attribute + " " +
                    param.name + " " + param.description);

                for (Apidoc.Value value: param.values)
                {
                    addTextToComment(lines, INNER_INDENT, INNER_INDENT,
                        TAG_VALUE + " " + value.name + " " +
                        value.description);
                }
            }
        }
    }

    private static void addResultToComment(
        List<String> lines, Apidoc.Result result)
    {
        if (!result.caption.isEmpty())
        {
            addTextToComment(lines, 0, INNER_INDENT,
                TAG_RETURN + " " + result.caption);
        }

        for (Apidoc.Param param: result.params)
        {
            // NOTE: Attributes are not supported for Result.Param.

            addTextToComment(lines, INNER_INDENT, INNER_INDENT,
                TAG_PARAM + " " + param.name + " " + param.description);

            for (Apidoc.Value value: param.values)
            {
                addTextToComment(lines, 2 * INNER_INDENT, INNER_INDENT,
                    TAG_VALUE + " " + value.name + " " +
                        value.description);
            }
        }
    }

    /**
     * Add possibly multiline text to the comment.
     * @param innerIndent Additional indent after initial "*".
     * @param newLineIndent Additional indent for each non-first line.
     */
    private static void addTextToComment(
        List<String> result, int innerIndent, int newLineIndent, String text)
    {
        final String[] lines = text.split("\n");

        String newLineIndentStr = "";
        for (String line: lines)
        {
            result.add(COMMENT_PREFIX + Utils.stringOfSpaces(innerIndent) +
                newLineIndentStr + line.trim());

            if (newLineIndentStr.isEmpty())
                newLineIndentStr = Utils.stringOfSpaces(newLineIndent);
        }
    }

    //--------------------------------------------------------------------------

    private static final String COMMENT_START = "/**" + TAG_APIDOC;
    private static final String COMMENT_END = " */";
    private static final String COMMENT_PREFIX = " * ";
    private static final int INNER_INDENT = 4;
}
