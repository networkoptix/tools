#!/bin/bash

CONFIG=$1

BIN="$HOME"/taskbot/devtools/taskbot/core/
PRNENV="$BIN"/prnenv.py

if [ "x$CONFIG" = "x" ]
then
    echo "Config file isn't defined" > /dev/stderr && exit 1
fi

TASKBOT_CONFIG=$(realpath $CONFIG)

# Set taskbot environment
eval $($PRNENV $TASKBOT_CONFIG)

echo "Create 'test' user"
echo "You have to login as root to NX1..."
CMD=$(cat << EOF
id test >/dev/null 2>&1
if [ \$? != 0 ]; then
  echo "Create user 'test' and set password..."
  useradd test -m --shell /bin/bash
  passwd test 
fi
echo "core.%p" > /proc/sys/kernel/core_pattern
[ ! -f /etc/sysctl.conf.backup ] && cp /etc/sysctl.conf /etc/sysctl.conf.backup
if [ ! \$(grep "kernel.core_pattern=" /etc/sysctl.conf) ]; then
  echo  >> /etc/sysctl.conf
  echo "kernel.core_pattern=core.%p" >> /etc/sysctl.conf
else
  sed -r 's|^.*kernel.core_pattern=(.*)$|kernel.core_pattern=core.%p|' /etc/sysctl.conf > /tmp/sysctl.conf
  mv /tmp/sysctl.conf /etc/sysctl.conf
fi
EOF
)
ssh -tt root@$TASKBOT_NX1_ADDRESS "$CMD"

echo "Copy SSH keys for user 'test'"
echo "You have to login as 'test' to NX1..."
ssh-copy-id test@$TASKBOT_NX1_ADDRESS
