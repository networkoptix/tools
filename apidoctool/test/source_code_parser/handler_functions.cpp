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
    /**%apidoc value2 description */
    value2,
};

struct ElementStruct
{
};

/**%apidoc Output description */
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
    Enum enumParam;
    std::optional<QnUuid> optUuid;
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
 * %param enumParam Derived param description
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
 * %param nested.enumParam Nested param description
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
