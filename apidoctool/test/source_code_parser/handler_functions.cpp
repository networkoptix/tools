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
 * %param:object someParam some
 *     param description
 *         with indent
 *     continue description
 *     continue description
 *     %param:integer someParam.field  description
 *         continue description
 *             with indent
 *         continue description
 * %return: string some result description
 */
reg("urlPrefix/testFunction2", new onTestFunction2());

/**%apidoc Enum
 * description
 */
enum class Enum
{
    value1, /**<%apidoc value1 description */
    /**%apidoc value2 description
     * %deprecated Explanation why the enum value is deprecated
     */
    value2,
    /**%apidoc[proprietary] value3 description
     * Proprietary description
     */
    value3,
    /**%apidoc[proprietary] value3 description
     * Proprietary description
     * %deprecated Deprecated description
     */
    value4
};

struct ElementStruct
{
};

/**%apidoc SomeStruct description */
struct SomeStruct
{
    /**%apidoc[opt]:object
     * List as object
     */
    std::vector<ElementStruct> elements;

    /**%apidoc outputParam Param description
     * %value 1 one
     * %value 2 two
     */
    int outputParam;

    /**%apidoc enumParam param description
     * %deprecated Explanation why the param is deprecated
     */
    Enum enumParam;
    /**%apidoc optUuid param description
     * %deprecated
     */
    std::optional<QnUuid> optUuid;
    Enum enumParam;
    /**%apidoc[proprietary] optUuids param description */
    std::optional<std::vector<QnUuid>> optUuids;
};

/**%apidoc GET /urlPrefix/testFunction3
 * %struct SomeStruct
 * %param outputParam Param description overridden
 *     %value regularValue Appears in xml.
 * %return some result description
 *     %struct SomeStruct
 */
reg("urlPrefix/testFunction3", new onTestFunction3());


/**%apidoc GET /urlPrefix/testFunction4
 * %param outputParam Param description
 * %return some result description
 *     %param:object someParam description
 *     %struct SomeStruct
 *     %param:integer someParam.outputParam overridden description
 */
reg("urlPrefix/testFunction4", new onTestFunction4());

/**%apidoc Derived description
 * %param [unused] outputParam
 * %param enumParam Overriding description in StructDerived for SomeStruct::enumParam
 */
struct StructDerived: SomeStruct
{
    /**%apidoc Additional param*/
    int addParam;
};

/**%apidoc GET /urlPrefix/testFunction5
 * %return
 *     %struct StructDerived
 */
reg("urlPrefix/testFunction5", new onTestFunction5());

/**%apidoc Nested description
 * %param [unused] nested.outputParam
 * %param nested.enumParam Overriding description in StructNested for nested SomeStruct::enumParam
 */
struct StructNested
{
    /**%apidoc Nested overriden description*/
    SomeStruct nested;

    /**%apidoc Additional param*/
    int addParam;
};

/**%apidoc GET /urlPrefix/testFunction6
 * %return
 *     %struct StructNested
 */
reg("urlPrefix/testFunction6", new onTestFunction6());

/**%apidoc Description for StructWithDescription. */
struct StructWithDescription
{
    /**%apidoc Description for StructWithDescription::field. */
    int field;
};

/**%apidoc GET /urlPrefix/testReturnStructWithOverriddenDescription
 * %return Overridden description.
 *     %struct StructWithDescription
 */
reg("urlPrefix/testReturnStructWithOverriddenDescription", new handler());

/**%apidoc GET /urlPrefix/testReturnStructWithDescription
 * %return
 *     %struct StructWithDescription
 */
reg("urlPrefix/testReturnStructWithDescription", new handler());

/**%apidoc GET /urlPrefix/testReturnStructArray
 * %return:array
 *     %struct StructWithDescription
 */
reg("urlPrefix/testReturnStructArray", new handler());

/**%apidoc GET /urlPrefix/testValuesFromParamStruct
 * %struct SomeStruct
 * %param outputParam Param description overridden
 * %return some result description
 *     %struct SomeStruct
 */
reg("urlPrefix/testValuesFromParamStruct", new onTestValuesFromParamStruct());

/**%apidoc
 * Description for StructWithFantomParam.
 * %param fantomParam Description of fantomParam which is absent in the struct definition.
 */
struct StructWithFantomParam
{
    /**%apidoc Description for StructWithFantomParam::field. */
    int field;
};

/**%apidoc GET /urlPrefix/testStructWithFantomParam
 * %return
 *     %struct StructWithFantomParam
 */
reg("urlPrefix/testStructWithFantomParam", new handler());

/**%apidoc Description of Result. */
struct Result
{
    /**%apidoc Description of resultField. */
    int resultField;
};

/**%apidoc Description of Reply. */
struct Reply
{
    /**%apidoc Description of replyField. */
    int replyField;
};

/**%apidoc GET /urlPrefix/testResultWithReply
 *
 * %// Assuming that the function accepts as input and returns the same data - `struct Result` with
 * %// a fantom param `struct Reply reply` which is not a C++ field but added during serialization.
 *
 * %struct Result
 * %param reply
 *     %struct Reply
 * %return
 *     %struct Result
 *     %param reply
 *         %struct Reply
 */
reg("urlPrefix/testResultWithReply", new handler());

/**%apidoc GET /urlPrefix/deprecatedFunctionWithoutExplanation
 * Description of a deprecated function
 * %deprecated
 *
 * %return
 *     %param reply
 *         %struct Reply
 */
reg("urlPrefix/deprecatedFunctionWithoutExplanation", new handler());

/**%apidoc GET /urlPrefix/deprecatedFunctionWithExplanation
 * Description of a deprecated function
 * %deprecated Explanation why the function is deprecated
 *
 * %return
 *     %param reply
 *         %struct Reply
 */
reg("urlPrefix/deprecatedFunctionWithExplanation", new handler());

