#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
List of artifacts that must be published
See: https://networkoptix.atlassian.net/wiki/display/SD/Installer+Filenames
"""
samples = ["nxwitness-client-3.0.0.13804-linux86-beta-test.deb",
            "nxwitness-client-3.0.0.13804-linux86-beta.tar.gz",
            "nxwitness-client-3.0.0.13804-linux86-test.zip",
            "nxwitness-client-3.0.0.13804-linux86.msi"]
            
class Artifact():
    BETA = "beta"
    def __init__(self, name):
        self.name = name
        # parsing rule {product}-{apptype}-{version}-{platform}-{optional:beta_status}-{optional:cloud_instance_group}.{extension}
        parts = name.split('-')
        last = parts[-1]
        parts.pop()
        last, sep, self.extension = last.partition('.')
        parts.append(last)

        nargs = len(parts)
        assert(4 <= nargs <= 6)

        self.product = parts[0]
        self.apptype = parts[1]
        self.version = parts[2]
        self.platform = parts[3]
        self.beta = False
        self.cloud = ""

        if nargs < 5:
            return

        option = parts[4]
        self.beta = option == Artifact.BETA
        if nargs == 6:
            assert(self.beta)
            self.cloud = parts[5]
        else:
            self.cloud = option if not self.beta else ""


def get_artifacts(customization, cloud, beta):
    print customization

if __name__ == '__main__':
    get_artifacts("default", "test", True)
    sys.exit(0)