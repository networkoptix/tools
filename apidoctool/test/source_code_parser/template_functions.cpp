// This cpp file contains Apidoc comments that apply to "template" regisrtation type,
// that should be parsed as an equivalent to apidoc.xml.

/**%apidoc POST /urlPrefix/testFunction1
 * %// This is an apidoc comment - this tag and its text do not appear in xml, even in case it is
 *     multiline, as in this example. The comments ends with the start of any other percent-tag.
 * %//Testing comments without a space after `//`.
 * %param withProprietaryValues
 *     %value regularValue Appears in xml.
 *     %value[proprietary] proprietaryValue Such values are ignored, thus, do not appear in xml.
 * %return some result description
 *     %param someParam some result param
 *     %param[proprietary] proprietaryParam proprietary result param
 */
regUpdate<ApiDummyData>(dummy, ApiCommand::testFunction1);

enum class Status;

enum ResourceStatus
{
    Offline,
    Unauthorized,
    Online,
    Recording,
    NotDefined,
    /*! Applies only to a server resource. A server is incompatible only when it has system
     * name different
     * from the current or it has incompatible protocol version.
     * \note Incompatible server is not the same as fake server which is create in the client by
     * QnIncompatibleServerWatcher. Fake servers can also have Unauthorized status.
     * So if you want to check if the server is fake use QnMediaServerResource::isFakeServer().
     */
    Incompatible,

    AnyStatus
};

/**%apidoc Enum description*/
enum class Enum
{
    value1, /**<%apidoc value1 description*/
    /**%apidoc value2 description*/
    value2,
};

Q_DECLARE_FLAGS(Enums, Enum)

/**%apidoc inner object description*/
struct InnerStruct
{
    QString innerParam;
    Enum innerEnumParam;
    ResourceStatus status;
};

namespace N1 {
namespace N2 {

struct BaseStruct
{
    /**apidoc base value description
     */
    int baseValue;/**<%apidoc base value description*/
};

}

}

/**%apidoc Input struct description
 * multiline
 */
struct NX_DEF InputStruct
    : N1::N2::BaseStruct
{
    int param1; /**<%apidoc[opt] int param description*/
    InnerStruct innerObject;
};

/**%apidoc Output description*/
struct OutputStruct
{
    /**%apidoc outputParam description
     * %value 1 one
     * %value 2 two
     */
    int outputParam;
    Enum enumParam;
    Enums flagsParam;
};


/**%apidoc:arrayParams GET /urlPrefix/getStorages
 * Read the list of current storages.
 * %param innerObject.innerParam override description from function comment
 */
regGet<InputStruct, OutputStructList>(p, ApiCommand::getStorages);
