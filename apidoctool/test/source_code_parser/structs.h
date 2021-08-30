#pragma once

#include "api_globals.h"
#include "api_data.h"

namespace ec2 {

/**%apidoc Enum description*/
enum class Enum
{
    value1, /**<%apidoc value1 description*/
    /**%apidoc value2 description */
    value2 = 0x1,
    unusedValue = 0xFF, /**<%apidoc[unused] */
};

/**%apidoc InstrumentedEnum description*/
NX_REFLECTION_ENUM_CLASS(InstrumentedEnum,
    value1, /**<%apidoc value1 description*/
    /**%apidoc value2 description */
    value2 = 0x1,
    unusedValue = 0xFF /**<%apidoc[unused] */
)

namespace Qn {
    /**%apidoc Enum description*/
    enum class IndentedEnum
    {
        value1, /**<%apidoc value1 description*/
        /**%apidoc value2 description */
        value2
    };
}

/**%apidoc inner object description */
struct InnerStruct
{
    QString innerParam;
    Enum innerEnumParam;
};

struct BaseStruct
{
    /**%apidoc base value description
     */
    int baseValue;
};

/**%apidoc Input struct description
 * multiline
 */
struct NX_DEF InputStruct
    : BaseStruct
{
    int param1; /**<%apidoc[opt] int param description */
    InnerStruct innerObject;
};

/**%apidoc Output description */
struct OutputStruct
{
    /**%apidoc outputParam description
     * %value 1 one
     * %TODO_UNEXPECTED_TAG 2 two
     */
    int outputParam;
    Enum enumParam;
    void someFunction(int i)
    {
        int y = 0;
    }
};

/**%apidoc
 * Description for StructWithFantomParam.
 * %param field Overridden description of StructWithFantomParam::field.
 * %param fantomParam Description of fantomParam which is absent in the struct definition.
 */
struct StructWithFantomParam
{
    /**%apidoc Description for StructWithFantomParam::field. */
    int field;
};

} // namespace ec2
