# Ansible Role: Firewall linux

Install iptables and configure its rules

## Requirements

None.

## Role Variables

- allow_icmp
- allowed_ips
- allowed_tcp_ports

## Dependencies

None.

# Example Playbook

```yaml
- hosts: server
  roles:
    - role: firewall_linux
      vars:
         allow_icmp: False # to prohibit ICMP traffic
```
