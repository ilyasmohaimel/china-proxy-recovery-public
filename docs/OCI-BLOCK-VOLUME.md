# OCI block volume

Use an OCI Block Volume for `/srv`, keeping application data, backups, and Git checkouts separate from the boot disk.

## Create and attach

Create the volume in OCI, then attach it to the VM as **Paravirtualized** with **Read/write** access.

## Identify the disk

Never assume a device name. Compare the boot disk, expected new size, filesystem state, and OCI device mappings before formatting anything:

```sh
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS,MODEL
sudo blkid
ls -l /dev/oracleoci/
sudo wipefs -n /dev/<NEW_DISK>
```

The boot disk must already contain the mounted root filesystem. The new volume must match the expected size and have no existing filesystem signatures.

## Format and mount

After identifying the new disk unambiguously, back up `fstab`, create an ext4 filesystem, and mount it at `/srv`:

```sh
sudo install -m 0600 /etc/fstab /etc/fstab.pre-block-volume
sudo mkfs.ext4 -L <VOLUME_LABEL> /dev/<NEW_DISK>
sudo mkdir -p /srv
sudo blkid /dev/<NEW_DISK>
```

Add the filesystem UUID, never the device name, to `/etc/fstab`:

```fstab
UUID=<VOLUME_UUID> /srv ext4 defaults,_netdev,nofail,noatime 0 2
```

Then mount and verify it:

```sh
sudo mount -a
findmnt /srv
df -h /srv
lsblk
```

## Layout and reboot test

Keep the volume root-owned and create the initial layout:

```sh
sudo install -d -o root -g root -m 0755 /srv/apps /srv/data /srv/backups /srv/git
```

Reboot once, then repeat `findmnt /srv`, `df -h /srv`, and `lsblk` before relying on the mount. Keep live UUIDs, OCIDs, IPs, and credentials out of version control.
