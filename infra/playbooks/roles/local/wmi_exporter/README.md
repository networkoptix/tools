# Ansible Role: WMI prometheus exporter

Install WMI exporter to windows node

## Requirements

None.

## Role Variables

## Dependencies

None.

# Example Playbook

```yaml
- hosts: server
  roles:
    - role: wmi_exporter
      vars:
         wmi_exporter_reinstall: True # to force reinstall
```

# Uninstall WMI exporter

You can use power shell script to do that:
```
$app = Get-WmiObject -Class Win32_Product -Filter "Name = 'WMI exporter'"
$app.Uninstall()
```