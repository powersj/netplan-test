# Netplan Test

Simple and dirty framework to test various netplan configurations

## Prereqs
The following configuration and packages are required before running tests:

```
sudo mkdir /srv/netplan
sudo chown -R "$USER":"$USER" /srv/netplan
sudo apt update
sudo apt install cloud-image-utils python3-distro-info python3-simplestreams
```

## Collecting Output

Files are collected via cloud-init using user-data found in `tools/user_data.yaml`. Below is an example:

```
runcmd:
  - [sh, -c, 'ip -oneline -4 addr show > /var/tmp/ip_addr']
```

Then during collect phase everything in /var/tmp is collected.

## Test VM
### Default Network Devices

| name | mac |
|------|-----|
| ens4 | 52:54:00:12:34:04 |
| ens5 | 52:54:00:12:34:05 |
| ens6 | 52:54:00:12:34:06 |
| ens7 | 52:54:00:12:34:07 |
