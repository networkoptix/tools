#!/bin/bash

HGRCPATH=/etc/mercurial/hgrc

cd "$( dirname "${BASH_SOURCE[0]}" )"

hg convert nx_vms_integrations nx_open_integrations --filemap=to_nx_open_integrations.filemap --sourcesort

cd nx_open_integrations; hg push -f || true
