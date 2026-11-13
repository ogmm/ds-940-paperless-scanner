# Deploy the receiver with Docker Compose

[Quick start](../README.md#quick-start) · [Synology DSM 7 example](synology.md)

Build and run the `scanner` service from `compose.yaml` on an x86-64 Linux host on the scanner's LAN. A local directory is enough for the first scan. Point the same service at a mounted share for network storage or a Paperless-ngx consume directory for automatic import.

## Configure the receiver

Set these values in the `.env` file beside `compose.yaml`. The two directory settings are paths on the Docker host. Relative paths are resolved from the project folder. Create the directories before starting the container. [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)

| Setting | Default | What to enter |
| --- | --- | --- |
| `SCANNER_IP` | Required | Reserved IPv4 address of the Brother on your LAN. |
| `SCAN_UID`, `SCAN_GID` | `1000`, `1000` | Numeric IDs with write access to the working and output directories. |
| `SCAN_WORK_DIR` | `./work` | Persistent directory for status, page images, and the PDF spool. Use local storage so jobs are available during share outages. |
| `SCAN_OUTPUT_DIR` | `./consume` | Local folder, mounted network directory, or Paperless-ngx consume directory. |
| `SCAN_PAPER_SIZE` | `a4` | Paper profile. See the [paper size notes](../README.md#paper-sizes) before trying `auto` or `legal`. |

Run the [quick start](../README.md#quick-start) for a new installation. After editing `.env` for the standalone receiver, run `docker compose up -d scanner`. For the included Paperless-ngx stack, run `docker compose -f compose.yaml -f compose.paperless.yaml up -d` so both services pick up changes to the shared directory and user settings.

To skip the `-f` options with the Paperless-ngx stack, uncomment `COMPOSE_FILE=compose.yaml:compose.paperless.yaml` in `.env`. Plain `docker compose up -d`, `ps`, and `logs` then use both files. [Compose environment variables](https://docs.docker.com/compose/how-tos/environment-variables/envvars/#compose_file)

## Save to a mounted network share

For example, a mini PC running Docker can save to a folder exported by a NAS or another file server.

1. Mount an SMB or NFS share on the Docker host, for example at `/mnt/scans`. If the receiver starts automatically at boot, arrange for the share to be mounted before the receiver starts.
2. Confirm the mount with `findmnt --mountpoint /mnt/scans`. Set the share and mount permissions so the receiver's `SCAN_UID` and `SCAN_GID` can create and rename files in the destination.
3. Set `SCAN_OUTPUT_DIR=/mnt/scans` in `.env`. Start the receiver with `docker compose up -d --build scanner` and check that a test PDF appears on the share.

If Docker runs on the file server itself, set `SCAN_OUTPUT_DIR` to the local path behind the share. Both arrangements use the same Compose service.

## Add Paperless-ngx

### Use an existing installation

Find the host folder that Paperless-ngx watches for incoming documents. In a standard Docker installation it is mounted at `/usr/src/paperless/consume`. Set the receiver's `SCAN_OUTPUT_DIR` to that folder's path on the receiver host. For separate hosts, mount the same network share on both.

Give the receiver permission to create and rename files and the Paperless consumer permission to read and remove them. If your filesystem misses file change notifications, enable polling on the Paperless side. For Paperless-ngx 3, set `PAPERLESS_CONSUMER_POLLING_INTERVAL=15`. [Paperless-ngx consumption settings](https://docs.paperless-ngx.com/configuration/#document-consumption)

Start the receiver with `docker compose up -d --build scanner`. Feed a test sheet and check the Paperless document list after import and OCR.

### Start a new Paperless-ngx stack

The optional `compose.paperless.yaml` overlay adds Paperless-ngx, PostgreSQL, and Valkey. It uses the same `SCAN_OUTPUT_DIR` as the scanner service.

Create `export` alongside `work` and `consume` with write access for the configured UID and GID. Set separate random values for `POSTGRES_PASSWORD` and `PAPERLESS_SECRET_KEY` in your local `.env`.

```sh
mkdir -p export
docker compose -f compose.yaml -f compose.paperless.yaml config --quiet
docker compose -f compose.yaml -f compose.paperless.yaml up -d --build
```

On the Docker host, open `http://127.0.0.1:8010` by default. To open the web interface from another device, set `PAPERLESS_BIND_IP` to the Docker host's LAN address before starting the stack. Create the first administrator and send a test scan. [Paperless-ngx setup guide](https://docs.paperless-ngx.com/setup/)

## Update the receiver

Pull the new version and rebuild the image from the project folder. Use the same `-f` files as for the first start.

```sh
git pull
docker compose up -d --build scanner
```

Git does not track `.env`, `work`, `consume`, or `export`, so the update keeps your settings, spool, and scans. If you downloaded a ZIP instead of cloning, extract the new files over the project folder. To change the Paperless-ngx version, set `PAPERLESS_VERSION` in `.env` after reading the Paperless-ngx release notes, then run `docker compose -f compose.yaml -f compose.paperless.yaml up -d`.

## Troubleshoot the receiver

Use `docker compose logs -f scanner` or read `auto-status.json` under `SCAN_WORK_DIR`. Docker's health check reports supervisor health. The `waiting_for_paper` state confirms the driver reached the feeder.

Switch the scanner on right before a batch, start each scan only by inserting a sheet, and switch the scanner off afterwards. Never press the Scan button on the scanner. The [everyday use rules](../README.md#everyday-use) explain why.

| What you see | What to check |
| --- | --- |
| The exclamation-mark light blinks yellow and the scanner doesn't respond, usually after the Scan button was pressed | Hold the power button for a few seconds until the scanner is fully off. Leave the containers running. Switch the scanner on, wait for Wi-Fi and `Ready for paper`, and insert the sheet again. |
| A sheet doesn't start a scan after the scanner has been on for a long time without scanning | The scanner's pool of network connections is full. Switch the scanner off and on again and wait for `Ready for paper`. Switch it off after each batch to prevent this. |
| `scanner_offline` | Check Wi-Fi mode, `SCANNER_IP`, and connectivity from the Docker host. Wait for the next retry after powering on. |
| `scanner_busy` or `-NG 401` | Close other scanner clients. Let the receiver retry or power-cycle the scanner. Use one receiver per scanner. |
| `paper_blocked` | Clear the feeder and check the paper length, output guide, and paper profile. |
| A spool job is `ready` | A complete PDF is waiting for delivery. Check that the output directory is mounted and writable. |
| A spool job is `forwarded` | The PDF reached the output directory. For Paperless-ngx, check the consume mount and import logs. |

Each job directory in `SCAN_WORK_DIR/spool` contains a manifest and the data saved for that attempt. Check the destination before archiving or removing old jobs. Keep jobs marked `ready` until delivery finishes. A restart during publication can offer the same completed file again. The included Paperless-ngx configuration enables duplicate detection. [Brother jam instructions](https://support.brother.com/g/b/faqend.aspx?c=gb&faqid=faq00000694_502&lang=en&prod=ds940dw_us_eu_as)
