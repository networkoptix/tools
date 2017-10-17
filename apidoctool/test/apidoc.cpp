// This cpp file contains Apidoc comments that should be parsed as an equivalent to apidoc.xml.

/**%apidoc POST /urlPrefix/testFunction1
 * %// This is an apidoc comment - this tag and its text do not appear in xml, even in case it is
 *     multiline, as in this example. The comments ends with the start of any other percent-tag.
 * %param withProprietaryValues
 *     %value regularValue Appears in xml.
 *     %value[proprietary] proprietaryValue Such values are ignored, thus, do not appear in xml.
 */
regUpdate<ApiDummyData>(dummy, ApiCommand::testFunction1);
