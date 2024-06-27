// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import java.util.*;

/**
 * Helper functions for handling Apidoc structure elements.
 */
public final class ApidocUtils
{
    private ApidocUtils() {}

    public static final class Error
        extends Exception
    {
        public Error(String message)
        {
            super(message);
        }
    }

    /**
     * @throws Error if not found.
     */
    public static Apidoc.Group getGroupByUrlPrefix(
        Apidoc apidoc, String urlPrefix, boolean isProprietary) throws Error
    {
        for (Apidoc.Group group: apidoc.groups)
        {
            if (group.urlPrefix.equals(urlPrefix)
                && (isProprietary == group.groupName.startsWith("Proprietary ")))
            {
                return group;
            }
        }

        // For proprietary functions, no "Proprietary ..." group found - look for any group.
        if (isProprietary)
        {
            for (Apidoc.Group group: apidoc.groups)
            {
                if (group.urlPrefix.equals(urlPrefix))
                    return group;
            }
        }

        throw new Error("Group not found in Apidoc: " + urlPrefix);
    }

    public static Apidoc.Group getGroupByName(Apidoc apidoc, String name)
    {
        for (Apidoc.Group group: apidoc.groups)
        {
            if (group.groupName.equals(name))
                return group;
        }
        Apidoc.Group group = new Apidoc.Group();
        group.groupName = name;
        group.urlPrefix = "";
        apidoc.groups.add(group);
        return group;
    }

    public static void sortGroups(Apidoc apidoc, List<String> groupNames)
    {
        if (groupNames == null)
            throw new IllegalStateException();

        for (Apidoc.Group group: apidoc.groups)
        {
            if (groupNames.contains(group.groupName))
                sortGroup(group);
        }
    }

    public static void sortGroup(Apidoc.Group group)
    {
        Collections.sort(group.functions, new Comparator<Apidoc.Function>()
        {
            @Override
            public int compare(Apidoc.Function f1, Apidoc.Function f2)
            {
                return f1.name.compareTo(f2.name);
            }
        });
    }

    /**
     * @return false if duplicate function found.
     */
    public static boolean checkFunctionDuplicate(
        Apidoc.Group group, Apidoc.Function functionToCheck)
    {
        for (Apidoc.Function function: group.functions)
        {
            if (function.name.equals(functionToCheck.name)
                && function.method.equals(functionToCheck.method))
                return false;
        }
        return true;
    }
}
