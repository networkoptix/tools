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

    public void execute()
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

        generator.insertCommentsForSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        editor.saveToFile(outputConnectionFactoryCppFile);
        System.out.println("SUCCESS: Created .cpp file:");
        System.out.println("    " + outputConnectionFactoryCppFile);

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);
        System.out.println("SUCCESS: Created .xml file:");
        System.out.println("    " + outputApiXmlFile);
    }
}
