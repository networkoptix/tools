#!/bin/sh
status "$1"|grep 'start' || start "$1"
