// modified example from https://stackoverflow.com/a/35158578/1243636

import hudson.FilePath
import java.io.InputStream

def build = Thread.currentThread().executable

def unstable = false;
if(build.workspace.isRemote()) {
    channel = build.workspace.channel;
    fp = new FilePath(channel, build.workspace.toString() + "/unstable.flag")
    if (fp.exists()) {
      unstable = true;
    }
} else {
    fp = new FilePath(new File(build.workspace.toString() + "/unstable.flag"))
    if (fp.exists()) {
      unstable = true;
    }
}

manager.listener.logger.println("Build unstable? " + unstable.toString())
if (unstable) {
    manager.listener.logger.println('setting build to unstable')
    manager.buildUnstable()
}