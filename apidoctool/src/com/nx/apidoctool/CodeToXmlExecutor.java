package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.*;

import java.io.File;

public final class CodeToXmlExecutor
    extends Executor
{
    public File vmsPath;
    public File templateApiXmlFile;
    public File outputApiXmlFile;
    public File outputApiJsonFile; ///< Can be null if not needed.
    public String sourceFileExtraSuffix = "";

    public int execute()
        throws Exception
    {
        final File connectionFactoryCppFile = Utils.insertSuffix(
            new File(vmsPath + CONNECTION_FACTORY_CPP), sourceFileExtraSuffix);

        System.out.println("apidoctool: parsing apidoc in C++ and inserting into XML");
        System.out.println("    Input: " + connectionFactoryCppFile);
        System.out.println("    Input: " + templateApiXmlFile);

        // NOTE: This code can be easily rewritten to avoid deserializing and
        // serializing of untouched XML groups.

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(templateApiXmlFile));

        SourceCode reader = new SourceCode(connectionFactoryCppFile);

        SourceCodeParser parser = new SourceCodeParser(verbose, reader);

        final Apidoc.Group targetGroup = new Apidoc.Group();
        final int processedFunctionsCount = parser.parseCommentsFromSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME), targetGroup);

        ApidocHandler.replaceFunctions(apidoc, targetGroup);

        System.out.println("    API functions processed: " + processedFunctionsCount);

        XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApiXmlFile);

        if (outputApiJsonFile != null)
        {
            final String json = JsonSerializer.toJsonString(apidoc);
            Utils.writeStringToFile(outputApiJsonFile, json);
            System.out.println("    Output: " + outputApiJsonFile);
        }

        return processedFunctionsCount;
    }
}
