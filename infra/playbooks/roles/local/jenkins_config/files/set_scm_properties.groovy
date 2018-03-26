import jenkins.model.*

quiet_period = ${quiet_period}
scm_checkout_retry_count = ${scm_checkout_retry_count}

Jenkins j = Jenkins.instance
save = false

if(j.quietPeriod != quiet_period) {
  println "Current Jenkins Quiet Period is: " + j.quietPeriod.toString()
  println "Setting Jenkins Quiet Period to: " + quiet_period.toString()
  j.quietPeriod = quiet_period
  save = true
}

if(j.scmCheckoutRetryCount != scm_checkout_retry_count) {
  println "Current SCM checkout retry count is: " + j.scmCheckoutRetryCount.toString()
  println "Setting SCM checkout retry count to: " + scm_checkout_retry_count.toString()
  j.scmCheckoutRetryCount = scm_checkout_retry_count
  save = true
}

if(save) {
  j.save()
  println "Configuration changed"
} else {
  println "Configuration not changed"
}
