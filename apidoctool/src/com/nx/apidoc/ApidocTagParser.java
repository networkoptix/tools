package com.nx.apidoc;

import com.nx.util.SourceCode;
import com.nx.util.Utils;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Parses a multiline comment into items started by %-tags. Format of each
 * comment item is as follows:
 * <pre>
 * * %tag:label [attribute] initialToken Possibly-multiline-text
 * </pre>
 * Each of the components, including initial "*", but except the tag, is
 * optional. Note that "%" char is prohibited in a continuation line (because it
 * can be interpreted as a beginning of the next tag).
 */
public final class ApidocTagParser
{
    public static class Error
        extends Exception
    {
        public Error(String filename, int line, String message)
        {
            super(filename + ":" + line + ": " + message);
        }
    }

    public final static class Item
    {
        private final String tag;
        private final String attribute;
        private final String label;
        private final String initialTokenUntrimmed;
        private final List<String> textAfterInitialToken;

        private final boolean verbose;
        private final String filename;
        private final int firstLineOfItem;

        protected Item(
            String tag,
            String attribute,
            String label,
            String initialTokenUntrimmed,
            List<String> textAfterInitialToken,
            String filename,
            int firstLineOfItem,
            boolean verbose)
        {
            assert tag != null;
            assert !tag.isEmpty();
            this.tag = tag;

            assert(attribute != null);
            this.attribute = attribute;

            assert(label != null);
            this.label = label;

            assert(initialTokenUntrimmed != null);
            this.initialTokenUntrimmed = initialTokenUntrimmed;

            assert textAfterInitialToken != null;
            this.textAfterInitialToken = textAfterInitialToken;

            this.verbose = verbose;
            this.filename = filename;
            this.firstLineOfItem = firstLineOfItem;
        }

        /**
         * @return Tag with "%".
         */
        public String getTag()
        {
            return tag;
        }

        /**
         * @return Label or "" if omitted.
         */
        public String getLabel()
        {
            return label;
        }

        /**
         * @return Attribute with brackets, or "" if omitted.
         */
        public String getAttribute()
        {
            return attribute;
        }

        /**
         * @return Initial token, or "" if the initial token is omitted.
         */
        public String getInitialToken()
        {
            return initialTokenUntrimmed.trim();
        }

        /**
         * @return Text following the initial token (if any). Never null.
         */
        public String getTextAfterInitialToken(int indentLevel)
        {
            if (textAfterInitialToken.isEmpty())
                return "";

            final String indentString = Utils.stringOfSpaces(indentLevel * 4);

            StringBuilder b = new StringBuilder(Utils.trimRight(textAfterInitialToken.get(0)));
            for (int line = 1; line < textAfterInitialToken.size(); ++line)
            {
                if (!b.toString().isEmpty()) //< skip empty lines
                    b.append("\n");
                String continuationTrimmed = textAfterInitialToken.get(line);
                if (continuationTrimmed.startsWith(indentString))
                {
                    continuationTrimmed = continuationTrimmed.substring(indentString.length());
                }
                else if (verbose)
                {
                    System.out.println("WARNING: " + filename + ":" + (firstLineOfItem + line)
                            + ": Too small indent.");
                }
                b.append(Utils.trimRight(continuationTrimmed));
            }
            return b.toString();
        }

        /**
         * @return Text including the initial token (if any).
         */
        public String getFullText(int indentLevel)
        {
            final boolean newLineRequired = !initialTokenUntrimmed.trim().isEmpty()
                && textAfterInitialToken.size() > 1
                && textAfterInitialToken.get(0).trim().isEmpty();
            if (newLineRequired)
                return initialTokenUntrimmed + "\n" + getTextAfterInitialToken(indentLevel);
            return initialTokenUntrimmed + getTextAfterInitialToken(indentLevel);

        }

        public  String getErrorPrefix()
        {
            return filename + ":" + firstLineOfItem + ": ";
        }
    }

    public static List<Item> getItems(
        List<String> lines, String filename, int firstLine, boolean verbose)
        throws Error
    {
        final List<Item> items = new ArrayList<Item>();
        final ApidocTagParser parser = new ApidocTagParser(lines, filename, firstLine, verbose);
        Item item = parser.parseNextItem();
        while (item != null)
        {
            items.add(item);
            item = parser.parseNextItem();
        }
        return items;
    }

    // TODO: This method must be renamed, because it is used not only for structs or enums, but
    // also for non-type entities like struct fields and enum items. Also tag checks must be added
    // to the usages of this method: currently, if e.g. "%value" in a struct field apidoc comment
    // is replaced with an arbitrary tag (e.g. "%xxx"), apidoctool works as if it were "%value",
    // instead of producing an "Unexpected tag" error.
    /**
     * @return Null in case no apidoc comment found.
     */
    public static List<Item> getItemsForType(SourceCode sourceCode, int line, boolean verbose)
        throws Error
    {
        final List<String> commentLines;
        final String trailingComment = getTrailingComment(sourceCode, line);
        final List<String> precedingCommentLines = getPrecedingComment(sourceCode, line - 1);

        if (trailingComment == null && precedingCommentLines == null)
            return null;

        if (trailingComment != null && precedingCommentLines != null)
        {
            throw new Error(sourceCode.getFilename(), line,
                "Both trailing and preceding apidoc comments found.");
        }

        final int firstCommentLine;
        if (trailingComment != null)
        {
            firstCommentLine = line;
            commentLines = new ArrayList<String>();
            commentLines.add(trailingComment);
        }
        else
        {
            firstCommentLine = line - precedingCommentLines.size() - 1;
            commentLines = precedingCommentLines;
        }

        if (commentLines.isEmpty())
            return null;

        final List<Item> items = getItems(
            commentLines, sourceCode.getFilename(), firstCommentLine, verbose);
        assert !items.isEmpty();
        assert ApidocComment.TAG_APIDOC.equals(items.get(0).getTag());
        return items;
    }

    private ApidocTagParser(List<String> lines, String filename, int firstLine, boolean verbose)
    {
        this.filename = filename;
        this.firstLine = firstLine;
        this.verbose = verbose;
        this.lines = lines;
        line = 0;
    }

    private Item parseNextItem()
        throws Error
    {
        // Skip empty comment lines: those containing only "/**" or "*".
        while (line < lines.size() &&
            Utils.matchRegex(emptyCommentLineRegex, lines.get(line)) != null)
        {
            ++line;
        }

        if (line >= lines.size())
            return null;

        int firstLineOfItem = firstLine + line;
        String sourceLine = lines.get(line);
        if (sourceLine.endsWith("*/")) //< single line case
            sourceLine = sourceLine.substring(0, sourceLine.length() - 2);

        final String[] values = Utils.matchRegex(itemStartRegex, sourceLine);
        if (values == null)
            throw new Error(filename, firstLine + line, "Invalid tag line in Apidoc comment");

        ++line;
        final List<String> textAfterToken = new ArrayList<String>();
        textAfterToken.add(values[6]);
        while (line < lines.size())
        {
            final String[] continuation = Utils.matchRegex(
                itemContinuationRegex, lines.get(line));
            if (continuation == null)
                break;

            textAfterToken.add(continuation[0]);
            ++line;
        }

        return new Item(
            values[1],
            values[2],
            values[4],
            values[5],
            textAfterToken,
            filename,
            firstLineOfItem,
            verbose);
    }

    private static String getTrailingComment(SourceCode sourceCode, int startLine) throws Error
    {
        String[] values = sourceCode.matchLine(startLine, trailingCommentRegex);
        if (values == null)
            return null;

        if (!"<".equals(values[1]))
        {
            throw new Error(
                sourceCode.getFilename(),
                startLine,
                "Trailing comment should start with \"/**<\".");
        }
        return values[0];
    }

    public static List<String> getPrecedingComment(SourceCode sourceCode, int startLine)
        throws Error
    {
        final List<String> lines = sourceCode.getPreviousLines(
            startLine, commentStartRegex, commentEndRegex);

        if (lines == null)
            return null;

        String[] values = Utils.matchRegex(apidocCommentStartRegex, lines.get(0));
        if (values == null)
            return null;

        if ("<".equals(values[0]))
        {
            throw new Error(
                sourceCode.getFilename(),
                startLine,
                "Preceding comment should not start with \"/**<\"");
        }
        return lines;
    }

    //---------------------------------------------------------------------------------------------

    private final String filename;
    private final boolean verbose;
    private final int firstLine;
    private final List<String> lines;
    private int line;

    //---------------------------------------------------------------------------------------------

    private static final Pattern emptyCommentLineRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?/?\\s*");
      //     /*       *   /

    private static final Pattern itemStartRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?\\*?(<)?\\s*(%[^\\s\\[:]+)\\s*(\\[\\w+\\])?\\s*" +
      //     /*       *               %tag              [attr]
        "(:\\s*((?:[_A-Za-z0-9{}<>:]|, )+))?\\s*([^\\[\\s][^\\s]*\\s*)?(.*)");
      // Label                                 Token                  ...

    private static final Pattern itemContinuationRegex = Pattern.compile(
        "\\s*\\* ([^%]*)");
      //     *   non-%...

    public static final Pattern trailingCommentRegex = Pattern.compile(
        ".+(\\/\\*\\*(<)?\\s*%apidoc.*\\*/)");

    public static final Pattern commentEndRegex = Pattern.compile(
        "\\s*(/\\*\\*.*)?\\*/\\s*");

    public static final Pattern commentStartRegex = Pattern.compile(
        "\\s*/\\*.*");

    public static final Pattern apidocCommentStartRegex = Pattern.compile(
        "\\s*/\\*\\*(<)?\\s*%apidoc.*");
}
