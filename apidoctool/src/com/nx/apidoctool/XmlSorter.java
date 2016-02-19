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
        System.out.println("Sorting group \"" + groupName + "\" in XML file:");
        System.out.println("    " + sourceApiXmlFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(sourceApiXmlFile));

        ApidocHandler.sortGroup(
            ApidocHandler.getGroupByName(apidoc, groupName));

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);

        System.out.println("SUCCESS: Created .xml file:");
        System.out.println("    " + outputApiXmlFile);
    }
}
