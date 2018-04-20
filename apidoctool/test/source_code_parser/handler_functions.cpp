// This cpp file contains Apidoc comments applied to "hanlder" registration type,
// that should be parsed as an equivalent to apidoc.xml.

/**%apidoc GET /urlPrefix/testFunction2
 * %param someParam
 *     %value regularValue Appears in xml.
 * %return some result description
 *     %param someParam some result param
 *
 * %apidoc GET /urlPrefix/testFunction2/add some function description
 * {
 *     test: "test"
 * }
 * %param someParam some
 *     param description
 *         with indent
 *     continue description
 *     continue description
 *     %param someParam.field description
 *         continue description
 *             with indent
 *         continue description
 * %return some result description
 */
reg("urlPrefix/testFunction2", new onTestFunction2());
