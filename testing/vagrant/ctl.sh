#!/bin/bash
# Pre- and post-test mediaserver control script.
# Restarts server, changes it's config, clear unnecessary data and so on
# $1 - test name
# $2 - mode (init, clear, ...)
. /vagrant/conf.sh
testName=$1
mode=$2
shift 2

echo STARTED: ctl.sh $testName $mode $@

debugLevel=DEBUG
# possible values -- names of log level or number for case in setLogLevel function

#:set -x

function setLogLevel {
    case "$1" in
        0)
            level=
            ;;
        1)
            level=DEBUG
            ;;
        2)
            level=DEBUG2
            ;;
        *)
            level=$1
    esac
    nxedconf logLevel "$level"
    nxedconf http-log-level "$level"
}

function legacy_ctl {
    case "$mode" in
        clear)
            nxcleardb
    esac
}

function timesync_ctl {
    case "$mode" in
        init)
            echo '*** STOPPING NTPD ***'
            service ntp stop
            nxcleardb
            setLogLevel DEBUG2
            /sbin/ifdown $EXT_IF > /dev/null
            # make it non-executable to disable ntpd start when eth0 goes up:
            chmod -x /etc/network/if-up.d/ntpdate
            date --set=@$1
            ;;
        prepare_isync)
            safestop "$SERVICE"
            echo configuring inet sync
            /sbin/ifdown $EXT_IF > /dev/null
            date --set=@$1
            nxcleardb
            # values should be less than INET_SYNC_TIMEOUT in timetest.py
            nxedconf ecInternetSyncTimePeriodSec 12
            nxedconf ecMaxInternetTimeSyncRetryPeriodSec 12
            #safestart "$SERVICE"
            ;;
        clear)
            chmod +x /etc/network/if-up.d/ntpdate
            /etc/network/if-up.d/ntpdate
            date --set=@$1
            nxcleardb
            ;;
        *) echo "Unknown mode '${mode}' for timesync test control"
    esac
}

function bstorage_ctl {
    case "$mode" in
        init)
            nxcleardb
            setLogLevel $debugLevel
            ;;
        clear)
            # Clears the main and the backaup storages, passed as $1 and $2
            nxrmbase "$1"
            nxrmbase "$2"
            nxcleardb
            ;;
        rmstorage)
            nxrmbase "$1"
            ;;
        *) echo "Unknown mode '${mode}' for bstorage test control"
    esac
}

function msarch_ctl {
    case "$mode" in
        init)
            nxcleardb
            setLogLevel $debugLevel
            ;;
        clear)
            # Clears the main storage, passed as $1, and restore the system name
            nxrmbase "$1"
            nxcleardb
            edconf systemName "$MAIN_SYS_NAME"
            ;;
        *) echo "Unknown mode '${mode}' for msarch test control"
    esac
}

function stream_ctl {
    case "$mode" in
        init)
            nxcleardb
            setLogLevel $debugLevel
            ;;
        clear)
            # Clears the main storage, passed as $1, and restore the system name
            nxrmbase "$1"
            nxcleardb
            ;;
        *) echo "Unknown mode '${mode}' for stream test control"
    esac
}

function natcon_ctl {
    case "$mode" in
        init)
            nxcleardb
            setLogLevel $debugLevel
            ;;
        clear)
            nxrmbase "$1"
            nxcleardb
            ;;
        *) echo "Unknown mode '${mode}' for natcon test control"
    esac
}

function db_ctl {
    case "$mode" in
        init)
            cp "/vagrant/$1" "$SERVDIR/var/ecs.sqlite"
            nxedconf removeDbOnStartup 0  `# we DO NOT need to clear DB on startup, so make sure it do not`
            nxedconf serverGuid "$2"
            nxedconf guidIsHWID no
            nxedconf tranLogLevel DEBUG
            cp "$SERVCONF" "$SERVCONF.copy"
            setLogLevel $debugLevel
            ;;
        clear)
            # nxcleardb  # not used, this test doesn't call clear
            ;;
        *) echo "Unknown mode '${mode}' for dbup test control"
    esac
}

################################################################################################

case "$mode" in
    init)
        test -e "${SERVCONF}.orig" && cp "${SERVCONF}.orig" "$SERVCONF"
        ;;
    clear)
        safestop "$SERVICE"
        ;;
esac

case "$testName" in
    legacy)
        legacy_ctl "$@"
        ;;
    timesync)
        timesync_ctl "$@"
        ;;
    bstorage)
        bstorage_ctl "$@"
        ;;
    msarch)
        msarch_ctl "$@"
        ;;
    stream|hlso)
        stream_ctl "$@"
        ;;
    natcon)
        natcon_ctl "$@"
        ;;
    db)
        db_ctl "$@"
        ;;
    *)
        echo Unknown test name "$testName"
        exit 1
esac

case "$mode" in
    init)
        safestart "$SERVICE"
        ;;
esac

