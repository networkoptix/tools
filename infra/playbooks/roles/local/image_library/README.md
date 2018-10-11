**DEPRECATED**

This role was used before we introduced centralized image library.

Right now there is no need to download images from internet or build
them locally on each host anymore.
Instead, NAS should be used as source for base images.

Packing windows machine should be extracted from this role into special
project or another role that will be related to creation of base images only.


### VisualStudio notes

Sometimes our developers got issues with VS C++ compiler (compiler bugs related to C++17 features).
In such cases, they usually just switch to latest VS version. There're some useful commands to do that:
* Upgrade by chocolate:
```commandline
C:\> choco upgrade visualstudio2017community
```
* Upgrade by vs_installershell.exe. For more details, please, see
https://docs.microsoft.com/en-us/visualstudio/install/command-line-parameter-examples?view=vs-2017:
```commandline
C:\> "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installershell.exe" update --quiet --installpath "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community"
```
