import jenkins.model.*

master_executors = ${master_executors}
master_labels = "${master_labels}"
master_usage = "${master_usage}"

Jenkins j = Jenkins.instance
save = false

if(j.numExecutors != master_executors) {
  println "Current master num executors is: " + j.numExecutors.toString()
  println "Setting master num executors to: " + master_executors.toString()
  j.numExecutors = master_executors
  save = true
}

if(j.labelString != master_labels) {
  println "Current master labels is: " + j.labelString.toString()
  println "Setting master labels to: " + master_labels.toString()
  j.setLabelString(master_labels)
  save = true
}

if(j.mode.toString() != master_usage) {
  println "Current master usage is: " + j.mode.toString()
  println "Setting master usage to: " + master_usage.toString()
  j.mode = Node.Mode."${master_usage}"
  save = true
}

if(save) {
  j.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
