package com.nx.apidoctool;

import java.util.ArrayList;

final class Replacement
{
    public final String target;
    public final String replacement;

    Replacement(String target, String replacement)
    {
        this.target = target;
        this.replacement = replacement;
    }

    public static ArrayList<Replacement> parse(String urlPrefixReplacement)
    {
        ArrayList<Replacement> replacements = new ArrayList<Replacement>();
        if (urlPrefixReplacement.isEmpty())
            return replacements;
        for (final String item: urlPrefixReplacement.trim().split(","))
        {
            final String[] pair = item.trim().split(" ");
            if (pair.length != 2)
            {
                throw new IllegalArgumentException(
                    "Invalid urlPrefixReplacement parameter, see help for valid format.");
            }
            final Replacement replacement = new Replacement(pair[0].trim(), pair[1].trim());
            if (replacement.target.isEmpty() || replacement.replacement.isEmpty())
            {
                throw new IllegalArgumentException(
                    "Invalid urlPrefixReplacement parameter, see help for valid format.");
            }
            replacements.add(replacement);
        }
        return replacements;
    }
}
