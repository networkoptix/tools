package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCode;
import com.nx.util.Utils;
import com.nx.util.XmlUtils;

import java.io.File;

public final class CodeToXmlExecutor
    extends Executor
{
    public File vmsPath;
    public File templateApiXmlFile;
    public File outputApiXmlFile;
    public String sourceFileExtraSuffix = "";

    public int execute()
        throws Exception
    {
        final File connectionFactoryCppFile = Utils.insertSuffix(
            new File(vmsPath + CONNECTION_FACTORY_CPP), sourceFileExtraSuffix);

        System.out.println("Parsing Apidoc in C++ and inserting to XML.");
        System.out.println("Input files:");
        System.out.println("    " + connectionFactoryCppFile);
        System.out.println("    " + templateApiXmlFile);

        // NOTE: This code can be easily rewritten to avoid deserializing and
        // serializing of untouched XML groups.

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(templateApiXmlFile));

        SourceCode reader = new SourceCode(connectionFactoryCppFile);

        SourceCodeParser parser = new SourceCodeParser(reader);

        final Apidoc.Group targetGroup = new Apidoc.Group();
        final int processedFunctionsCount = parser.parseCommentsFromSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME), targetGroup);

        ApidocHandler.replaceFunctions(apidoc, targetGroup);

        System.out.println("Processed " + processedFunctionsCount + " API functions");

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);
        System.out.println("Created .xml file:");
        System.out.println("    " + outputApiXmlFile);

        return processedFunctionsCount;
    }
}
