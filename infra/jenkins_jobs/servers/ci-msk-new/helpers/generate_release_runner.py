#!/usr/bin/env python

# This is a helper utility to generate list of all sub jobs in multijob
# usage: generate_release_runner.py > ../templates/runner.yaml

CUSTOMIZATIONS_LIST = [
    'default',
    'default_cn',
    'default_zh_CN',
    'cox',
    'digitalwatchdog',
    'digitalwatchdog_global',
    'hanwha',
    'ipera',
    'ionetworks',
    'nutech',
    'ras',
    'senturian',
    'systemk',
    'tricom',
    'ust',
    'vista',
    'vmsdemoblue',
    'vmsdemoorange',
    'metavms',
    'xcello'
]

PLATFORMS_LIST = [
    'linux-x64',
    'linux-x86',
    'bananapi',
    'bpi',
    'rpi',
    'edge1',
    'tx1',
    'android-arm',
    'windows-x64',
    'windows-x86',
    'mac',
    'ios'
]

print '''#
# DO NOT EDIT THIS TEMPLATE MANUALLY
# This configuration is autogenerated by helper script '../helpers/generate_release_runner.py'.
#
- job-template:
    name: '{pipeline}.{version}.{project}.runner'
    project-type: multijob
    description: |
      Entry point

    node: runner
    concurrent: true

    realcameratesting-framework-branch: $BRANCH

    properties:
    - throttle:
        max-total: 5
        option: project
    - build-discarder:
        days-to-keep: 30
        num-to-keep: 100
        artifact-days-to-keep: 30
        artifact-num-to-keep: 100

    parameters:
    - p_REQUESTED_BY
    - p_UPSTREAM_JOB_NAME
    - p_BUILD_DESCRIPTION:
        default: ''
    - p_PLATFORMS:
        default: '{default-platforms}'
    - p_CUSTOMIZATIONS:
        default: '{default-customizations}'
    - p_BUILD_WEBADMIN:
        default: true
    - p_BUILD_INSTALLER:
        default: true
    - p_RUN_UNITTESTS:
        default: true
    - p_RUN_FUNCTESTS:
        default: false
    - p_RUN_REALCAMERATESTS:
        default: false
    - p_BRANCH:
        default: '{default_branch}'
    - p_USE_NX_VMS_COMMIT:
        default: '{default_branch}'
    - p_USE_BUILD_IDENTITY:
        default: NEW
    - p_CLEAN_WORKSPACE:
        default: false
    - p_CLEAN_BUILD:
        default: false
    - p_CLEAN_CLONE
    - p_CLOUD_GROUP:
        default: test
    - p_HARDWARE_SIGNING:
        default: 'OFF'
    - p_TRUSTED_TIMESTAMPING:
        default: 'OFF'
    - p_CUSTOM_CMAKE_PARAMETERS:
        default: ''
    - p_PIPELINE(hidden):
        default: '{pipeline}'

    wrappers:
    - timestamps
    # note: DO NOT ADD any timeouts here. Put them in corresponding child jobs.

    builders:
    - set-custom-build-description
    - custom-build-description:
        envvars: [ BUILD_URL ]
        action: append
        target: upstream
        description: >-
          <br> <a href='$BUILD_URL'>to runner</a>

    # inject as is
    - inject:
        properties-content: |
          BUILD_IDENTITY=$USE_BUILD_IDENTITY
          NX_VMS_COMMIT=$USE_NX_VMS_COMMIT

    # if it's auto, get from existing build
    - conditional-step:
        condition-kind: strings-match
        condition-string1: '${{NX_VMS_COMMIT}}'
        condition-string2: 'AUTO'
        steps:
        # Note, that we don't want to copy BUILD_IDENTITY. because we don't want
        # to override the one that came from args

        - copyartifact:
            project: '{pipeline}.{version}.{project}.register-build'
            filter: 'NX_VMS_COMMIT.envvar'
            which-build: last-successful
            parameter-filters: >-
              BUILD_IDENTITY=$USE_BUILD_IDENTITY
            optional: false
        - inject:
            properties-file: 'NX_VMS_COMMIT.envvar'

    # Freeze nx realcamera framework commit
    - freeze-nx-vms-commit(remote):
        pipeline: '{pipeline}'
        branch: '{realcameratesting-framework-branch}'
        commit-to-freeze: '{realcameratesting-framework-branch}'
        commit-varname: NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT

    # Build identity may be defained in args, or use NEW keqyword,
    # which means that we need to create one..
    - conditional-step:
        condition-kind: strings-match
        condition-string1: '${{USE_BUILD_IDENTITY}}'
        condition-string2: 'NEW'
        steps:
        - multijob:
            name: Request new release build id
            projects:
            - name: '{pipeline}.build_number.generator'
              kill-phase-on: FAILURE
              predefined-parameters: |
                REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
                BUILD_DESCRIPTION=$BUILD_DESCRIPTION
        - copyartifact:
            project: '{pipeline}.build_number.generator'
            filter: 'BUILD_IDENTITY.envvar'
            which-build: last-completed
            parameter-filters: REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
        - inject:
            properties-file: 'BUILD_IDENTITY.envvar'

    # At this point we know BUILD_IDENTITY and NX_VMS_COMMIT
    # TODO: Should we fetch all links from publisher or something like that?
    - inject:
        properties-content: |
          JUNKSHOP_HOST={junk_shop_host}
          JUNKSHOP_DB_HOST={junkshop_db_host}
    - inject:
        properties-content: |
          JUNKSHOP_PROJECT_NAME={junkshop_project_name}
    - inject:
        properties-content: |
          JUNKSHOP_BASE_URL=http://$JUNKSHOP_HOST
    - inject:
        properties-content: |
          JUNKSHOP_URL=$JUNKSHOP_BASE_URL/{junkshop_location_root_pattern}
          REPOSITORY_URL={artifact_repository_base_url}/{artifact_location_root_pattern}
          REPOSITORY_ROOT_URL={artifact_repository_base_url}/{artifact_location_root_pattern}

    - build-name-setter:
        template: '#$BUILD_ID $BRANCH-$BUILD_IDENTITY@$NX_VMS_COMMIT'
        macro: true

    - description-setter:
        description: |
          $PLATFORMS $CUSTOMIZATIONS for $NX_VMS_COMMIT ($USE_NX_VMS_COMMIT)

    # At this step we will register id->commit or fail if we have wrong commit for this id.
    - build-registry-add:
        pipeline: '{pipeline}'
        version: '{version}'
        branch: $BRANCH
        project: '{project}'
        build-identity: $BUILD_IDENTITY
        nx-vms-commit: $NX_VMS_COMMIT

    # TODO: we don't need to build webadmin for macOS. But it's not enough to disable it here
    # because artifact is mandatory in build installers.
    - multijob:
        name: Build web admin
        projects:
        - name: '{pipeline}.{version}.{project}.webadmin.universal.build'
          enable-condition: >-
            ("$BUILD_WEBADMIN").toBoolean()
          kill-phase-on: FAILURE
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            CLEAN_WORKSPACE=$CLEAN_WORKSPACE
            CLEAN_BUILD=$CLEAN_BUILD
            CLEAN_CLONE=$CLEAN_CLONE
            RUNNER_URL=$BUILD_URL

    - multijob:
        name: Run all VMS distribution related jobs
        condition: COMPLETED # allow unstable
        projects:'''

for platform in PLATFORMS_LIST:
    for customization in CUSTOMIZATIONS_LIST:

        # below is template for skipping non-desired intersections.
        # if platform == "--1--" and customization == "--2--": continue

        if platform == "edge1" and customization != "digitalwatchdog":
            continue
        # TODO: ios and android have own release cycles and branches, need to extract in other project
        # if platform in ['ios', 'android-arm']:
        #     continue

        print '''
        - name: '{pipeline}.{version}.{project}.distribution.'''+platform+'''.'''+customization+'''.all'
          kill-phase-on: NEVER
          enable-condition: >-
            ("$PLATFORMS     ").trim().split(",").contains("'''+platform+'''") &&
            ("$CUSTOMIZATIONS").trim().split(",").contains("'''+customization+'''") &&
            ("$BUILD_INSTALLER").toBoolean()
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            CUSTOM_CMAKE_PARAMETERS=$CUSTOM_CMAKE_PARAMETERS
            CLEAN_WORKSPACE=$CLEAN_WORKSPACE
            CLEAN_BUILD=$CLEAN_BUILD
            CLEAN_CLONE=$CLEAN_CLONE
            RUN_UNITTESTS=$RUN_UNITTESTS
            RUNNER_URL=$BUILD_URL
            CLOUD_GROUP=$CLOUD_GROUP
            HARDWARE_SIGNING=$HARDWARE_SIGNING
            TRUSTED_TIMESTAMPING=$TRUSTED_TIMESTAMPING
'''
print '''
    - multijob:
        name: Run all VMS distribution functional tests
        projects:
'''

for customization in CUSTOMIZATIONS_LIST:
    print '''
        - name: '{pipeline}.{version}.{project}.distribution.'''+customization+'''.functest'
          condition: COMPLETED # allow unstable
          kill-phase-on: NEVER
          enable-condition: >-
            ("$CUSTOMIZATIONS").trim().split(",").contains("'''+customization+'''") &&
            ("$RUN_FUNCTESTS").toBoolean()
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            NX_TEST_FRAMEWORK_COMMIT=$NX_VMS_COMMIT
            CLEAN_WORKSPACE=$CLEAN_WORKSPACE
            CLEAN_BUILD=$CLEAN_BUILD
            CLEAN_CLONE=$CLEAN_CLONE
            RUNNER_URL=$BUILD_URL
            JUNKSHOP_HOST=$JUNKSHOP_HOST
            JUNKSHOP_DB_HOST=$JUNKSHOP_DB_HOST

        - name: '{pipeline}.{version}.{project}.distribution.'''+customization+'''.realcameratest'
          condition: COMPLETED # allow unstable
          kill-phase-on: NEVER
          enable-condition: >-
            ("$CUSTOMIZATIONS").trim().split(",").contains("'''+customization+'''") &&
            ("$RUN_REALCAMERATESTS").toBoolean()
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            NX_TEST_FRAMEWORK_COMMIT=$NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT
            CLEAN_WORKSPACE=$CLEAN_WORKSPACE
            CLEAN_BUILD=$CLEAN_BUILD
            CLEAN_CLONE=$CLEAN_CLONE
            RUNNER_URL=$BUILD_URL
            JUNKSHOP_HOST=$JUNKSHOP_HOST
            JUNKSHOP_DB_HOST=$JUNKSHOP_DB_HOST
'''
print '''
    publishers:
    - groovy-postbuild:
        script: !include-raw-escape: ../builders/report_all_links.groovy
    - display-upstream-changes
    - archive:
        artifacts: '*.envvar'
        allow-empty: 'false'
        fingerprint: true
    - completed-email(group)
'''
