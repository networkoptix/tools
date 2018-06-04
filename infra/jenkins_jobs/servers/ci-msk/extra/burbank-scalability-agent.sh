#!/bin/bash -xe

# usage: <this-script>.sh <slave-ip-addr-or-host-name>

SLAVE_HOST="$1"

# actual address of junk-shop postgres database on alphabet (moscow ci servers rack)
JUNK_SHOP_DB_HOST=10.0.0.113


AGENT_FNAME=$(basename "$AGENTJAR_URL")

pwd

cd /tmp

rm "$AGENT_FNAME" || true

wget --no-verbose "$AGENTJAR_URL"
echo "WORKSPACE=[$WORKSPACE]"
scp "$AGENT_FNAME" "$SLAVE_HOST:$WORKSPACE"

ssh -R 5432:$JUNK_SHOP_DB_HOST:5432 "$SLAVE_HOST" java -jar "$WORKSPACE/$AGENT_FNAME"
