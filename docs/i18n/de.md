# Brother DS-940DW auf Synology DSM 7 einrichten

[Englische Anleitung](../synology.md) · [Projekt-README](../../README.md)

Nach dem Einschalten genügt es, ein Blatt einzulegen. Der NAS-Empfänger speichert beide Seiten in einer PDF-Datei. Als Ziel eignen sich eine SMB-Freigabe, eine vorhandene Paperless-ngx-Installation oder ein neuer Paperless-ngx-Stack.

## 1. Scanner und NAS vorbereiten

1. Installiere **Container Manager** im **Paket-Zentrum**. Der verwendete Treiber setzt einen x86-64-NAS voraus. `uname -m` sollte `x86_64` ausgeben.
2. Verbinde den Scanner im WLAN-Modus mit dem Heimnetz und reserviere seine IPv4-Adresse im Router. Der NAS muss den Scanner im LAN erreichen können. In der Referenzinstallation verwendete der Treiber TCP 54921 und UDP 161.
3. Lege in **File Station** den Ordner `/volume1/docker/ds-940-paperless-scanner` an und kopiere den Inhalt des Repositorys hinein. Dazu gehören `Dockerfile`, `compose.yaml`, `ds940/` und `.env.example`.
4. Lege bei der ersten Einrichtung `work` und `consume` an und kopiere die Vorlage nach `.env`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

Trage die Scanner-Adresse in `SCANNER_IP` ein. Verwende für `SCAN_UID` und `SCAN_GID` die IDs eines Benutzers und einer Gruppe mit Schreibzugriff auf beide Ordner. Die Befehle `id -u` und `id -g` zeigen diese IDs in einer SSH-Sitzung an. Bewahre `.env` lokal auf dem NAS auf.

## 2. In eine Freigabe oder ein vorhandenes Paperless scannen

Für SMB setzt du `SCAN_OUTPUT_DIR` auf den NAS-Pfad des Freigabeordners. Für Paperless ermittelst du im Container Manager den **Host-Pfad**, der unter `/usr/src/paperless/consume` eingebunden ist. Verwende diesen Pfad als `SCAN_OUTPUT_DIR`. Beide Container benötigen Zugriff auf denselben Ordner. Falls Dateisystemereignisse auf der Netzwerkfreigabe ausbleiben, setze im Paperless-Container `PAPERLESS_CONSUMER_POLLING_INTERVAL=15`.

Wähle im Container Manager **Projekt → Erstellen**, den Quellordner und die Datei `compose.yaml`. Erstelle und starte das Projekt. Wenn der Assistent `.env` nicht auswertet, starte den Empfänger per SSH.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 3. Einen neuen Paperless-ngx-Stack starten

Lege `export` an. Die gewählten IDs benötigen Schreibzugriff auf `work`, `consume` und `export`. Trage zwei unabhängige Zufallswerte für `POSTGRES_PASSWORD` und `PAPERLESS_SECRET_KEY` in die lokale `.env` ein. Du kannst sie jeweils mit `openssl rand -hex 32` erzeugen. Für den Zugriff über das Heimnetz setzt du `PAPERLESS_BIND_IP` auf die LAN-Adresse des NAS. Der Standardport ist 8010.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

Öffne Paperless unter der konfigurierten Adresse und erstelle das erste Administratorkonto. Die Befehle der gewählten Variante kannst du auch einmalig im **Aufgabenplaner** als benutzerdefiniertes Skript mit dem Benutzer `root` ausführen. Übernimm die Zeile mit `cd` und lass `sudo` weg.

## 4. Den ersten Scan prüfen

1. Schalte den Scanner ein und warte im Protokoll des Containers `scanner` auf `Ready for paper`. Die Datei `work/auto-status.json` zeigt dann `waiting_for_paper`.
2. Markiere Vorder- und Rückseite eines Testblatts. Lege es mit der Vorderseite nach oben ein. Warte, bis das Blatt ausgeworfen wurde.
3. Öffne die PDF-Datei in der Freigabe oder in Paperless und prüfe beide Seiten. Gib Paperless Zeit für Import und OCR. Schalte den Scanner nach der Serie aus.

`SCAN_PAPER_SIZE=a4` ist die Standardeinstellung. `auto` erkennt die Papiergröße. `legal` verwendet einen festen Scanbereich von rund 355,6 mm Länge. Ein vollständiger physischer Scan eines langen Belegs im Legal-Modus steht noch aus. Schließe bei Papier über A4 die obere Ausgabeführung. Starte den Dienst nach einer Profiländerung mit `docker compose up -d scanner` und denselben Projekt- und `-f`-Optionen neu.

## Empfänger aktualisieren

Kopiere die Dateien der neuen Version nach `/volume1/docker/ds-940-paperless-scanner` und ersetze die alten. Das Repository enthält weder `.env` noch `work`, `consume` oder `export`, daher bleiben Einstellungen und Scans erhalten. Baue den Empfänger anschließend per SSH mit demselben Projektnamen und denselben `-f`-Dateien wie bei der Installation neu. Wenn du den Paperless-ngx-Stack aus diesem Projekt nutzt, ergänze `-f compose.paperless.yaml`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## Fehler beheben

Die meisten Probleme vermeidest du mit drei Regeln: Schalte den Scanner erst kurz vor dem Scannen ein, drücke nie die Scan-Taste am Gerät (der Scan startet, sobald du ein Blatt einlegst und der Scanner es einzieht) und schalte den Scanner nach jeder Serie aus.

- Blinkt nach einem Druck auf die Scan-Taste das gelbe Ausrufezeichen und reagiert der Scanner nicht mehr, halte die Ein/Aus-Taste einige Sekunden gedrückt und warte, bis er ausgeschaltet ist. Lass die Container weiterlaufen. Schalte den Scanner wieder ein, warte auf WLAN und `Ready for paper` und lege das Blatt erneut ein.
- Startet ein eingelegtes Blatt keinen Scan, nachdem der Scanner lange ohne Scan eingeschaltet war, ist sein Pool an Netzwerkverbindungen voll. Schalte den Scanner aus und wieder ein, warte auf `Ready for paper` und lege das Blatt erneut ein.
- Bei `scanner_offline` prüfe WLAN-Modus, reservierte Adresse und Erreichbarkeit im LAN.
- Bei `scanner_busy` oder `-NG 401` schließe andere Scannerprogramme. Warte auf einen neuen Versuch oder schalte den Brother aus und wieder ein.
- Bei `paper_blocked` öffne die obere Abdeckung, ziehe das Blatt vorsichtig heraus und schließe die Abdeckung.
- Fehlt das Dokument in Paperless, prüfe Pfad, Zugriffsrechte und Protokoll. In `work/spool` bedeutet `ready`, dass die Zustellung aussteht. `forwarded` bestätigt den Schreibvorgang im Zielordner. Archiviere ältere Aufträge, nachdem du den Import geprüft und die benötigten Kopien gesichert hast.
