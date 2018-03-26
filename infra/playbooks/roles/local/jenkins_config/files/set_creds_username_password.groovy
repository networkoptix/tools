import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.CredentialsMatchers
import com.cloudbees.plugins.credentials.domains.SchemeRequirement
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.common.StandardUsernameCredentials

scope = "${scope}"
id = "${id}"
description = "${description}"
username = "${username}"
password = "${password}"

if (scope == "GLOBAL") {
  credsScope = CredentialsScope.GLOBAL
} else if (scope == "system") {
  credsScope = CredentialsScope.SYSTEM
}

credentials = new UsernamePasswordCredentialsImpl(
  credsScope,
  id,
  description,
  username,
  password
)

def availableCredentials = CredentialsProvider.lookupCredentials(
    StandardUsernameCredentials.class,
    Jenkins.getInstance(),
    hudson.security.ACL.SYSTEM,
    new SchemeRequirement("ssh")
)

def existingCredentials = CredentialsMatchers.firstOrNull(
  availableCredentials,
  CredentialsMatchers.withId(id)
)

def credentialsStore = Jenkins.instance.getExtensionList(
  'com.cloudbees.plugins.credentials.SystemCredentialsProvider'
)[0].getStore()

if(existingCredentials != null) {
  update = false
  if (existingCredentials.username != credentials.username) {
    update = true
  }
  if (existingCredentials.password != credentials.password) {
    update = true
  }
  if (existingCredentials.description != credentials.description) {
    update = true
  }
  if (update) {
    credentialsStore.updateCredentials(
      Domain.global(),
      existingCredentials,
      credentials
    )
    println "Configuration changed"
  } else {
    println "Configuration not changed"
  }

} else {
  credentialsStore.addCredentials(Domain.global(), credentials)
  println "Configuration changed"
}
