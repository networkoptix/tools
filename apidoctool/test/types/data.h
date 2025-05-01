// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/


/**%apidoc Enum &ast;. */
enum class ExampleEnum
{
    /**%apidoc Enum value &ast;. */
    one = 1,

    /**%apidoc
     * Enum value with deprecated &ast;.
     * %deprecated Deprecated enum value &ast;.
     */
    two = 2,
};

struct ExampleStruct
{
    /**%apidoc
     * %example 01234567-89ab-cdef-0123-456789abcdef
     */
    QnUuid id;

    /**%apidoc
     * %example 0
     */
    int i;

    ExampleEnum e;

    /**%apidoc
     * Field with deprecated &ast;.
     * %deprecated Deprecated field &ast;.
     * %example 0
     */
    std::chrono::seconds secondsS;
};

struct NamedMap: std::map<QnUuid, ExampleStruct>
{
};

/**%apidoc[immutable] Immutable struct. */
struct ImmutableStruct
{
    int i;
};

struct StructSeconds
{
    std::chrono::seconds secondsS;
};

//struct NamedVariantMap: std::map<QnUuid, std::variant<int, ExampleStruct>>
//{
//};

/**%apidoc
 * Struct with deprecated &ast;.
 * %deprecated Deprecated struct &ast;.
 */

 // Test multiline and nested using statements
 using MapToStruct = std::map<
    QString,
    ExampleStruct // Comment in test
    // Comment in its own line
>;
using VariantWithMap = std::variant<
    int,
    MapToStruct
>;

struct ExampleData
{
    /**%apidoc
     * %value 01234567-89ab-cdef-0123-456789abcdef Value &ast;.
     */
    QnUuid idWithValue;

    /**%apidoc Field of struct &ast;. */
    ExampleStruct inner;
    std::vector<std::chrono::seconds> secondListS;
    // Separate line comment.
    std::variant<int,
        ExampleStruct> variant;
    std::variant<ExampleStruct,
        ExampleStruct> variantOfTwoStructs;
    std::vector< // Extra comments to check
        std::variant< // Big multi line
            // Separate line comment
            int,
            ExampleStruct
        >
    > variantList; // End with a comment
    VariantWithMap variantWithMap;
    std::variant<int, std::vector<ExampleStruct>>> variantWithList;
    std::variant<int, std::vector<std::map<QString, ExampleStruct>>> variantWithMapList;
    std::variant<int, std::chrono::seconds> variantWithChrono;
    std::variant<int, std::variant<QString, ExampleStruct>>> variantWithVariant;
    std::map<QString, ExampleStruct> map;
    std::vector<std::map<QString, ExampleStruct>> mapList;
    std::map<QString, std::vector<ExampleStruct>> mapOfList;
    std::map<QString, NamedMap> mapOfNamedMap;
    std::map<QString, std::chrono::seconds> chronoMap;
    std::map<QString, std::variant<QString, ExampleStruct>> mapWithVariant;
    std::vector<std::map<QString, std::variant<QString, ExampleStruct>>> mapListWithVariant;
    std::map<QString, std::vector<std::variant<QString,
        ExampleStruct>>> mapWithVariantList;
    std::map<QString, std::map<QnUuid, ExampleStruct>> mapOfMap;
    std::map<QString, std::map<QnUuid, std::variant<int, ExampleStruct>>> mapOfMapWithVariant;
//    std::map<QString, NamedVariantMap> mapOfNamedVariantMap;

    ImmutableStruct immutableStruct;

    /**%apidoc[immutable]
     * %value 0 Value with deprecated &ast;.
     *     %deprecated Deprecated value &ast;.
     * %value 1
     */
    int immutableField;

    std::optional<nx::Uuid> optionalUuid;

    /**%apidoc[opt] */
    nx::Uuid optionalUuid2;
};

/**%apidoc
 * Simple structure for order by testing
 */
struct StringOrderByExampleData
{
    /**%apidoc
     *   %value id
     *   %value name
     */
    std::string _orderBy;
    int id;
    int name;
};

/**%apidoc
 * Simple structure for order by testing
 */
struct EnumOrderByExampleData
{
    ExampleEnum _orderBy;
    std::string one;
    std::string two;
};
