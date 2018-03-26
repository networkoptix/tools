import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.CredentialsMatchers
import com.cloudbees.plugins.credentials.domains.SchemeRequirement
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.common.StandardUsernameCredentials
import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey

scope = "${scope}"
id = "${id}"
description = "${description}"
username = "${username}"
passphrase = "${pass_phrase}"
privateKey = """${private_key}"""

keySource = new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(privateKey)

if (scope == "GLOBAL") {
  credsScope = CredentialsScope.GLOBAL
} else if (scope == "system") {
  credsScope = CredentialsScope.SYSTEM
}

credentials = new BasicSSHUserPrivateKey(
  credsScope,
  id,
  username,
  keySource,
  passphrase,
  description
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
  if (existingCredentials.getPrivateKey() != credentials.getPrivateKey()) {
    update = true
  }
  if (existingCredentials.passphrase != credentials.passphrase) {
    update = true
  }
  if (existingCredentials.description != credentials.description) {
    update = true
  }
  if (update){
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
