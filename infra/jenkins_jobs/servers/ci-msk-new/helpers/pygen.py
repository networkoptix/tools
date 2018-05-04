# This is a helper utility to generate list of all sub jobs in multijob
for platform in ("linux-x64 linux-x86 bananapi bpi rpi edge1 "
    "tx1 android-arm win-x64 win-x86 mac ios").split():
    for customization in ("default default_cn default_zh_CN cox "
        "digitalwatchdog digitalwatchdog_global hanwha "
        "ipera ionetworks nutech ras senturian systemk "
        "tricom ust vista vmsdemoblue vmsdemoorange").split():

        # below is template for skipping non-desired intersections.
        # if platform == "--1--" and customization == "--2--": continue

        if platform == "edge1" and customization != "digitalwatchdog": continue

        print '''
        - name: '{pipeline}.{branch}.vms.installer.'''+platform+'''.'''+customization+'''.all'
          kill-phase-on: NEVER
          enable-condition: >-
            ("$PLATFORM     ").trim().split(",").contains("'''+platform+'''") &&
            ("$CUSTOMIZATION").trim().split(",").contains("'''+customization+'''")
          predefined-parameters: |
            BUILD_IDENTITY=${counter_var_name}
            NX_VMS_COMMIT=$NX_VMS_COMMIT
        '''
