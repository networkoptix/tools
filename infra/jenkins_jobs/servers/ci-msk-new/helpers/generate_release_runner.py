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
    'xccelo'
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

UNITTESTABLE = {
    'default': [
        'linux-x64',
        'windows-x64',
        'mac'
    ]
}

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
    max_concurrent_runners: 5 # default

    properties:
    - throttle:
        max-total: '{max_concurrent_runners}'
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
    - string:
        name: REPLACE_BUILD_WITH_NEWER
        default: 'NO'
    - p_PLATFORMS:
        default: '{default_platforms}'
    - p_CUSTOMIZATIONS:
        default: '{default_customizations}'
    - p_BUILD_WEBADMIN:
        default: true
    - p_BUILD_INSTALLER:
        default: true
    - p_RUN_UNITTESTS:
        default: true
    - p_RUN_FUNCTESTS:
        default: false
    - p_TEST_SELECT_EXPR:
        default: ''
    - p_TEST_LIST:
        default: ''
    - p_RUN_REALCAMERATESTS:
        default: false
    - p_BRANCH:
        default: '{default_branch}'
    - p_NX_VMS_COMMIT
    - p_BUILD_IDENTITY
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
    - string:
        name: NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT
    # TODO:
    # - string:
    #     name: NX_FUNCTESTS_COMMIT
    - string:
        name: ST_ENABLED
        default: 'NO'
    - string:
        name: ST_COMMIT
        default: ''

    wrappers:
    - timestamps
    - workspace-cleanup
    # note: DO NOT ADD any timeouts here. Put them in corresponding child jobs.

    builders:
    - set-custom-build-description
    # FIXME: remove when it will be unused
    - custom-build-description:
        envvars: [ BUILD_URL ]
        action: append
        target: upstream
        description: >-
          <br> <a href='$BUILD_URL'>to runner</a>
    - validate-required-params:
        params: >-
          NX_VMS_COMMIT
          BUILD_IDENTITY
    # FIXME: temp stub
    - inject:
        properties-content: |
          NX_FUNCTESTS_COMMIT=$NX_VMS_COMMIT
    - shell: |
        #!bash
        echo "NX_VMS_COMMIT=$NX_VMS_COMMIT" > NX_VMS_COMMIT.envvar
        echo "BUILD_IDENTITY=$BUILD_IDENTITY" > BUILD_IDENTITY.envvar
        echo "NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT=$NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT" > NX_VMS_REAL_CAMERA_TEST_FRAMEWORK_COMMIT.envvar
        echo "NX_FUNCTESTS_COMMIT=$NX_FUNCTESTS_COMMIT" > NX_FUNCTESTS_COMMIT.envvar

    # At this point we know BUILD_IDENTITY and NX_VMS_COMMIT
    # TODO: Should we fetch all links from publisher or something like that?
    - inject:
        properties-content: |
          JUNKSHOP_URL={junkshop_base_url}/project/{junkshop_project_name}/$BRANCH/$BUILD_IDENTITY
          REPOSITORY_URL={artifacts_base_url}/$PIPELINE/$BRANCH/$BUILD_IDENTITY
          REPOSITORY_ROOT_URL={artifacts_base_url}/$PIPELINE/$BRANCH/$BUILD_IDENTITY

    - build-name-setter:
        template: '#$BUILD_ID $BRANCH-$BUILD_IDENTITY@$NX_VMS_COMMIT'
        macro: true

    - description-setter:
        description: |
          $PLATFORMS $CUSTOMIZATIONS for $NX_VMS_COMMIT

    # TODO: remove this: unused
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

        # *.all job contains build and test, so if this particular platform & customization is not
        # unittestable at all, then we don't need to generate *.all that vontains only build..

        # The only difference in all and build params are RUN_UNITTESTS parameter
        if platform in UNITTESTABLE.get(customization, []):

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
        else:
            print '''
        - name: '{pipeline}.{version}.{project}.distribution.'''+platform+'''.'''+customization+'''.build'
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

# For now we test only default, so next 2 lines should be changed after other customizations added
# for customization in CUSTOMIZATIONS_LIST:
#     print '''
customization = 'default'
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
            NX_TEST_FRAMEWORK_COMMIT=$NX_FUNCTESTS_COMMIT
            TEST_LIST=$TEST_LIST
            TEST_SELECT_EXPR=$TEST_SELECT_EXPR
            CLEAN_WORKSPACE=$CLEAN_WORKSPACE
            CLEAN_BUILD=$CLEAN_BUILD
            CLEAN_CLONE=$CLEAN_CLONE
            RUNNER_URL=$BUILD_URL

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

        - name: '{pipeline}.{version}.{project}.distribution.'''+customization+'''.scalability-test'
          condition: COMPLETED # allow unstable
          kill-phase-on: NEVER
          enable-condition: >-
            ("$CUSTOMIZATIONS").trim().split(",").contains("'''+customization+'''") &&
            ("$ST_ENABLED").contains("ON")
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            ST_COMMIT=$ST_COMMIT
            CLEAN_WORKSPACE=true
            RUNNER_URL=$BUILD_URL

'''
print '''
    - shell: |
        #!bash
        echo "Wait a bit before scheduling reporting"
        echo "To be sure that all build/ut reporters are scheduled"
        sleep 10

    - multijob:
        name: Send notifications
        projects:
        - name: '{pipeline}.helper.build-notification'
          condition: ALWAYS
          predefined-parameters: |
            REQUESTED_BY=$JOB_NAME-$BUILD_NUMBER
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT
            RUNNER_URL=$BUILD_URL

    - multijob:
        name: Promote build for publishing via DepCon
        projects:
        - name: '{pipeline}.helper.promote-build'
          condition: SUCCESSFUL
          predefined-parameters: |
            BUILD_DESCRIPTION=$BUILD_DESCRIPTION
            BUILD_IDENTITY=$BUILD_IDENTITY
            BRANCH=$BRANCH
            NX_VMS_COMMIT=$NX_VMS_COMMIT

    publishers:
    - groovy-postbuild:
        script: !include-raw-escape: ../builders/report_all_links.groovy
    - display-upstream-changes
    - archive:
        artifacts: '*.envvar'
        allow-empty: 'false'
        fingerprint: true
    # - completed-email(group)
'''
