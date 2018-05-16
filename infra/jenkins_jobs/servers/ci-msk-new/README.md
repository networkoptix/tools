# Manual configuration steps used for "staging":

## Configure groovy

Go to http://10.0.0.112:8080/configureTools/

In "Groovy" section display all groovy installations, then ensure that added

```
name: groovy
install automatically: yes
version: 2.4.9
```

## Uncheck "Usage Statistics"

Go to http://10.0.0.112:8080/configure

In section "Usage Statistics" uncheck checkbox

## Configure default view

"All" is not the best choice because there are too many jobs and no reason
to load them all every time any user opens jenkins.

Go to http://10.0.0.112:8080/configure

In default view drop down choose runners.

## Add some users

Here we suppose that we use jenkins own users DB.

To manage/list registered users go to http://10.0.0.112:8080/securityRealm/
To add new user go to http://10.0.0.112:8080/securityRealm/addUser

```
name: login as used in email (ex: jsnow)
password: generate some random password (`$ uuidgen | pbcopy` is ok) and paste here
confirm: paste one more time
full name: name and surname (ex: John Snow)
email: full email of user (ex: jsnow@networkoptix.com)
```

Next send credentials (login/password) to user privately and ask to change password.

Repeat for other users.

## Configure auth rules

Go to http://10.0.0.112:8080/configureSecurity/

IMPORTANT: DO NOT SAVE UNTIL AT LEAST ONE USER OR GROUP HAS FULL ACCESS!!!

In Authorization section check radio with Project-based Matrix Authorization Strategy.
This strategy allow to restrict user actions even for triggering particular builds.

In revealed matrix

* allow "Authenticated Users" to do everything.
* allow "admin" to do everything (just in case..)

Now it's safe to save.

Other users may be added to auth matrix if needed.
