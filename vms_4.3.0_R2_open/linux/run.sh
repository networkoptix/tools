#!/bin/bash

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./conan/data/hidapi/0.10.1/_/_/package/312cfb0686778c8adc6913601d8a994200ab257c/lib
                                           
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:./packages/linux_x64/intel-media-sdk-19.4.0/lib

../nx-open-build-linux_x64/bin/metavms_client
