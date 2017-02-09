#!/bin/bash

TARGET=/usr/share/nginx/xslt/dirlist.xslt
sudo mv $TARGET $TARGET.bak
sudo cp ./dirlist.xslt $TARGET
sudo nginx -s reload
