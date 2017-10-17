package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCodeEditor;
import com.nx.util.Utils;
import com.nx.util.XmlSerializer;
import com.nx.util.XmlUtils;

import java.io.File;

public final class ApiXmlToVmsCodeExecutor
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

        System.out.println("apidoctool: inserting apidoc from XML into C++");
        System.out.println("    Input: " + sourceApiXmlFile);
        System.out.println("    Input: " + connectionFactoryCppFile);

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(sourceApiXmlFile));

        final SourceCodeEditor editor = new SourceCodeEditor(
            connectionFactoryCppFile);

        final SourceCodeGenerator generator = new SourceCodeGenerator(editor);

        final int processedFunctionsCount = generator.insertCommentsForSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        System.out.println("    API functions processed: " + processedFunctionsCount);

        editor.saveToFile(outputConnectionFactoryCppFile);
        System.out.println("    Output: " + outputConnectionFactoryCppFile);

        XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApiXmlFile);

        return processedFunctionsCount;
    }
}
