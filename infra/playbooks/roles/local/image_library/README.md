**DEPRECATED**

This role was used before we introduced centralized image library.

Right now there is no need to download images from internet or build
them locally on each host anymore.
Instead, NAS should be used as source for base images.

Packing windows machine should be extracted from this role into special
project or another role that will be related to creation of base images only.
