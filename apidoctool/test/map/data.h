// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/


enum class Display
{
    none = 0,
    table = (1 << 0),
    panel = (1 << 1),
    both = table|panel,
};
Q_DECLARE_FLAGS(Displays, Display)

enum class AlarmLevel
{
    none,
    warning,
    error,
};

template<typename Visitor>
constexpr auto nxReflectVisitAllEnumItems(AlarmLevel*, Visitor&& visitor)
{
    using Item = nx::reflect::enumeration::Item<AlarmLevel>;
    return visitor(
        Item{AlarmLevel::none, ""},
        Item{AlarmLevel::warning, "warning"},
        Item{AlarmLevel::error, "error"}
    );
}

struct NX_VMS_API AlarmRule
{
    AlarmLevel level = AlarmLevel::none;
    QString condition;
    QString text; //< TODO: Optional.
};
#define AlarmRule_Fields (level)(condition)(text)
QN_FUSION_DECLARE_FUNCTIONS(AlarmRule, (json), NX_VMS_API)

struct NX_VMS_API ValueRule
{
    QString name;
    QString description;
    bool isOptional = false;
    Displays display;
    QString format;
    QString calculate;
    QString insert;
    std::vector<AlarmRule> alarms;
};
#define ValueRule_Fields (name)(description)(isOptional)(display)(format)(calculate)(insert)(alarms)
QN_FUSION_DECLARE_FUNCTIONS(ValueRule, (json), NX_VMS_API)

struct NX_VMS_API ValueGroupRules
{
    QString name;
    std::map<QString, ValueRule> values;
};
#define ValueGroupRules_Fields (name)(values)
QN_FUSION_DECLARE_FUNCTIONS(ValueGroupRules, (json), NX_VMS_API)

struct NX_VMS_API ResourceRules
{
    QString name;
    QString resource;
    std::map<QString, ValueGroupRules> values;
};
#define ResourceRules_Fields (name)(resource)(values)
QN_FUSION_DECLARE_FUNCTIONS(ResourceRules, (json), NX_VMS_API)
