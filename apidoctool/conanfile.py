#!/usr/bin/env python

from conans import ConanFile, tools

class ApiDocToolConan(ConanFile):
    name = "apidoctool"
    version = "2.1"
    description = "Parses Apidoc comments in C++ code and generates api.xml"
    exports_sources = "*"

    def system_requirements(self):
        if tools.os_info.is_windows:
            return

        installer = tools.SystemPackageTool()
        installer.install("gradle", update=False)

    def build(self):
        self.run("gradle build")

    def package(self):
        self.copy("apidoctool.jar", dst="", src="build/libs")
