package com.nx.apidoc;

import com.nx.util.Utils;

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
    public static final class Item
    {
        private final String tag;
        private final String attribute;
        private final String initialTokenUntrimmed;
        private final String textAfterInitialToken;

        protected Item(String tag, String attribute,
            String initialTokenUntrimmed, String textAfterInitialToken)
        {
            assert tag != null;
            assert !tag.isEmpty();
            this.tag = tag;

            this.attribute = attribute == null ? "" : attribute;

            this.initialTokenUntrimmed =
                initialTokenUntrimmed == null ? "" : initialTokenUntrimmed;

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
        public String getTextAfterInitialToken()
        {
            return textAfterInitialToken;
        }

        /**
         * @return Text including the initial token (if any).
         */
        public String getFullText()
        {
            return initialTokenUntrimmed + textAfterInitialToken;
        }
    }

    public ApidocTagParser(List<String> lines)
    {
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

        String[] values = Utils.matchRegex(itemStartRegex, lines.get(line));
        if (values == null)
        {
            throw new ApidocCommentParser.Error(
                "Invalid tag line in Apidoc comment: " + lines.get(line));
        }

        ++line;
        final String text = values[3] == null ? "" : values[3];
        StringBuilder b = new StringBuilder(text.trim());

        while (line < lines.size())
        {
            final String[] continuation = Utils.matchRegex(
                itemContinuationRegex, lines.get(line));
            if (continuation == null)
                break;

            b.append("\n");
            b.append(continuation[0].trim());
            ++line;
        }

        item = new Item(values[0], values[1], values[2], b.toString().trim());
    }

    public Item getItem()
    {
        return item;
    }

    //--------------------------------------------------------------------------

    private final List<String> lines;
    private int line;
    private Item item;

    //--------------------------------------------------------------------------

    private static final Pattern emptyCommentLineRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?\\s*");
      //     /*       *

    private static final Pattern itemStartRegex = Pattern.compile(
        "\\s*(?:/\\*)?\\*?\\s*(%[^\\s\\[]+)\\s*(\\[\\w+\\])?\\s*([^\\s]+\\s*)?(.*)");
      //     /*       *       %tag             [attr]           Token         ...

    private static final Pattern itemContinuationRegex = Pattern.compile(
        "\\s*\\*?\\s*([^%]*)");
      //       *     non-%...
}
