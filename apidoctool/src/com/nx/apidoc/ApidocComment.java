package com.nx.apidoc;

/**
 * Base class for mechanisms which require knowledge about Apidoc Comments, both
 * for generation and parsing.
 */
public abstract class ApidocComment
{
    // TODO: Consider defining default "format" and the description of its values in the C++ code.
    protected static final String DEFAULT_FORMAT_DESCRIPTION =
        "Data format. Default value is \"json\".";

    protected static final String TAG_APIDOC = "%apidoc";
    protected static final String TAG_STRUCT = "%struct";
    protected static final String TAG_COMMENTED_OUT = "%//";
    protected static final String TAG_CAPTION = "%caption";
    protected static final String TAG_INGROUP = "%ingroup";
    protected static final String TAG_PERMISSIONS = "%permissions";
    protected static final String TAG_PARAM = "%param";
    protected static final String TAG_VALUE = "%value";
    protected static final String TAG_RETURN = "%return";
    protected static final String TAG_DEPRECATED = "%deprecated";

    protected static final String ATTR_PROPRIETARY = "[proprietary]";
    protected static final String ATTR_READONLY = "[readonly]";
    protected static final String ATTR_OPT = "[opt]";
    protected static final String ATTR_DEFAULT = "[default]";
    protected static final String ATTR_REF = "[ref]";
    protected static final String ATTR_UNUSED = "[unused]";

    protected static final String LABEL_ARRAY_PARAMS = "arrayParams";

    protected static final String PARAM_FORMAT = "format";

//-------------------------------------------------------------------------------------------------
// Apidoc comment format
//
// ATTENTION: This specification should be kept in sync with the current implementation,
// because currently it is the only documentation for the Apidoc comment format.
//
// - Introduction
//
// See Apidoc comment examples in test/source_code_parser/.
//
// Apidoc comments are C++ comments from which the Rest API documentation XML is generated by
// the Java-based command-line tool "apidoctool". Such comments are placed in the C++ code
// before the respective API method registration lines, and, to avoid duplication, can be partially
// moved to classes, class fields, enums and enum items.
//
// The format of Apidoc comments is designed to resemble Javadoc/Doxygen, but using "%" for
// tags instead of "@" to differentiate from Javadoc/Doxygen tags. Thus, Apidoc comments which
// relate to classes, class fields, enums, and enum items are technically Javadoc/Doxygen
// comments, and the whole Apidoc comment contents is treated by Doxygen as a plain text.
//
// - Syntax
//
// Each Apidoc comment begins with "/**%apidoc", or, if it follows a class field or enum item,
// with "/**<%apidoc", and ends with "*/".
//
// Apidoc comments for API functions start with a function header denoting the HTTP method and the
// function name, followed by "%param" tags for function arguments. Params which are JSON objects
// or object arrays are documented with inner "%value" tags. Then follows the "%return" tag which
// may describe a JSON object or object array with inner "%param" and "%value" tags as well.
//
// If an API function's input, result, or a certain param is an object or an object array, and the
// C++ struct for such object has apidoc comments, these comments can be embedded by specifying the
// "%struct StructName" tag instead of or additionally to "%param" tags for the object fields; if
// "%param" tags are specified additionally, they override comments coming from the struct.
//
// Each API method documentation is always multiline, and may contain multiple sections (each
// starting with "%apidoc"), when a single C++ method registration line yields multiple functions.
//
// Object arrays and nested objects are syntactically represented as a linear list of params, but
// should use names like "parent[].field" and "parent.field", recursively.
//
// Apidoc comment grammar is shown below using the XML specification notation.
//
// NOTE: This grammar can be formally inaccurate, but gives a good understanding of the syntax.
//
//.................................................................................................
//
// S ::= (#x20)+
//
// NewLine ::= #x0A | (#x0D #x0A)
//
// TextLine ::= S* "*" (S Char+)?
//
// Tag ::= [a-z]+ //< See ApidocComment.TAG_*
//
// TagLabel ::= [A-Za-z]+ //< See enum Apidoc.Type.toString()
//
// TagAttr ::= [a-z]+ //< See ApidocComment.ATTR_*
//
// Item ::= //< Basically, a tag with a text that follows it.
//     S* "*" S+ "%" Tag (S* "[" TagAttr "]")? (S* ":" S* TagLabel)? \
//     S* (S Char+ (NewLine TextLine)*)?
//
// FunctionName ::= ("/api/" | "/ec2/") [_A-Za-z0-9{}/]+ //< Braces are used as placeholders.
//
// FunctionHeader ::=
//     "%apidoc" (S* ":" S* "arrayParams")? (S* "[" TagAttr "]")? S ("GET" | "POST") S FunctionName
//
// FunctionApidocComment ::= //< NOTE: Can contain multiple "%apidoc" tags.
//     S* "/**" (FunctionHeader (NewLine TextLine)* (NewLine Item)*)+ NewLine S* "*/"
//
// StructOrEnumApidocComment ::= //< Can be either single-line or multiline.
//     S* "/**%apidoc" (S* "[" TagAttr "]")? S* \
//     Char* (NewLine TextLine)* (NewLine (Item NewLine)*)? S* "*/"
//
// FieldApidocComment ::= //< Does not contain tags besides the initial "%apidoc".
//     S* "/**%apidoc" (S* "[" TagAttr "]")? S* \
//     Char* (NewLine TextLine)* NewLine? S* "*/"
//
// FieldOrEnumItemPostfixApidocComment ::= //< Always single-line.
//     S* "/**<%apidoc" (S* "[" TagAttr "]")? Char* "*/"
//
// EnumItemApidocComment ::= //< Can contain "%caption <effective-item-caption>".
//     S* "/**%apidoc" (S* "[" TagAttr "]")? S* \
//     Char* (NewLine TextLine)* NewLine? S* \
//     ("%caption" S+ [_A-Za-z0-9]+)? S* NewLine? S* "*/"
//
//.................................................................................................
//
// - Semantics of labels
//
// Label "apidoc:arrayParams" means that the function receives an array of objects instead of a
// single object.
//
// Labels of "param" and "result" tags denote param types.
//
// - Semantics of attributes
//
// Attribute "[unused]" may appear in "%param"; it means that the item must be omitted from the
// generated XML.
//
// Attribute "[proprietary]" may appear in "%param", or function's "%apidoc", where it means that the item must be
// hidden from the user when the generated XML is presented in the browser, but should technically be present in
// that XML; also it may appear in "%value" meaning that the item must be completely ignored.
//
// Attribute "[opt]" may appear in "%param" or struct field's "%apidoc" to mark it as optional.
//
// Attribute "[default]" may appear only in "%param" with the name "format":
//     %param[default] format
// This line inserts into XML a hard-coded text which describes the "format" parameter which
// is common to many API functions and defines the format (JSON, UBJSON, etc) of the requested
// data.
}
