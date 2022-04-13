from conans import ConanFile, tools
import os
import sys


class CustomizationConan(ConanFile):
    name = "customization"
    version = "1.0"
    description = "Zip package for customization assets."
    options = {
        "customization": "ANY",
    }
    default_options = {
        "customization": "default",
    }
    exports_sources = "get_zip_from_cloud.py"

    def build(self):
        sys.path.append(".")
        import get_zip_from_cloud

        get_zip_from_cloud.main([
            os.getenv("CMS_PULLER_USERNAME"),
            os.getenv("CMS_PULLER_PASSWORD"),
            "type",
            f"--customization={self.options.customization}",
        ])

    def package(self):
        self.copy("package.zip", dst="", src=f"customization_pack-{self.options.customization}")
