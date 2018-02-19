# Playbooks for setting up infrastructure

## Getting started.

### Development

1. Clone repo.
2. Run `./setup_env.sh` to create venv and install all dependencies.
3. Add some changes.
4. Run linter `./lint.sh` and fix all errors and warnings.
5. Commit.

### Style guide.

In community it's common to use .yml extensions for YAML files.
Therefore other file extensions for YAML files are forbidden.

Run linter before commit.

### Apply playbook on Production

```bash
source ./.venv/bin/activate
ansible-playbook \
  --inventory ./inventory-prod.ini \
  --ask-vault-pass \
  ./main.yml -vv
deactivate
```

if you use specific ssh key & user, for example, networkoptix.rsa.key and admin

```bash
source ./.venv/bin/activate
ansible-playbook \
  --private-key=~/.ssh/networkoptix.rsa.key \
  --user=admin \
  --inventory ./inventory-local.ini \
  --ask-vault-pass \
  ./main.yml -vv
deactivate
```

Youa also may limit hosts providing `--limit`.

It's supposed that you have all required permissions and vault password.

To decrypt secrets:

```bash
source ./.venv/bin/activate
ansible-vault decrypt secrets.yml --ask-vault-pass
deactivate
```

To encrypt it back

```bash
source ./.venv/bin/activate
ansible-vault encrypt secrets.yml
deactivate
```

You will be prompted for new password

## Repo layout

Repo is organized accordingly to "Ansible best practices", see
http://docs.ansible.com/ansible/latest/playbooks_best_practices.html
for general information.

Here are details about this repo.

`./ansible.cfg` is config for Ansible itself and it may be shared across
environments. Ansible is configured to use local inventory by default.
So all production operations require to provide prod inventory explicitly.

`./inventory-prod.ini` is inventory file where all hosts and groups of hosts are
described. This is production version!

`./inventory-local.ini` is inventory file where all hosts and groups of hosts are
described. This is local version. And this file is not committed. So you need to
create it manually if you want to set up local environment for testing and
debugging purposes. Fill `./inventory-local.ini` using `./inventory-prod.ini`
as reference.

`main.yml` is play and main entry point. Execution of this play means running
entire playbook on all managed hosts.

`secrets.yml` is secret file that contains sensitive information for production
infrastructure. For example, passwords and ssh keys. Keep this file encrypted or
don't commit at all.

`secrets.yml.example` is example of `secrets.yml`. You should use it as
reference for setting up local testing and debugging infrastructures.

`host_vars` and `group_vars` are directories where YAML files with host-specific
or group-specific information is located.

`roles` is directory for holding different roles.

## Roles and role variables

### Setting up KVM and libvirt on host

`roles/kvm_host`

Does not require any variables.

Works on Debian9 only. Supports Ubuntu 16.04

### Defining and managing KVM guest lifecycle

`roles/kvm_guest`

See variables in roles/kvm_guest/defaults/main.yml

Note: guest specification is defined in guest variables, but this role is
delegated to (executed on) kvm_host. kvm_host is required variable for guest
vars and kvm_host hostname must match with on of hosts from inventory file.
And that host must be provisioned with kvm_host role.

### Setting up Build node

`roles/build_node`

Does not require any variables.

Works on Ubuntu 16.04.

Currently this role is "all-in-one for linux platform" allows building

* amd64
* i386 in cross env
* nodejs projects

### Setting up node as Jenkins slave

`roles/jenkins_slave`

Creates Jenkins user and configures environment such as authorized keys and some
secrets/sensitive data.

Optional requirements are jenkins home, name, and group as well as ssh keys.
Se more in `roles/jenkins_slave/defaults/main.yml`

## Known issues

### KVM setup

It requires special config in BIOS. This is under Admin team responsibility.

Task "Test libvirtd operational" is supposed to verify that KVM is ok. But it
didn't fail build last time. Instead Guest starting was failed.

If this happens, SSH into server. Run `sudo virt-host-validate`.
If you see "QEMU: Checking if device /dev/kvm exists: FAIL (Check that the
'kvm-intel' or 'kvm-amd' modules are loaded & the BIOS has enabled
virtualization)", you need to go to admins and ask them to turn on that stuff.
