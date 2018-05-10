# Ansible Role: Windows build node

Prepare windows node

## Requirements

None.

## Role Variables

## Dependencies

None.

# Example Playbook

    - hosts: server
      roles:
        - role: libvirt_guest
  

## Issues

Change hostname. We can't do it here, because of restart cycle possibility 
due to conflict with libvirt_guest_init_windows role. The following code was removed:

    - name: Get Windows machine facts
    setup:

    - name: Change Windows HostName
    command: >-
        powershell -Command
        "Rename-Computer -NewName {{ libvirt_guest__hostname }} -Restart"
    when: "libvirt_guest__hostname != ansible_hostname"
    register: change_windows_hostname_result

    - name: Reboot the system when hostname is changed
    shell: shutdown /r -t 1
    when: change_windows_hostname_result.changed
    async: 60
    poll: 0
    
 Add NFS & samba shares. There is [a known issue with network shares under Cygwin](https://cygwin.com/faq/faq.html#faq.using.shares)
 Also we have to:
 - check a share is already exists
 - use ansible variable instead explicit ip for cinas.
 
 The following code was removed:
    
    - name: Mount infra share
    command: >-
        net use I: \\\\192.168.13.2\\infra /persistent:yes /user:infra {{ samba_mount_pass }}

    # Install windows NFS client, if you run playbook on already existing node:
    #   Install-WindowsFeature -Name NFS-Client
    # To ensure nfs client installed:
    #   Get-WindowsFeature -Name NFS*
    - name: Mount beta-builds share
    command: >-
        powershell -Command
        "New-PSDrive -Name T -PSProvider FileSystem -Root \\\\192.168.13.2\\share\\NFSv=4\\beta-builds -Persist"
  