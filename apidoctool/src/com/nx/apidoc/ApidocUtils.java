package com.nx.apidoc;

import com.nx.util.SourceCode;

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
        public Error(String message, Throwable cause)
        {
            super(message, cause);
        }

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

        throw new Error("Group not found in Apidoc XML: " + urlPrefix);
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

    /**
     * Move all functions from newGroup to the group with the same name in
     * apidoc, replacing old functions with the same name.
     */
    public static void replaceFunctions(Apidoc apidoc, Apidoc.Group newGroup)
        throws Error
    {
        for (Apidoc.Group group: apidoc.groups)
        {
            if (group.groupName.equals(newGroup.groupName))
            {
                replaceFunctionsInGroup(group, newGroup);
                return;
            }
        }
        throw new Error("Group not found in Apidoc XML by url prefix: [" + newGroup.groupName + "]");
    }

    private static void replaceFunctionsInGroup(
        Apidoc.Group group, Apidoc.Group newGroup)
    {
        for (Iterator<Apidoc.Function> newFuncIt =
             newGroup.functions.listIterator(); newFuncIt.hasNext();)
        {
            Apidoc.Function newFunc = newFuncIt.next();

            boolean found = false;
            for (ListIterator<Apidoc.Function> funcIt =
                 group.functions.listIterator(); funcIt.hasNext();)
            {
                Apidoc.Function func = funcIt.next();
                if (func.name.equals(newFunc.name))
                {
                    funcIt.set(newFunc);
                    newFuncIt.remove();
                    found = true;
                    break;
                }
            }
            if (!found)
            {
                group.functions.add(newFunc);
                newFuncIt.remove();
            }
        }

        sortGroup(group);
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

    /**
     * @return false if duplicate function found in entire group.
     */
    public static void checkNoFunctionDuplicates(Apidoc apidoc) throws Error
    {
        for (Apidoc.Group group: apidoc.groups)
        {
            final Set<String> uniques = new HashSet();
            for (Apidoc.Function function: group.functions)
            {
                if (!uniques.add(function.name + function.method))
                    throw new Error("Duplicate function found: [" + function.name + "]");
            }
        }
    }

    /**
     * @return null if not found.
     */
    public static Apidoc.Function findFunction(
        Apidoc.Group group, String functionName)
    {
        for (Apidoc.Function function: group.functions)
        {
            if (function.name.equals(functionName))
                return function;
        }
        return null;
    }
}
