import jenkins.model.Jenkins;
import hudson.model.Result;

// instance of hudson.model.FreeStyleBuild
// https://javadoc.jenkins.io/hudson/model/FreeStyleBuild.html
def currentBuild = Thread.currentThread().executable;

// instance of hudson.EnvVars
// https://javadoc.jenkins-ci.org/hudson/EnvVars.html
def env = currentBuild.getEnvVars();

def jobname  = env.get("JOB_NAME");
def canCancel = env.get("CANCEL_IN_FAV_OF_NEWER_BUILD", "false").toBoolean();

if ( canCancel ) {
    if ( Jenkins.instance.queue.items.any { it.task.name == jobname } ) {
        currentBuild.doStop()
        def description = build.getDescription().toString();
        currentBuild.setDescription(
            description +
            "<br>" +
            "ABORTED IN FAV OF NEWER BUILD"
        );
        currentBuild.@result = hudson.model.Result.ABORTED
    }
}
