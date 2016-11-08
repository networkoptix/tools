#!/bin/bash
sig=${1:-INT}
cat mrtsp.pids | while read p; do kill -$sig $p; echo $p; sleep 0.2; done
