package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.XmlUtils;

import java.io.File;

public class XmlSorter
{
    public String groupName;
    public File sourceApiXmlFile;
    public File outputApiXmlFile;

    public void execute()
        throws Exception
    {
        System.out.println("apidoctool: sorting group \"" + groupName + "\"");
        System.out.println("    Input: " + sourceApiXmlFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(sourceApiXmlFile));

        ApidocHandler.sortGroup(ApidocHandler.getGroupByName(apidoc, groupName));

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);

        System.out.println("    Output: " + outputApiXmlFile);
    }
}
