//
// Simple wrapper for starting processes that outputs logs into file plus stdout.
//
// Required variables
// EXECUTABLE                   - executable program to call
// EXECUTABLE_IS_RELPATH        - flag to mark that executable is relative to WORKSPACE (false)
// ARGUMENTS                    - comma-separated arguments to pass to executable
// INHERIT_ENVIRON              - flag to inherit environment variables
// ENVIRON                      - environment variables to set (override) for executable
//                              - comma-separeted key=value pairs
// LOGFILE                      - file in WORKSPACE where to put output text
// SUPPRESS_FAIL                - don't really fail. Just touch FAIL_FILE.
// FAIL_FILE                    - file to touch when fail is suppressed.


import groovy.time.TimeCategory
import groovy.time.TimeDuration

def env = System.getenv();

// Make $WORKSPACE resolved in string templates as it's commonly used var
def WORKSPACE = env.get("WORKSPACE")

def EXECUTABLE_IS_RELPATH = (env.get("EXECUTABLE_IS_RELPATH") ?: "false").toBoolean()

def EXECUTABLE = new File(env.get("EXECUTABLE")).toString()
if (EXECUTABLE_IS_RELPATH) {
    EXECUTABLE = new File( env.WORKSPACE, EXECUTABLE).toString()
}
def ARGUMENTS = []
def _arguments = env.get("ARGUMENTS")
if (_arguments && _arguments != "") {
    ARGUMENTS.addAll(_arguments.split(","))
}

def INHERIT_ENVIRON = (env.get("INHERIT_ENVIRON") ?: "false").toBoolean()
def ENVIRON = [:]
if (INHERIT_ENVIRON) {
    ENVIRON.putAll(env)
}
def _environ = (env.get("ENVIRON") ?: "")
if (_environ.trim() != "") {
    _environ.split(",").each {
        if (it.trim() != "") {
            kv = it.split("=")
            ENVIRON.put(kv[0], kv[1])
        }
    }
}

def WORKDIR = env.get("WORKDIR", env.WORKSPACE)
def LOGFILE = new File( env.WORKSPACE, env.get("LOGFILE", "output.log")).toString()

def COMMAND = [EXECUTABLE]
    COMMAND.addAll(ARGUMENTS)

def SUPPRESS_FAIL = (env.get("SUPPRESS_FAIL") ?: "false").toBoolean()
def FAIL_FILE = env.get("SUPPRESS_FAIL") ?: "fail"

def started_at = new Date()

println "=" * 80
println "Will run subprocess with following spec:"
println "Executable:     " + EXECUTABLE.toString()
println "Arguments:      " + ARGUMENTS.toString()
println "Command:        " + COMMAND.toString()
println "Workdir:        " + WORKDIR.toString()
println "Logfile:        " + LOGFILE.toString()
println "Environment:    "
ENVIRON.keySet().each {
    println ("    " + it + " = " + ENVIRON.get(it))
}
println "-" * 80
println "Started at:     " + started_at.toString()
println "-" * 80

ProcessBuilder pb = new ProcessBuilder(COMMAND)
pb.environment().putAll(ENVIRON)
pb.directory(new File(WORKDIR));
pb.redirectErrorStream(true)
Process process = pb.start()

InputStream stdout = process.getInputStream()
BufferedReader reader = new BufferedReader (new InputStreamReader(stdout))
def file = new File(LOGFILE)
while ((line = reader.readLine()) != null) {
    println line
    file << line
    file << "\n"
}
int excode = process.waitFor();
process.destroy();
println '-' * 80

def finished_at = new Date()
println "Finished at:    " + finished_at.toString()
println "Time taken:     " + TimeCategory.minus( finished_at, started_at ).toString()
println "Exit code:      " + excode.toString()
println '=' * 80
if (SUPPRESS_FAIL) {
    def fail_file = new File(FAIL_FILE)
    fail_file << "FAILED\n"
    System.exit(0);
} else {
    System.exit(excode);
}