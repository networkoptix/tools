package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCodeEditor;
import com.nx.util.Utils;
import com.nx.util.XmlUtils;

import java.io.File;

public final class XmlToCodeExecutor
    extends Executor
{
    public File vmsPath;
    public File sourceApiXmlFile;
    public File outputApiXmlFile;

    public int execute()
        throws Exception
    {
        final File connectionFactoryCppFile = new File(
            vmsPath + CONNECTION_FACTORY_CPP);

        final File outputConnectionFactoryCppFile = Utils.insertSuffix(
            connectionFactoryCppFile, OUTPUT_FILE_EXTRA_SUFFIX);

        System.out.println("Inserting Apidoc from XML to C++.");
        System.out.println("Input files:");
        System.out.println("    " + sourceApiXmlFile);
        System.out.println("    " + connectionFactoryCppFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(sourceApiXmlFile));

        final SourceCodeEditor editor = new SourceCodeEditor(
            connectionFactoryCppFile);

        final SourceCodeGenerator generator = new SourceCodeGenerator(editor);

        final int processedFunctionsCount = generator.insertCommentsForSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        System.out.println("Processed " + processedFunctionsCount + " API functions");

        editor.saveToFile(outputConnectionFactoryCppFile);
        System.out.println("Created .cpp file:");
        System.out.println("    " + outputConnectionFactoryCppFile);

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);
        System.out.println("Created .xml file:");
        System.out.println("    " + outputApiXmlFile);

        return processedFunctionsCount;
    }
}
