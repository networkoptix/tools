#!/bin/bash
key=~/.vagrant.d/insecure_private_key
dest="$1"
shift
if [ -z "$dest" ]; then
	echo Usage:
	echo "$0" ADDRESS-AND-PATH [SCP-PARAMS] FILES
	echo "(Note, the destination is the first. Don't forget to use : even with no path after address)"
	exit 1
fi
scp -B -q -o Compression=yes -o DSAAuthentication=yes -o LogLevel=ERROR -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -i "$key" "$@" "vagrant@$dest"
