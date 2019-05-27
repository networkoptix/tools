#!/bin/bash -e

PACKAGE_DIR="$1"
CLOUD_HOSTS_FILE="${PACKAGE_DIR}/cloud_hosts.json"
CLOUD_HOSTS_FILE_TMP="/tmp/cloud_hosts.json.tmp"
URL="http://s3.ireg.hdw.mx/cloud_hosts.json"

[[ ! -d $PACKAGE_DIR ]] && mkdir -p "$PACKAGE_DIR"

curl "$URL" -o "$CLOUD_HOSTS_FILE_TMP"
diff -q "$CLOUD_HOSTS_FILE" "$CLOUD_HOSTS_FILE_TMP" && exit

cp "$CLOUD_HOSTS_FILE_TMP" "$CLOUD_HOSTS_FILE"

cat >"$PACKAGE_DIR/.rdpack" <<EOL
[General]
time = $(date '+%s')
uploader = "Cloud Hosts Auto Update Script on $HOSTNAME"
EOL
