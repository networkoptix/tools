C:\ProgramData\chocolatey\choco.exe install -y jdk8 --version 8.0.162

# FIXME: Need to find version&build programmatically instead of hardcoded
setx PATH "%PATH%;C:\Program Files\Java\jdk1.8.0_162\bin"
setx JAVA_HOME "C:\Program Files\Java\jdk1.8.0_162"
