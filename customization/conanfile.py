#!/usr/bin/env python

from conans import ConanFile, tools
import os
import sys

class CustomizationPackConan(ConanFile):
    name = "customization_pack"
    version = "1.0"
    description = "Zip package for customization assets."
    url = "https://cloud-test.hdw.mx"
    exports_sources = "*"
    options = {
        "customization": "ANY",
        "draft": [True, False],
    }
    default_options = {
        "customization": "default",
        "draft": False,
    }

    def build(self):
        sys.path.append(".")
        import get_zip_from_cloud

        username = os.getenv("CMS_PULLER_USERNAME")
        password = os.getenv("CMS_PULLER_PASSWORD")

        arguments = [
            username,
            password
        ]

        if self.options.draft:
            arguments.append("--draft")

        arguments += [
            "type",
            "--customization=" + str(self.options.customization),
        ]

        get_zip_from_cloud.main(arguments)

    def package(self):
        self.copy("package.zip", dst="", src=f"customization_pack-{self.options.customization}")
