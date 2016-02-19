package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.*;
import java.util.regex.Pattern;

/**
 * Helper functions for handling Apidoc structure elements.
 */
public final class ApidocHandler
{
    private ApidocHandler() {}

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
    public static Apidoc.Group getGroupByName(Apidoc apidoc, String groupName)
        throws Error
    {
        for (Apidoc.Group group: apidoc.groups)
        {
            if (group.groupName.equals(groupName))
                return group;
        }
        throw new Error("Group not found in Apidoc XML: " + groupName);
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
        throw new Error("Group not found in Apidoc XML: " + newGroup.groupName);
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
