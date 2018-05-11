# Ansible Role: Windows libvirt guest initialization

Prepare windows virtual machine.

## Requirements

None.

## Role Variables

## Dependencies

None.

# Example Playbook

```yaml
- hosts: server
  roles:
    - role: libvirt_guest_init_windows
```

## Known issues

There's an issue with NFS client installation: VM is unaccessable due to hangs during installation.
The powershell script install_nfs_client.ps1 was removed from floppy and _setup.bat:

```
# Install client to mount NFS shares
Install-WindowsFeature -Name NFS-Client
```