import jenkins.model.*

admin_email = "${admin_email}"

Jenkins j = Jenkins.instance
JenkinsLocationConfiguration l = j.getExtensionList('jenkins.model.JenkinsLocationConfiguration')[0]
save = false

if(l.adminAddress != admin_email) {
  println "Current Admin Email is: " + l.adminAddress.toString()
  println "Setting Admin Email to: " + admin_email.toString()
  l.adminAddress = admin_email
  save = true
}

if(save) {
  l.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
