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
    public File optionalOutputVmsPath; //< Can be null if should equal to vmsPath.
    public File sourceApiXmlFile;
    public File outputApiXmlFile;

    public int execute()
        throws Exception
    {
        final File ec2RegistrationCppFile = new File(vmsPath + params.ec2RegistrationCpp());

        final File outputEc2RegistrationCpp = Utils.insertSuffix(
            new File(
                ((optionalOutputVmsPath != null) ? optionalOutputVmsPath : vmsPath)
                + params.ec2RegistrationCpp()),
            OUTPUT_FILE_EXTRA_SUFFIX);

        System.out.println("apidoctool: inserting apidoc from XML into C++");
        System.out.println("    Input: " + sourceApiXmlFile);
        System.out.println("    Input: " + ec2RegistrationCppFile);

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(sourceApiXmlFile));

        final SourceCodeEditor editor = new SourceCodeEditor(ec2RegistrationCppFile);

        final SourceCodeGenerator generator = new SourceCodeGenerator(editor);

        final int processedFunctionsCount = generator.insertCommentsForSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        System.out.println("    API functions processed: " + processedFunctionsCount);

        editor.saveToFile(outputEc2RegistrationCpp);
        System.out.println("    Output: " + outputEc2RegistrationCpp);

        XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApiXmlFile);

        return processedFunctionsCount;
    }
}
