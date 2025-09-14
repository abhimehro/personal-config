Control D switching
- Privacy: privacy-dns
- Gaming:  gaming-dns
- Status:  dns-status

Verification:
- dns-status
- nslookup example.com 127.0.0.1
- nslookup ad.doubleclick.net 127.0.0.1

Notes:
- If VPN overrides DNS, disable its "use VPN DNS" feature to let 127.0.0.1 (ctrld) handle resolution.
- After macOS updates/reboots, run dns-status to confirm ctrld is active.
- I also have a repository called personal_config for these types of configurations and scripts if you can ensure everything gets properly backed up, then pushed. The folder is located at ~/Users/abhimehrotra/Documents/dev/personal-config
