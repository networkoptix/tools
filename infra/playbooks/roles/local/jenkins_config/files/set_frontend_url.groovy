import jenkins.model.*

frontend_url = "${frontend_url}"

Jenkins j = Jenkins.instance
JenkinsLocationConfiguration l = j.getExtensionList('jenkins.model.JenkinsLocationConfiguration')[0]
save = false

if(l.url != frontend_url) {
  println "Current URL is: " + l.url.toString()
  println "Setting URL to: " + frontend_url.toString()
  l.url = frontend_url
  save = true
}

if(save) {
  l.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
