# Brother DS-940DW Wi-Fi Scan Receiver

**Give an affordable Wi-Fi scanner a scan-to-folder workflow.** Power on the Brother DS-940DW, feed a sheet, and find both sides in one PDF. Save to a local folder, a NAS share, or Paperless-ngx without opening a phone app for each scan.

Brother's standard Wi-Fi workflow uses a scanning client on a phone or computer. We wanted to put the DS-940DW on a shelf and send mail, invoices, and receipts straight to a network folder. The Docker receiver takes the role of the app on your local network. It gave us the workflow we wanted and saved a trip to the post office to return the scanner. [Brother DS-940DW user guide](https://support.brother.com/g/s/id/htmldoc/ads/cv_ds640/uke/index.html?lang=en&prod=ds940dw_us_eu_as)

[Docker quick start](#get-your-first-pdf) · [Deployment examples](#deployment-examples) · [Docker configuration](docs/docker.md)

![The Docker receiver asks the Brother DS-940DW to scan over Wi-Fi. The scanner returns page images. The receiver saves a PDF to a local or network folder, or to the Paperless-ngx import folder.](assets/scanner-architecture.svg)

## Feeding a sheet starts the next scan

The container uses Brother's Linux driver, `brscan5` through SANE, to send a scan request. When the feeder is empty, the receiver closes the session, waits three seconds, and tries again. When a sheet is present, the next request captures both sides in color at 300 dpi. The receiver uses longer retry delays when the scanner is off or busy.

## Get your first PDF

Use a **Brother DS-940DW in Wi-Fi mode** and an **x86-64 Linux host with Docker Engine and Compose**. The bundled driver setup targets `linux/amd64`. Connect the scanner to the host's local network and reserve its IPv4 address in your router. The receiver uses Docker host networking to reach it. [Brother wireless setup](https://support.brother.com/g/b/producttop.aspx?c=gb&lang=en&prod=ds940dw_us_eu_as) · [Docker host networking](https://docs.docker.com/engine/network/drivers/host/)

Open the downloaded source folder on the Docker host. On first setup, create the working and output directories and copy the configuration template.

```sh
mkdir -p work consume
cp .env.example .env
```

Set `SCANNER_IP` to the scanner's reserved IPv4 address. Set `SCAN_UID` and `SCAN_GID` to the numeric user and group that can write to `work` and `consume`. Use `id -u` and `id -g` for the account that created the directories. The default `SCAN_OUTPUT_DIR=./consume` saves ordinary PDF files in that folder. [Configuration reference](docs/docker.md#configure-the-receiver)

```sh
docker compose config --quiet
docker compose up -d --build scanner
docker compose logs -f scanner
```

Power on the scanner and wait for `Ready for paper` in the log. Mark both sides of a test sheet, insert it face up, and open the PDF in `consume` to verify both pages. Wait for each sheet to exit before feeding the next. Power off the scanner when the batch is done to end its Wi-Fi session. The receiver stays running for the next batch.

## Deployment examples

- **Linux host writing to a NAS or file server.** Mount an SMB or NFS share on the host and point `SCAN_OUTPUT_DIR` at the mounted directory. [Network share example](docs/docker.md#save-to-a-mounted-network-share)
- **Paperless-ngx for OCR and search.** Point the receiver at your existing import folder or start a new archive with the optional Compose overlay. [Paperless-ngx setup](docs/docker.md#add-paperless-ngx)
- **Synology DSM 7 as the Docker host.** Run the same receiver in Container Manager on an amd64 NAS and write to a shared folder or Paperless-ngx. [Synology example](docs/synology.md)

Translations of the Synology example · [Polski](docs/i18n/pl.md) · [Deutsch](docs/i18n/de.md) · [Français](docs/i18n/fr.md) · [Español](docs/i18n/es.md) · [简体中文](docs/i18n/zh-CN.md) · [Русский](docs/i18n/ru.md)

## The receiver publishes one complete PDF at a time

![The receiver captures both sides, builds a PDF in the spool, and renames the temporary file in the destination. Failed deliveries are retried from the spool.](assets/pdf-delivery.svg)

The receiver stages the page images and builds the PDF in its local `work/spool` directory. It writes a temporary file in the destination and renames it to its final `.pdf` name after the write succeeds. If delivery fails, the spool keeps the finished PDF for retry. It also retains delivered scans and partial data from failed scans. [Spool and recovery](docs/docker.md#troubleshoot-the-receiver)

## A4 is the starting point for everyday scanning

| `SCAN_PAPER_SIZE` | Behavior |
| --- | --- |
| `a4` | Default fixed scan area of 210 × 297 mm. This is the format used for everyday scanning in the original home installation. |
| `auto` | Uses the driver's document size detection. A roughly 35 cm receipt jammed in the original trial. |
| `legal` | Requests a fixed scan area about 355.6 mm long. The scanner accepted the geometry with an empty feeder. A full physical receipt scan in this mode is still unverified. Short sheets can have extra white space below the image. |

For paper longer than A4, close the top output guide and leave room for the sheet to exit straight. For receipts beyond the driver's range, Brother provides a separate single-sided **Long Paper** mode in iPrint&Scan. [Supported documents](https://support.brother.com/g/b/faqend.aspx?c=us&faqid=faq00002914_005&lang=en&pfs=1&prod=ds940dw_us_eu_as) · [Brother Long Paper instructions](https://support.brother.com/g/b/faqend.aspx?c=gb&faqid=faq00100159_001&lang=en&prod=ds940dw_us_eu_as)

## Build and verify the receiver

Run the tests with Python 3.12 on Linux.

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

The tests cover duplex PDF output, Legal-sized frames, partial scans, retries, and connection recovery. CI checks both Compose configurations and builds the amd64 image. A separate Paperless-ngx 3.4.2 stack imported a synthetic duplex PDF from the receiver and recognized text on both pages. Use a marked sheet to verify your physical scanner after setup.

The Dockerfile fetches Brother's pinned driver package and checks its SHA-256 during the build. Build the image for your own installation under Brother's driver terms. Store deployment settings and scans in local runtime directories. [Brother driver downloads and terms](https://support.brother.com/g/b/downloadlist.aspx?c=gb&lang=en&prod=ds940dw_us_eu_as&os=128)
