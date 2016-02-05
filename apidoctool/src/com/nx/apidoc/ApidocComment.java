package com.nx.apidoc;

/**
 * Base class for mechanisms which require knowledge about Apidoc Comments .both
 * for generation and parsing.
 */
public abstract class ApidocComment
{
    // TODO: Consider defining default "format" in the Source Code.
    protected static final String DEFAULT_FORMAT_DESCRIPTION =
        "Data format. Default value: 'json'";

    protected static final String TAG_APIDOC = "%apidoc";
    protected static final String TAG_PRIVATE = "%//";
    protected static final String TAG_CAPTION = "%caption";
    protected static final String TAG_PARAM = "%param";
    protected static final String TAG_VALUE = "%value";
    protected static final String TAG_RETURN = "%return";
    protected static final String TAG_ATTRIBUTE = "%attribute";

    protected static final String ATTR_PROPRIETARY =  "[proprietary]";
    protected static final String ATTR_OPT = "[opt]";
    protected static final String ATTR_DEFAULT = "[default]";

    protected static final String PARAM_FORMAT = "format";

    // Apidoc Comment format sample:

    /**%apidoc[proprietary] GET /ec2/listDirectory
     * Description.
     * %caption Some caption, optional
     * %param[default] format
     * %param[proprietary] Proprietary param (always optional).
     * %param[opt] folder Folder name in a virtual FS
     *     %value EarliestFirst Description.
     * %return Return object in requested format
     *     %attribute name Description
     * %// Private comment, not intended for XML.
     */
}
