// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.Utils;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Works with the specific versions of several APIs specified in the apidoctool.properties file. It
 * is used to filter functions not matching the required version out of the apidoctool result, and
 * to check that all the text fragments matching the specified APIs are exactly the required
 * version, or their version range contains the required version. The accepted range fragments are
 * replaced with the required version.
 */
public class ApiVersion
{
    public ApiVersion(final String value) throws Exception
    {
        final String[] values = Utils.matchRegex(regex, value);
        if (values == null)
            throw new Exception("apiVersions parameter `" + value + "` is invalid.");

        this.value = value;
        prefix = values[0];
        version = Integer.parseInt(values[1]);
        pathVersionRegex = Pattern.compile(prefix + "(\\d+)(.*)");
        pathVersionRangeRegex = Pattern.compile("(" + prefix + "\\{(\\d+)-(\\d+)?\\})(.*)");
        textPathVersionRegex = Pattern.compile(prefix + "(\\d+)");
        textPathVersionRangeRegex = Pattern.compile(prefix + "\\{(\\d+)-(\\d+)?\\}");
    }

    public static String applyExactOrNearestVersionToRange(
        final String path, final List<ApiVersion> apiVersions) throws Exception
    {
        for (final ApiVersion apiVersion: apiVersions)
        {
            final String[] patternValues = Utils.matchRegex(apiVersion.pathVersionRangeRegex, path);
            if (patternValues == null)
                continue;

            final int firstVersion = Integer.parseInt(patternValues[1]);
            final int lastVersion = patternValues[2].isEmpty()
                ? Integer.MAX_VALUE
                : Integer.parseInt(patternValues[2]);
            if (firstVersion > lastVersion)
            {
                throw new Exception(patternValues[0] + " is invalid: first version " + firstVersion +
                    " is greater than last version " + lastVersion + '.');
            }
            final String pathTail = path.substring(patternValues[0].length());
            if (firstVersion > apiVersion.version)
                return apiVersion.prefix + firstVersion + pathTail;
            if (lastVersion < apiVersion.version)
                return apiVersion.prefix + lastVersion + pathTail;
            return apiVersion.value + pathTail;
        }
        return path;
    }

    public static String applyExactVersion(
        String text, final List<ApiVersion> apiVersions) throws Exception
    {
        for (final ApiVersion apiVersion: apiVersions)
        {
            final Matcher matcher = apiVersion.textPathVersionRegex.matcher(text);
            if (!matcher.find())
                continue;
            do
            {
                if (Integer.parseInt(matcher.group(1)) != apiVersion.version)
                {
                    throw new Exception(matcher.group(0) + " is invalid: only " + apiVersion.value +
                        " is allowed.");
                }
            } while (matcher.find(matcher.start() + matcher.group(0).length()));
        }

        String result = "";
        for (final ApiVersion apiVersion: apiVersions)
        {
            final Matcher matcher = apiVersion.textPathVersionRangeRegex.matcher(text);
            if (!matcher.find())
                continue;

            int beginIndex = 0;
            do
            {
                final int firstVersion = Integer.parseInt(matcher.group(1));
                final int lastVersion = matcher.group(2) == null
                    ? Integer.MAX_VALUE
                    : Integer.parseInt(matcher.group(2));
                if (firstVersion > lastVersion)
                {
                    throw new Exception(matcher.group(0) + " is invalid: first version " +
                        firstVersion + " is greater than last version " + lastVersion + '.');
                }
                if (lastVersion < apiVersion.version)
                {
                    throw new Exception(matcher.group(0) + " is invalid: last version " +
                        lastVersion + " is less than " + apiVersion.value + '.');
                }
                if (firstVersion > apiVersion.version)
                {
                    throw new Exception(matcher.group(0) + " is invalid: first version " +
                        firstVersion + " is greater than " + apiVersion.value + '.');
                }
                final int endIndex = matcher.start();
                result += text.substring(beginIndex, endIndex) + apiVersion.prefix +
                    Math.max(firstVersion, apiVersion.version);
                beginIndex = endIndex + matcher.group(0).length();
            } while (matcher.find(beginIndex));
            result += text.substring(beginIndex);
            text = result;
            result = "";
        }
        return text;
    }

    public static boolean shouldPathBeIgnored(final String path, final List<ApiVersion> apiVersions)
    {
        for (final ApiVersion apiVersion: apiVersions)
        {
            final String[] pathVersionValues = Utils.matchRegex(apiVersion.pathVersionRegex, path);
            if (pathVersionValues != null)
                return Integer.parseInt(pathVersionValues[0]) != apiVersion.version;
        }
        return false;
    }

    private final String value;
    private final String prefix;
    private final int version;
    private final Pattern pathVersionRegex;
    private final Pattern pathVersionRangeRegex;
    private final Pattern textPathVersionRegex;
    private final Pattern textPathVersionRangeRegex;

    private static final Pattern regex = Pattern.compile("^((?:/[\\w\\d-]+)*/v)(\\d+)$");
    //                                                     0Prefix             1Number
}
