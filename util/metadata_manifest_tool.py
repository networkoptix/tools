#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import json
import argparse
from pprint import pprint
from collections import OrderedDict


EVENT_TYPES = [
    {
        "pluginId": "nx.stub",
        "guids": [
            {"guid": "{7e94ce15-3b69-4719-8dfd-ac1b76e5d8f4}", "text": "nx.stub.lineCrossing"},
            {"guid": "{b0e64044-ffa3-4b7f-807a-060c1fe5a04c}", "text": "nx.stub.objectInTheArea"},
            {"guid": "{153dd879-1cd2-46b7-add6-7c6b48eac1fc}", "text": "nx.stub.car"},
            {"guid": "{c23def4d-04f7-4b4c-994e-0c0e6e8b12cb}", "text": "nx.stub.humanFace"}
        ]
    }
]


PLUGIN_IDS = {
    "{6541f47d-99b8-4049-bf55-697bd6dd1bbd}": "nx.hanwha",
    "{190ed57a-b435-a80b-1f7b-9f31c52ad63e}": "nx.axis",
    "{3d8d6c8e-d6d5-4947-9989-38089df02a1f}": "nx.dw_mtt",
    "{55c9d815-d25e-4638-98e5-40ddbafeb98e}": "nx.hikvision",
    "{a798a4a7-a1b6-48c3-b3d0-c9b04f1e84a4}": "nx.ssc",
    "{e177ffa9-9db9-f975-e4c2-760ce7b279da}": "nx.vca"
}


def main():
    parser = argparse.ArgumentParser(description=(
        "Process metadata plugin manifest: replace eventTypeId value with "
        "\"<pluginId>.<internalName>\". Generate text-replacing SQLs for the database columns."
    ))
    parser.add_argument('ecs_sql', help=(
        "SQL to generate for ecs.sqlite vms_businessrule::event_condition"))
    parser.add_argument('mserver_sql', help=(
        "SQL to generate for mserver.sqlite audit_log::params"))
    parser.add_argument('manifest_json', help="Manifest file to change", nargs='+')
    args = parser.parse_args()

    for manifest_file in args.manifest_json:
        print("Processing manifest: %s" % manifest_file)
        manifest = load_manifest(manifest_file)
        update_manifest(manifest)
        extract_event_types(manifest)
        replace_guids_in_manifest(manifest)
        save_manifest(manifest, manifest_file + '.out')

    print("")
    print("Event types:")
    pprint(EVENT_TYPES)
    print("")

    generate_sql(args.ecs_sql, "vms_businessrule", "event_condition")

    generate_sql(args.mserver_sql, "runtime_actions", "event_subtype",
        lambda guid: canonical_guid(guid), MSERVER_SQL_PREFIX, MSERVER_SQL_POSTFIX)

    sys.exit(0)


def load_manifest(manifest_file):
    with open(manifest_file) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def update_manifest(manifest):
    """Rename manifest keys as required by transition from 3.2 and old 4.0 (before text ids).
    """
    manifest.rename_key('driverId', 'pluginId')
    manifest.rename_key('driverName', 'pluginName')
    for event_type in manifest['outputEventTypes']:
        event_type.rename_key('typeId', 'id')
        event_type.rename_key('eventTypeId', 'id')
        event_type.rename_key('eventName', 'name')


def extract_event_types(manifest):
    plugin_id = PLUGIN_IDS[canonical_guid(manifest['pluginId'])]
    EVENT_TYPES.append(
        {
            'pluginId': plugin_id,
            'guids': [
                {
                    'guid': canonical_guid(event_type['id']),
                    'text': plugin_id + "." + event_type['internalName']
                } for event_type in manifest['outputEventTypes']
            ]
        }
    )


def replace_guids_in_manifest(manifest):
    manifest['pluginId'] = PLUGIN_IDS[canonical_guid(manifest['pluginId'])]
    for event_type in manifest['outputEventTypes']:
        event_type['id'] = manifest['pluginId'] + '.' + event_type['internalName']


def save_manifest(manifest, manifest_file):
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=4)


def generate_sql(
    sql_file,
    table,
    column,
    guid_func=lambda guid: guid,
    prefix="",
    postfix=""):

    print("Generating %s (%s::%s)" % (sql_file, table, column))
    with open(sql_file, 'w') as f:
        f.write(prefix)
        f.write("-- Replace event type GUIDs with hierarchical strings in {0}::{1}.\n".format(
            table, column))
        for plugin in EVENT_TYPES:
            f.write("\n")
            f.write("-- Metadata plugin \"{0}\".\n".format(plugin['pluginId']))
            for event_type in plugin['guids']:
                f.write("UPDATE {0} SET {1} = replace({1},\n".format(table, column))
                f.write("    '{0}', '{1}');\n".format(
                    guid_func(event_type['guid']), event_type['text']))
        f.write(postfix)


MSERVER_SQL_PREFIX = """\
-- Replace event type GUIDs with hierarchical strings in runtime_actions::event_subtype,
-- changing the column type from blob to string.

ALTER TABLE "runtime_actions" RENAME TO "runtime_actions_tmp";

CREATE TABLE "runtime_actions" (
    timestamp INTEGER NOT NULL,
    action_type SMALLINT NOT NULL,
    action_params TEXT,
    runtime_params TEXT,
    business_rule_guid BLOB(16),
    toggle_state SMALLINT,
    aggregation_count INTEGER,
    event_type SMALLINT,
    event_resource_GUID BLOB(16),
    action_resource_guid BLOB(16),
    event_subtype TEXT
);

-- Copy old table, changing event_subtype BLOB to hex string.
INSERT INTO "runtime_actions"
    SELECT
        timestamp,
        action_type,
        action_params,
        runtime_params,
        business_rule_guid,
        toggle_state,
        aggregation_count,
        event_type,
        event_resource_GUID,
        action_resource_guid,
        CASE
            WHEN event_subtype IS NULL THEN
                NULL
            ELSE
                lower('{' ||
                    substr(hex(event_subtype), 1, 8) || '-' ||
                    substr(hex(event_subtype), 9, 4) || '-' ||
                    substr(hex(event_subtype), 13, 4) || '-' ||
                    substr(hex(event_subtype), 17, 4) || '-' ||
                    substr(hex(event_subtype), 21) ||
                    '}')
        END
    FROM "runtime_actions_tmp";
    
"""


MSERVER_SQL_POSTFIX = """\

DROP TABLE "runtime_actions_tmp";
"""


# -------------------------------------------------------------------------------------------------
# Utils


def canonical_guid(guid):
    """Add braces (if missing) and convert to lower case.
    """
    if not guid.startswith('{'):
        guid = '{' + guid
    if not guid.endswith('}'):
        guid = guid + '}'
    return guid.lower()


def rename_key(self, old_key, new_key):
    for _ in range(len(self)):
        k, v = self.popitem(False)
        self[new_key if old_key == k else k] = v


OrderedDict.rename_key = rename_key


if __name__ == "__main__":
    main()
