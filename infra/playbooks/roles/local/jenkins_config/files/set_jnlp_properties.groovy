import jenkins.model.*

jnlp_slave_port = ${jnlp_slave_port}

Jenkins j = Jenkins.instance
save = false

if(j.slaveAgentPort != jnlp_slave_port) {
  println "Current jnlp port is: " + j.slaveAgentPort.toString()
  println "Setting jnlp port to: " + jnlp_slave_port.toString()
  if(jnlp_slave_port <= 65535 && jnlp_slave_port >= -1) {
    j.slaveAgentPort = jnlp_slave_port
    save = true
  }
  else {
    println "ERROR: JNLP port ${jnlp_slave_port} outside of TCP port range.  Must be within -1 <-> 65535.  Nothing changed."
  }
}

if(save) {
  j.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
