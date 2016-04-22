#!/bin/bash
date --set=@$((`date +%s` + $1))

