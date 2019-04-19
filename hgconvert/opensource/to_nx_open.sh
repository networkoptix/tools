#!/bin/bash

HGRCPATH=/etc/mercurial/hgrc

cd "$( dirname "${BASH_SOURCE[0]}" )"

hg convert nx_vms nx_open --filemap=to_nx_open.filemap --sourcesort

cd nx_open; hg push -f || true
