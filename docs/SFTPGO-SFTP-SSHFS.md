# SFTPGo SFTP and desktop mount

SFTPGo can provide public file access without exposing SMB. This is an optional example — adapt paths and ports to your deployment.

The SFTPGo pattern confines a cloud account to a single directory (e.g., `/srv/cloud`) and supports both password login for phones and a separate SSH key for a desktop.

## Server

The SFTP listener in this example uses TCP/<SFTP_PORT>. Allow that port in UFW and OCI, while keeping TCP/445 private-only if you use Samba.

The SFTPGo account root is `/srv/cloud`; an SFTP client sees that as `/` and cannot browse the rest of `/srv`.

For a phone file manager:

```text
Protocol: SFTP
Host: <SERVER_IP>
Port: <SFTP_PORT>
User: <SFTP_USER>
```

## Linux desktop

Create a dedicated Ed25519 key locally and add only its public half to the existing SFTPGo account. Password authentication can stay enabled for mobile clients if needed.

```sh
ssh-keygen -t ed25519 -f ~/.ssh/<SFTP_KEY> -C sftpgo-cloud
chmod 600 ~/.ssh/<SFTP_KEY>
sftp -i ~/.ssh/<SFTP_KEY> -P <SFTP_PORT> <SFTP_USER>@<SERVER_IP>
```

Mount the account through SSHFS at `/mnt/cloud` (example) with a systemd automount. The remote path is `:/`, because SFTPGo already confines the account.

```ini
# /etc/systemd/system/mnt-cloud.mount
[Mount]
What=<SFTP_USER>@<SERVER_IP>:/
Where=/mnt/cloud
Type=fuse.sshfs
Options=port=<SFTP_PORT>,IdentityFile=/home/<LOCAL_USER>/.ssh/<SFTP_KEY>,UserKnownHostsFile=/home/<LOCAL_USER>/.ssh/known_hosts,StrictHostKeyChecking=yes,BatchMode=yes,PasswordAuthentication=no,KbdInteractiveAuthentication=no,PreferredAuthentications=publickey,allow_other,default_permissions,uid=<UID>,gid=<GID>,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3,ConnectTimeout=10
```

```ini
# /etc/systemd/system/mnt-cloud.automount
[Automount]
Where=/mnt/cloud
TimeoutIdleSec=5min
```

Enable the automount, then access the directory once to trigger the SSHFS mount.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now mnt-cloud.automount
findmnt /mnt/cloud
```

`/etc/fuse.conf` needs `user_allow_other` for the mount options above.

In a file manager, add a normal local Place for:

```text
file:///mnt/cloud
```

Do not use an `sftp://` bookmark with embedded credentials.

## Checks

```sh
sftp -i ~/.ssh/<SFTP_KEY> -P <SFTP_PORT> <SFTP_USER>@<SERVER_IP>
findmnt /mnt/cloud
systemctl status mnt-cloud.automount --no-pager
```

Verify list, upload, read, rename, move, and delete with a temporary file. Also stop the mount unit, access the directory again, and confirm the automount reconnects.
