package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Parses a multiline comment into items started by %-tags. Format of each
 * comment item is as follows:
 * <pre>
 * * %tag [attribute] initialToken Possibly-multiline-text
 * </pre>
 * Each of the components, including initial "*", but except the tag, is
 * optional. Note that "%" char is prohibited in a continuation line (because it
 * can be interpreted as a beginning of the next tag).
 */
public final class ApidocTagParser
{
    public final class Item
    {
        private final String tag;
        private final String attribute;
        private final String initialTokenUntrimmed;
        private final List<String> textAfterInitialToken;

        protected Item(
            String tag,
            String attribute,
            String initialTokenUntrimmed,
            List<String> textAfterInitialToken)
        {
            assert tag != null;
            assert !tag.isEmpty();
            this.tag = tag;

            assert(attribute != null);
            this.attribute = attribute;

            assert(initialTokenUntrimmed != null);
            this.initialTokenUntrimmed = initialTokenUntrimmed;

            assert textAfterInitialToken != null;
            this.textAfterInitialToken = textAfterInitialToken;
        }

        /**
         * @return Tag with "%".
         */
        public String getTag()
        {
            return tag;
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

            String indentString = "";
            for (int i = 0; i < indentLevel * 4; ++i)
                indentString += ' ';

            StringBuilder b = new StringBuilder(textAfterInitialToken.get(0));
            int line = 1;
            while (line < textAfterInitialToken.size())
            {
                if (!b.toString().isEmpty()) //< skip empty lines
                    b.append("\n");
                String continuationTrimmed = textAfterInitialToken.get(line);
                if (continuationTrimmed.startsWith(indentString))
                    continuationTrimmed = continuationTrimmed.substring(indentString.length());
                else if (verbose)
                {
                    System.out.println("    WARNING: " + filename + ":" + (firstLineOfItem + line)
                            + " too small indent");
                }
                b.append(continuationTrimmed);
                ++line;
            }
            return b.toString();
        }

        /**
         * @return Text including the initial token (if any).
         */
        public String getFullText(int indentLevel)
        {
            return initialTokenUntrimmed + getTextAfterInitialToken(indentLevel);
        }
    }

    public ApidocTagParser(List<String> lines, String filename, int firstLine, boolean verbose)
    {
        this.filename = filename;
        this.firstLine = firstLine;
        this.verbose = verbose;
        this.lines = lines;
        line = 0;
        item = null;
    }

    public void parseNextItem()
        throws ApidocCommentParser.Error
    {
        item = null;

        // Skip empty comment lines: those containing only "/**" or "*".
        while (line < lines.size() &&
            Utils.matchRegex(emptyCommentLineRegex, lines.get(line)) != null)
        {
            ++line;
        }

        if (line >= lines.size())
            return;

        firstLineOfItem = firstLine + line;
        String[] values = Utils.matchRegex(itemStartRegex, lines.get(line));
        if (values == null)
        {
            throw new ApidocCommentParser.Error(
                "Invalid tag line in Apidoc comment: " + lines.get(line));
        }

        ++line;
        List<String> textAfterToken = new ArrayList<String>();
        textAfterToken.add(values[3]);
        while (line < lines.size())
        {
            final String[] continuation = Utils.matchRegex(
                itemContinuationRegex, lines.get(line));
            if (continuation == null)
                break;

            textAfterToken.add(continuation[0]);
            ++line;
        }

        item = new Item(values[0], values[1], values[2], textAfterToken);
    }

    public Item getItem()
    {
        return item;
    }

    //--------------------------------------------------------------------------

    private final String filename;
    private final boolean verbose;
    private final int firstLine;
    private final List<String> lines;
    private int line;
    private int firstLineOfItem;
    private Item item;

    //--------------------------------------------------------------------------

    private static final Pattern emptyCommentLineRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?\\s*");
      //     /*       *

    private static final Pattern itemStartRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?\\*?\\s*(%[^\\s\\[]+)\\s*(\\[\\w+\\])?\\s*([^\\[\\s][^\\s]*\\s*)?(.*)");
      //     /*       *           %tag             [attr]           Token                  ...

    private static final Pattern itemContinuationRegex = Pattern.compile(
        "\\s*\\* ([^%]*)");
      //      *' '     non-%...
}
