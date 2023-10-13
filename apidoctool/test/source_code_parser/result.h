// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/


namespace nx::network::rest {

/**%apidoc JSON object including the error status.
 * %param:enum errorId Mnemonic error id corresponding to the error code.
 *     %value ok
 *     %value serviceUnavailable
 *     %value unauthorized
 *     %value sessionExpired
 *
 */
struct Result
{
    enum Error
    {
        /**%apidoc
         * %caption 0
         */
        NoError = 0

        /**%apidoc[proprietary]
         * %caption 2
         */
        ServiceUnavailable = 2,

        /**%apidoc
         * %caption 3
         * %deprecated Deprecated description
         */
        Unauthorized = 3,

        /**%apidoc[proprietary]
         * %caption 4
         * %deprecated Deprecated description
         */
        SessionExpired = 4
    };

    enum ProprietaryEnum
    {
        /**%apidoc[proprietary]
         * %caption test0
         */
        Test0,

        /**%apidoc[proprietary]
         * %caption test1
         */
        Test1
    };

    enum DeprecatedEnum
    {
        /**%apidoc
         * %caption test2
         * %deprecated Deprecated description
         */
        Test2,

        /**%apidoc
         * %caption test3
         * %deprecated Deprecated description
         */
        Test3
    };

    enum PartiallyProprietaryEnum
    {
        /**%apidoc
         * %caption test4
         */
        Test4,

        /**%apidoc[proprietary]
         * %caption test5
         */
        Test5,
    };

    enum PartiallyDeprecatedEnum
    {
        /**%apidoc
         * %caption test7
         */
        Test6,

        /**%apidoc
         * %caption test8
         * %deprecated Deprecated description
         */
        Test7,
    };

    /**%apidoc
     * Error code on failure (as an integer inside an enquoted string), or "0" on success.
     * %deprecated Use errorId instead.
     */
    Error error = Error::NoError;

    /**%apidoc
     * ProprietaryEnum description.
     */
    ProprietaryEnum proprietaryTest = ProprietaryEnum::Test0;

    /**%apidoc
     * DeprecatedEnum description.
     */
    DeprecatedEnum deprecatedTest = DeprecatedEnum::Test2;

    /**%apidoc
     * PartiallyProprietaryEnum description.
     */
    PartiallyProprietaryEnum partiallyProprietaryTest = PartiallyProprietaryEnum::Test4;

    /**%apidoc
     * PartiallyDeprecatedEnum description.
     */
    PartiallyDeprecatedEnum partiallyDeprecatedTest = PartiallyDeprecatedEnum::Test7;

    /**%apidoc[proprietary]
     * Error message in English, or an empty string.
     */
    QString errorString;
};

struct ResultWithNestedSameNamedEnum
{
    enum Error
    {
        thisValueMustNotReplaceResultErrorEnum
    };
};

} // namespace nx::network::rest
