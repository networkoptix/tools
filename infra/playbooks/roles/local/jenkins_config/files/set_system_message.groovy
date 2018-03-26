import jenkins.model.*

system_message = "${system_message}"

Jenkins j = Jenkins.instance
save = false

if(j.systemMessage != system_message) {
  println "Current SysMessage is: " + j.systemMessage.toString()
  println "Setting SysMessage to: " + system_message.toString()
  j.systemMessage = system_message
  save = true
}

if(save) {
  j.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
