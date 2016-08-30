package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.util.SourceCodeEditor;
import com.nx.util.Utils;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Injects Apidoc comments to SourceCode from Apidoc structure using
 * ApidocCommentGenerator and ApidocHandler.
 */
public final class SourceCodeGenerator
{
    public SourceCodeGenerator(SourceCodeEditor editor)
    {
        this.editor = editor;
    }

    public SourceCodeEditor getEditor()
    {
        return editor;
    }

    /**
     * Generate C++ comments for those functions from the specified group which
     * can be found in C++ comments. Processed functions are removed from the
     * specified group.
     * @return Number of API functions processed.
     */
    public int insertCommentsForSystemApi(Apidoc.Group group)
        throws Error, SourceCodeEditor.Error, ApidocCommentParser.Error
    {
        Set<Apidoc.Function> processedFunctions =
            new HashSet<Apidoc.Function>();

        int line = 1;
        while (line < editor.getLineCount())
        {
            MatchForRegisterHandler match = MatchForRegisterHandler.create(
                editor, line);
            if (match != null)
            {
                Apidoc.Function f = ApidocHandler.findFunction(group,
                    match.functionName);
                if (f != null)
                {
                    addProcessedFunction(processedFunctions, line, f);

                    line += insertComment(line, match.indent,
                        ApidocCommentGenerator.makeMainCommentFrom(
                            f, group, match.indent));

                    group.functions.remove(f);
                }
            }

            ++line;
        }

        logUnprocessedFunctions(processedFunctions, group);

        return processedFunctions.size();
    }

    //--------------------------------------------------------------------------

    /**
     * Insert the given comment to the code, moving existing "//" comments
     * preceding the main line (if any) to the end of the given comment in form
     * of the "%//" tag. Also insert a blank line before the comment if there
     * was no blank line there.
     * @return Number of lines inserted.
     */
    private int insertComment(
        final int mainLine, int indent, List<String> comment)
    {
        // Insert before the last comment line which contains "*/".
        assert comment.size() >= 1;
        final int commentIndexToInsert = comment.size() - 1;

        int line = mainLine - 1;
        while (line >= 1)
        {
            String[] values = editor.matchLine(line, existingCommentRegex);
            if (values == null)
                break;
            assert(values.length == 1);

            editor.deleteLine(line);
            --line; //< Point to the line preceding the deleted "//" line.

            final String textToInsert = Utils.stringOfSpaces(indent) +
                ApidocCommentGenerator.makePrivateTagLine(values[0].trim());

            comment.add(commentIndexToInsert, textToInsert);
        }

        // line points to the line preceding the main line.
        ++line; //< line points to the main line.

        // Insert blank line before the main line if needed.
        if (line > 1 && !editor.getLine(line - 1).trim().isEmpty())
            line += editor.insertLine(line, "");

        line += editor.insertLines(line, comment);
        // line points to the main line.

        return line - mainLine;
    }

    private void addProcessedFunction(
        Set<Apidoc.Function> processedFunctions, int line, Apidoc.Function f)
        throws Error
    {
        if (!processedFunctions.add(f))
        {
            throw new Error("Function " + f.name +
                " is registered in the source code again in line " +
                line + ".");
        }
    }

    private void logUnprocessedFunctions(
        Set<Apidoc.Function> processedFunctions, Apidoc.Group group)
    {
        if (processedFunctions.size() == group.functions.size())
            return;

        System.out.println(
            "WARNING: The following functions are present in API XML but\n" +
                "not registered in the source code:");

        for (Apidoc.Function function: group.functions)
        {
            if (!processedFunctions.contains(function))
                System.out.println("    " + function.name);
        }
    }

    //--------------------------------------------------------------------------

    private static final Pattern existingCommentRegex = Pattern.compile(
        "\\s*//(.*)");

    //--------------------------------------------------------------------------

    private SourceCodeEditor editor;
}
