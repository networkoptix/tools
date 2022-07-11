
enum class ExampleEnum
{
    one = 1,
    two = 2,
};

struct ExampleStruct
{
    /**%apidoc
     * %example Example id
     */
    QnUuid id;

    /**%apidoc
     * %example 0
     */
    int i;

    ExampleEnum e;
    std::chrono::seconds secondsS;
};

struct NamedMap: std::map<QnUuid, ExampleStruct>
{
};

//struct NamedVariantMap: std::map<QnUuid, std::variant<int, ExampleStruct>>
//{
//};

struct ExampleData
{
    /**%apidoc
     * %value Id value
     */
    QnUuid idWithValue;

    ExampleStruct inner;
    std::vector<std::chrono::seconds> secondListS;
    std::variant<int, ExampleStruct> variant;
    std::variant<ExampleStruct, ExampleStruct> variantOfTwoStructs;
    std::vector<std::variant<int, ExampleStruct>> variantList;
    std::variant<int, std::map<QString, ExampleStruct>> variantWithMap;
    std::variant<int, std::vector<ExampleStruct>>> variantWithList;
    std::variant<int, std::vector<std::map<QString, ExampleStruct>>> variantWithMapList;
    std::variant<int, std::chrono::seconds> variantWithChrono;
//    std::variant<int, std::variant<QString, ExampleStruct>>> variantWithVariant;
    std::map<QString, ExampleStruct> map;
    std::vector<std::map<QString, ExampleStruct>> mapList;
    std::map<QString, std::vector<ExampleStruct>> mapOfList;
    std::map<QString, NamedMap> mapOfNamedMap;
//    std::map<QString, std::chrono::seconds> chronoMap;
//    std::map<QString, std::variant<QString, ExampleStruct>> mapWithVariant;
//    std::map<QString, NamedVariantMap> mapOfNamedVariantMap;
//    std::vector<std::map<QString, std::variant<QString, ExampleStruct>>> mapListWithVariant;
//    std::map<QString, std::vector<std::variant<QString, ExampleStruct>>> mapWithVariantList;
//    std::map<QString, std::map<QnUuid, ExampleStruct>> mapOfMap;
};
