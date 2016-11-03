#!/bin/bash
cat mrtsp.pids | while read p; do kill -INT $p; echo $p; sleep 0.2; done
