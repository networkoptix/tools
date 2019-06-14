#!/bin/bash

HGRCPATH=/etc/mercurial/hgrc

cd "$( dirname "${BASH_SOURCE[0]}" )"

hg convert nx_vms nx_open --filemap=to_nx_open.filemap --sourcesort --config convert.hg.saverev=True --config convert.hg.startrev=7dd2a70974b3

cd nx_open; hg push -f || true
