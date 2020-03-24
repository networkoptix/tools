#!/bin/python2
# -*- coding: utf-8 -*-

import os
import jinja2

templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
templateFile = "index.html"


class Item:
    def __init__(self, src, frameTimestamp, metadataTimestamp):
        self.src = src
        self.frameTimestamp = frameTimestamp
        self.metadataTimestamp = metadataTimestamp
        

rootDir = "C:\\vdebug\\nx_rtp_parser"
rawDir = "raw"
overlayedDir = "overlayed"
outputFile = "parser.html"

def parseRaw(dirPath):
    rawItemList = []
    for filename in os.listdir(dirPath):
        split = filename.split(".")
        if len(split) != 2:
            continue
        item = Item(os.path.join(dirPath, filename), int(split[0]), 0)
        rawItemList.append(item)
    
    return rawItemList
    
    
def parseOverlayed(dirPath):
    overlayedItemList = []
    for filename in os.listdir(dirPath):
        split = filename.split(".")
        if len(split) != 2:
            continue
            
        timestampSplit = split[0].split("_")
        if len(timestampSplit) != 2:
            continue
            
        item = Item(os.path.join(dirPath, filename), int(timestampSplit[0]), int(timestampSplit[1]))
        overlayedItemList.append(item)
    
    return overlayedItemList
    
    
def parseMetadataFile(filePath):
    return []
    
def render(rawItemList, overlayedItemList):
    template = templateEnv.get_template(templateFile)
    output = template.render(rawItems=rawItemList, overlayedItems=overlayedItemList)
    with open(outputFile, "wb") as f:
        f.write(output)
        
def main():
    raw = parseRaw(os.path.join(rootDir, rawDir))
    overlayed = parseOverlayed(os.path.join(rootDir, overlayedDir))
    render(raw, overlayed)
    
if __name__ == "__main__":
    main()
        
        
