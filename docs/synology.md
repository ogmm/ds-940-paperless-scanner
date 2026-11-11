# Set up the Brother DS-940DW on Synology DSM 7

[Project README](../README.md) · [Polski](i18n/pl.md) · [Deutsch](i18n/de.md) · [Français](i18n/fr.md) · [Español](i18n/es.md) · [简体中文](i18n/zh-CN.md) · [Русский](i18n/ru.md)

Run the receiver on your NAS and choose where it writes finished PDFs. Use an SMB share, point it at an existing Paperless-ngx instance, or start a new Paperless-ngx stack alongside it.

## 1. Prepare the scanner and NAS

1. Install **Container Manager** from **Package Center**. The supplied Brother driver targets **x86-64 (amd64)**. On the NAS, `uname -m` should return `x86_64`.
2. Set the scanner’s switch to Wi-Fi and connect it to your home LAN. Reserve its IPv4 address in your router. The reference setup used TCP 54921 and UDP 161 between the NAS and the scanner. Keep the scanner connection on your LAN. [Brother wireless setup](https://support.brother.com/g/b/producttop.aspx?c=gb&lang=en&prod=ds940dw_us_eu_as)
3. In **File Station**, create a folder such as `/volume1/docker/ds-940-paperless-scanner`. Copy the contents of the downloaded repository directly into that folder, including `compose.yaml`, `Dockerfile`, `ds940/`, and `.env.example`.
4. Create the `work` directory and, if you need a new destination, `consume`. Choose a user and group that can write to both. Over SSH, `id -u` and `id -g` show the numeric IDs of the current account. For an existing Paperless installation, you can use its IDs if they have write access to both directories.
5. Copy `.env.example` to `.env` and set `SCANNER_IP`, `SCAN_UID`, and `SCAN_GID`. Keep `.env` in the project directory on the NAS. The default paths `./work` and `./consume` are relative to the project folder. You can also use absolute host paths for `SCAN_WORK_DIR` and `SCAN_OUTPUT_DIR`.

For a first setup over SSH, create the directories and configuration template as follows.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

Edit `.env` before starting the containers. Apply permissions to the receiver’s working directory and any new folders you create for this project.

## 2. Select the PDF destination

### A. An SMB share or an existing Paperless-ngx instance

- **SMB share.** Point `SCAN_OUTPUT_DIR` at a directory on the NAS, such as `/volume1/scans/inbox`. Open that share over SMB to view the completed PDFs.
- **Existing Paperless-ngx.** Open the Paperless container’s volume details in Container Manager and find the **host path** mounted at `/usr/src/paperless/consume`. Set `SCAN_OUTPUT_DIR` to that host path. Both containers need access to it. If a network filesystem misses file notifications, set `PAPERLESS_CONSUMER_POLLING_INTERVAL=15` in the Paperless container. [Paperless-ngx consumption settings](https://docs.paperless-ngx.com/configuration/#document-consumption)

Start the receiver using Container Manager or SSH.

- **Container Manager.** Choose **Project → Create**. Name the project `ds-940-paperless-scanner`, select the folder with the source files, and upload `compose.yaml`. Choose **Build**, then **Start**. If the wizard cannot resolve variables from `.env`, use the SSH commands below from the project folder. [Synology project documentation](https://kb.synology.com/tr-tr/DSM/help/ContainerManager/docker_project?version=7)
- **SSH.** Run the following commands from the project folder using an account with Docker access. Some older Synology installations expose Compose as `docker-compose`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

### B. A new Paperless-ngx stack

1. Create `export`. Ensure that the numeric user and group in `.env` can write to the new `work`, `consume`, and `export` directories. The example gives Paperless the same IDs.
2. Set separate random values for `POSTGRES_PASSWORD` and `PAPERLESS_SECRET_KEY` in `.env`. You can generate each value locally with `openssl rand -hex 32`. Set `PAPERLESS_BIND_IP` to the NAS’s LAN address if you want to reach the web interface from another device. The default port is 8010. Use `PAPERLESS_TIME_ZONE`, `PAPERLESS_OCR_LANGUAGE`, and `PAPERLESS_OCR_LANGUAGES` to customize the archive. [Paperless-ngx OCR settings](https://docs.paperless-ngx.com/configuration/#ocr-settings)
3. Run both Compose files from the source directory. The example creates dedicated data volumes for the new instance.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

4. Find the running containers under **Container Manager → Container**. Open Paperless on the address and port from `.env` and create the first administrator. PostgreSQL and Valkey use the project network.

You can also run the commands once through **Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script** as `root`. Paste the commands for your chosen option with the `cd` line and without `sudo`. Run the task manually once. The Compose restart policy handles subsequent NAS restarts. [DSM Task Scheduler](https://kb.synology.com/index.php/en-ro/DSM/help/DSM/AdminCenter/system_taskscheduler?version=7)

## 3. Verify a physical scan

1. Power on the scanner in Wi-Fi mode. In the `scanner` container log, wait for `Ready for paper`. You can also read `work/auto-status.json` in File Station. `waiting_for_paper` indicates that the driver reached the feeder. Docker’s `healthy` status reports that the supervisor is running, even while the scanner is powered off.
2. Mark the front and back of a test sheet. Insert it face up. The receiver starts automatically. Wait for the sheet to exit before feeding another.
3. Open the PDF on the share or in Paperless. Check both sides and the last line of the document. In Paperless, allow time for the import and OCR to finish.
4. Power off the scanner after the batch. The receiver stays available for the next session.

To change `SCAN_PAPER_SIZE` in `.env`, run `docker compose up -d scanner` again with the same project name and `-f` files as your installation. For paper longer than A4, close the top output guide and leave room for a straight exit. [Brother’s supported paper sizes](https://support.brother.com/g/b/faqend.aspx?c=us&faqid=faq00002914_005&lang=en&pfs=1&prod=ds940dw_us_eu_as)

## Troubleshoot the receiver

| What you see | What to check |
| --- | --- |
| `scanner_offline` after power-on | Check the scanner’s Wi-Fi mode, reserved IPv4 address, and LAN access from the NAS. The receiver retries after a delay. |
| `scanner_busy` or `-NG 401` | Close other scanner clients. Let the receiver retry or power-cycle the Brother. Use one receiver per scanner. |
| `paper_blocked` and the error light | Open the top cover, gently remove the sheet, and close the cover. Check its length, the guide, and the selected paper profile. |
| PDF in the spool, with no document in Paperless | Check `SCAN_OUTPUT_DIR`, permissions, and the Paperless logs. A manifest with `phase: ready` is waiting for delivery. `phase: forwarded` means the PDF reached the output directory. |

Each job in `work/spool` contains a manifest and the page images, completed PDF, or partial data saved after an error. After confirming import and keeping any backup you need, you can archive or remove old jobs marked `forwarded`. Keep jobs marked `ready` until delivery finishes. Disk use in the spool is separate from a busy Wi-Fi session. Switching off the scanner ends the session and leaves the files on the NAS.

A restart between publishing a PDF and updating its manifest can cause the receiver to offer the finished file again. The included Paperless configuration enables duplicate detection. [Brother jam instructions](https://support.brother.com/g/b/faqend.aspx?c=gb&faqid=faq00000694_502&lang=en&prod=ds940dw_us_eu_as) · [Paperless-ngx consumption options](https://docs.paperless-ngx.com/configuration/#document-consumption)
