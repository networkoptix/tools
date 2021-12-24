
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
    // TODO: Move out and use NX_REFLECTION_ENUM.
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

    /**%apidoc[proprietary]
     * Error message in English, or an empty string.
     */
    QString errorString;
};
} // namespace nx::network::rest
