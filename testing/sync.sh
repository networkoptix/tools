#!/bin/bash
NX_RSYNC_SOURCE=${NX_RSYNC_SOURCE:-noptix.enk.me}
DIR=${NX_VAGRANT_DIR:-vagrant}
test -d "$DIR" || mkdir "$DIR"
#pushd $environment && rsync -av --delete rsync://$NX_RSYNC_SOURCE/buildenv/linux/test .
rsync -av --delete rsync://$NX_RSYNC_SOURCE/buildenv/test/sample.mkv "$DIR"

