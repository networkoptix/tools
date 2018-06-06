// FIXME: Add description and interface declaration
import groovy.time.TimeCategory
import groovy.time.TimeDuration

def env = System.getenv();


def EXECUTABLE = new File(env.get("CMAKE_EXECUTABLE")).toString()

def ARGUMENTS = []
def ENVIRON = [:]

def CMAKE_BUILD_THREADS = (env.get("CMAKE_BUILD_THREADS") ?: "20")
def GENERATOR = (env.get("CMAKE_GENERATOR") ?: "")
// FIXME: This binding is probably incorrect, but it looks like we pick correct value here
def CMAKE_BUILD_TYPE = (env.get("CMAKE_ARG_CMAKE_BUILD_TYPE") ?: "Release")

ARGUMENTS.addAll(["--build", ".", "--config", CMAKE_BUILD_TYPE.capitalize()])

if (GENERATOR == "Ninja") {
    ARGUMENTS.addAll( ["--", "-j", CMAKE_BUILD_THREADS])
} else {
    ARGUMENTS.addAll([])
}

// Build environ
def INHERIT_ENVIRON = (env.get("INHERIT_ENVIRON") ?: "false").toBoolean()
if (INHERIT_ENVIRON) {
    ENVIRON.putAll(env)
}

def CMAKE_ENV_PREFIX = "CMAKE_ENV_"
env.each { key, val ->
    if (key.startsWith(CMAKE_ENV_PREFIX)  && val.trim() != "") {
        def keyname = key.substring(CMAKE_ENV_PREFIX.length())
        // drop quotes
        def value = val.replaceAll('^"|"$', "")
        ENVIRON.put(keyname, value)
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
