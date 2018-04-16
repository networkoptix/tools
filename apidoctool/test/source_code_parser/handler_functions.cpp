// This cpp file contains Apidoc comments applied to "hanlder" registration type,
// that should be parsed as an equivalent to apidoc.xml.

/**%apidoc GET /urlPrefix/testFunction2
 * %param someParam
 *     %value regularValue Appears in xml.
 * %return some result description
 * %param someParam some result param
 */
reg("urlPrefix/testFunction2", new onTestFunction2());
