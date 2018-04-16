package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.util.XmlSerializer;
import com.nx.util.XmlUtils;

import java.io.File;
import java.util.List;

public class XmlSorter
{
    public List<String> groupNames;
    public File sourceApiXmlFile;
    public File outputApiXmlFile;

    public void execute()
        throws Exception
    {
        System.out.println("apidoctool: sorting groups \"" + groupNames + "\"");
        System.out.println("    Input: " + sourceApiXmlFile);

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
                XmlUtils.parseXmlFile(sourceApiXmlFile));

        ApidocUtils.sortGroups(apidoc, groupNames);
        XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApiXmlFile);
    }
}
