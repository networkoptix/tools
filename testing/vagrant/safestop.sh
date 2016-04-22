#!/bin/sh
status "$1"|grep 'stop' || stop "$1"
