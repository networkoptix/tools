# General notes

We use some trick to reuse precompiled obj files.
Dirty builds run faster than clean and we are trying to optimize build speed.

Given axes:
platform linux-64, linux-86, windows-86, ..
branch default, vms, vms_3.2, ..
customization default, hanwha, ..

Optimization rules:
changing platform -> full rebuild
changing branch -> full rebuild (looks like)
changing customization -> partial rebuild

The solution is:

1.  Keep platform x branch in separate workspaces
2.  Allow to build different customization in the same place
3.  Mess-up auto, release and custom pipelines into the same workspace (this may result in
    full rebuild in future, but anyways we may control build time and see this problem)

Job specific:

According to prev. facts,

- all platform x branch variables are frozen in job
- all customization-related stuff is passed as arguments

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

- allow "Authenticated Users" to do everything.
- allow "admin" to do everything (just in case..)

Now it's safe to save.

Other users may be added to auth matrix if needed.

# Emulating NAS

On publish node:

1.  Create beta-builds fake mount with sticky group bit
2.  Change ownership on repository, grant only jenkins write access
3.  Add infra/cached-hg repo with rules similar to b-b (we don't wont)

```
sudo mkdir -p /mnt-stub/beta-builds/repository
sudo chown -R beta-builds:beta-builds /mnt-stub/beta-builds
sudo chmod 2775 /mnt-stub/beta-builds

sudo chown jenkins:jenkins /mnt-stub/beta-builds/repository
sudo chmod a-w /mnt-stub/beta-builds/repository
sudo chmod u+w /mnt-stub/beta-builds/repository
sudo chmod g-w /mnt-stub/beta-builds/repository

sudo mkdir -p /mnt-stub/infra/cached-hg
sudo chown -R infra:infra /mnt-stub/infra
sudo chmod 2775 /mnt-stub/infra/

sudo chmod -R g+w /mnt-stub/infra/
sudo usermod -a -G infra $YOUR_USER_NAME
```

from real prod server (for example, alpha)

```
rsync -av /mnt/infra/cached-hg/ $YOUR_USER_NAME@10.0.0.158:/mnt-stub/infra/cached-hg/
```

# Configuring email notifications

Go to http://10.0.0.112:8080/configure

In section "Extended E-mail Notification"

Configure smtp connection and credentials for service@networkoptix.user
Exact config is not provided due to security reasons.
