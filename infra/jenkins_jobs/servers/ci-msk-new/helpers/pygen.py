# This is a helper utility to generate list of all sub jobs in multijob
for x in ("linux-x64 linux-x86 bananapi bpi rpi edge1 "
    "tx1 android-arm win-x64 win-x86 mac ios").split():
    for y in ("default default_cn default_zh_CN cox "
        "digitalwatchdog digitalwatchdog_global hanwha "
        "ipera ionetworks nutech ras senturian systemk "
        "tricom ust vista vmsdemoblue vmsdemoorange").split():

        # below is template for skipping non-desired intersections.
        # if x == "--1--" and y == "--2--": continue

        print '''
        - name: '{pipeline}.{branch}.vms.installer.'''+x+'''.'''+y+'''.all'
          kill-phase-on: NEVER
          enable-condition: >-
            ("$PLATFORM     ").trim().split(",").contains("'''+x+'''") &&
            ("$CUSTOMIZATION").trim().split(",").contains("'''+y+'''")
          predefined-parameters: |
            BUILD_IDENTITY=${counter_var_name}
            NX_VMS_COMMIT=$NX_VMS_COMMIT
        '''
