# Brother DS-940DW na Synology DSM 7

Ten przewodnik prowadzi od połączenia Brothera z Wi‑Fi do pierwszego dokumentu na NAS. Możesz uruchomić sam odbiornik albo dodać do niego nową instancję Paperless-ngx.

## 1. Przygotuj urządzenia i katalogi

1. W **Centrum pakietów** zainstaluj **Container Manager**. Wariant w tym repo korzysta ze sterownika Brother dla **x86‑64 (amd64)**. Architektura hosta widoczna w terminalu po `uname -m` powinna być `x86_64`.
2. Ustaw przełącznik skanera w pozycji Wi‑Fi i podłącz go do domowej sieci w trybie infrastruktury. W routerze zarezerwuj jego adres IPv4. NAS powinien mieć dostęp do skanera w LAN. W sprawdzonej konfiguracji sterownik używał TCP 54921 i UDP 161. Pozostaw ruch skanera w sieci lokalnej. [Instrukcje Brothera](https://support.brother.com/g/b/producttop.aspx?c=gb&lang=en&prod=ds940dw_us_eu_as)
3. W **File Station** utwórz katalog projektu w udziale `docker`. Przykładowa ścieżka to `/volume1/docker/ds-940-paperless-scanner`. Umieść bezpośrednio w tym katalogu zawartość pobranego repo, w tym `compose.yaml`, `Dockerfile`, `ds940/` i `.env.example`.
4. Utwórz `work`. Przy zapisie do nowego katalogu utwórz też `consume`. Wybierz konto lub grupę, które będą mogły zapisywać do obu katalogów. Numery UID i GID konta możesz odczytać poleceniami `id -u` i `id -g` w sesji SSH na NAS. Przy istniejącym Paperless możesz użyć jego UID i GID, jeśli mają dostęp do `work` i `consume`.
5. Skopiuj `.env.example` do `.env` w katalogu projektu. Uzupełnij `SCANNER_IP`, `SCAN_UID` i `SCAN_GID`. `SCAN_WORK_DIR=./work` i `SCAN_OUTPUT_DIR=./consume` są ścieżkami względem katalogu projektu. Możesz podać ścieżki bezwzględne. Zachowaj `.env` na NAS w katalogu dostępnym dla administratora wdrożenia.

Jeśli tworzysz katalogi przez SSH, możesz użyć poniższych poleceń. Nadaj uprawnienia tylko katalogom odbiornika i nowym katalogom tego wdrożenia.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

## 2. Wybierz katalog docelowy

### Wariant A. Udział SMB albo istniejący Paperless-ngx

**Udział SMB.** Ustaw `SCAN_OUTPUT_DIR` na ścieżkę katalogu w udziale na NAS, np. `/volume1/scans/inbox`. PDF-y będą widoczne w tym udziale po SMB.

**Istniejący Paperless.** W Container Managerze otwórz szczegóły kontenera Paperless. W jego wolumenach odczytaj **ścieżkę hosta** przypisaną do `/usr/src/paperless/consume`. Przykład to `/volume1/docker/paperless/consume`. Wpisz tę ścieżkę jako `SCAN_OUTPUT_DIR`. Odbiornik i Paperless muszą mieć dostęp do tego samego katalogu. Jeśli Paperless nie reaguje na nowe pliki z udziału sieciowego, w jego środowisku ustaw `PAPERLESS_CONSUMER_POLLING_INTERVAL=15`. [Konfiguracja importu Paperless-ngx](https://docs.paperless-ngx.com/configuration/#document-consumption)

Wybierz Container Manager lub SSH, aby uruchomić sam odbiornik.

- **Container Manager.** Otwórz **Projekt → Utwórz**. Nazwij projekt `ds-940-paperless-scanner`, wskaż katalog ze źródłami i wgraj `compose.yaml`. Wybierz **Zbuduj** i **Uruchom**. Jeśli kreator nie odczyta zmiennych z `.env`, użyj poniższych poleceń w katalogu projektu. [Obsługa projektów Container Manager](https://kb.synology.com/tr-tr/DSM/help/ContainerManager/docker_project?version=7)
- **SSH.** W katalogu projektu uruchom polecenia jako administrator Dockera na NAS. W starszych instalacjach polecenie Compose może się nazywać `docker-compose`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

### Wariant B. Nowe Paperless-ngx i odbiornik

1. Utwórz w katalogu projektu `export`. Upewnij się, że UID i GID ustawione w `.env` mają dostęp do nowych katalogów `work`, `consume` i `export`. Przykład Compose przypisuje te same identyfikatory aplikacji Paperless.
2. W `.env` ustaw osobne losowe wartości `POSTGRES_PASSWORD` i `PAPERLESS_SECRET_KEY`. Możesz wygenerować każdą poleceniem `openssl rand -hex 32` na swoim komputerze lub NAS. Jeśli chcesz korzystać z Paperless w LAN, ustaw `PAPERLESS_BIND_IP` na adres NAS. Domyślny port to 8010. Własną strefę i języki OCR podaj w `.env`. Przykładowo `PAPERLESS_OCR_LANGUAGE=pol+eng` wraz z `PAPERLESS_OCR_LANGUAGES=pol` dodaje polski do domyślnego angielskiego. [Konfiguracja OCR](https://docs.paperless-ngx.com/configuration/#ocr-settings)
3. Uruchom oba pliki Compose z tego samego katalogu. Ten przykład tworzy osobny projekt ze swoimi wolumenami danych.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

4. W DSM znajdź uruchomione kontenery w **Container Manager → Kontener**. W przeglądarce otwórz Paperless na adresie i porcie z `.env` i utwórz pierwszego administratora. Baza i Valkey pozostają w sieci projektu.

Możesz też wykonać polecenia Compose jako jednorazowe zadanie DSM. W **Panel sterowania → Harmonogram zadań → Utwórz → Zaplanowane zadanie → Skrypt zdefiniowany przez użytkownika** wybierz konto `root`. Wklej polecenia danego wariantu bez `sudo`, z `cd` do katalogu źródeł. Uruchom zadanie ręcznie raz. Kontenery wznawiają pracę zgodnie z polityką restartu w Compose. [Harmonogram zadań DSM](https://kb.synology.com/index.php/en-ro/DSM/help/DSM/AdminCenter/system_taskscheduler?version=7)

## 3. Zrób pierwszy skan

1. Włącz Brothera w trybie Wi‑Fi. W dzienniku kontenera `scanner` zaczekaj na **Ready for paper**. Szczegółowy stan jest w `work/auto-status.json`. Stan `waiting_for_paper` oznacza, że sterownik otworzył skaner i sprawdził podajnik. Stan `healthy` kontenera dotyczy nadzorcy, który działa również przy wyłączonym Brotherze.
2. Zaznacz przód i tył kartki testowej. Wsuń ją do podajnika z przodem do góry. Odbiornik zacznie skan bez naciskania przycisku. Zaczekaj na całkowite wysunięcie kartki, zanim podasz kolejną.
3. Otwórz PDF w udziale lub w Paperless i sprawdź obie strony. Paperless pobiera plik z katalogu importu. Odczekaj, aż dokument pojawi się w aplikacji, i sprawdź wynik OCR.
4. Wyłącz skaner po zakończeniu serii. Odbiornik pozostanie uruchomiony i zaczeka na następną sesję.

Przy zmianie `SCAN_PAPER_SIZE` w `.env` wykonaj ponownie `docker compose up -d scanner` z taką samą nazwą projektu i listą plików `-f`, jak podczas instalacji. Przy paragonach dłuższych od A4 zamknij górną prowadnicę i zostaw miejsce na prosty wysuw papieru.

## Diagnostyka i obsługa bufora

| Objaw | Co sprawdzić |
| --- | --- |
| `scanner_offline` po włączeniu | Sprawdź tryb Wi‑Fi, adres IPv4 i dostępność w LAN. Odbiornik ponawia próbę w odstępach, więc daj mu chwilę na zmianę stanu. |
| `scanner_busy` lub `-NG 401` | Zamknij inne aplikacje korzystające ze skanera. Odczekaj na ponowienie lub wyłącz i włącz Brothera. Jednemu urządzeniu przypisz jeden odbiornik. |
| `paper_blocked` i wykrzyknik | Otwórz górną pokrywę, wyjmij zacięty papier i zamknij pokrywę. Sprawdź długość papieru, ułożenie prowadnicy i profil skanowania. |
| PDF jest w buforze, a brakuje go w Paperless | Sprawdź `SCAN_OUTPUT_DIR`, prawa do katalogu i dziennik Paperless. `phase: ready` oznacza oczekiwanie na przekazanie. `phase: forwarded` oznacza zapis do folderu docelowego. |

W `work/spool` każdy skan ma osobny folder z manifestem, obrazami stron oraz PDF-em albo częściowymi danymi po błędzie. Kopie ułatwiają odzyskanie skanu. Gdy potwierdzisz import i masz potrzebną kopię, możesz archiwizować lub usuwać wybrane starsze foldery z `phase: forwarded` w File Station. Zachowaj foldery ze stanem `ready` do czasu przekazania. Wzrost zajętości dysku w buforze to osobne zjawisko od zajętej sesji Wi‑Fi. Wyłączenie skanera kończy sesję pracy, a pliki zostają na NAS.

Po przerwaniu pracy między zapisem PDF a oznaczeniem manifestu odbiornik może ponowić przekazanie gotowego dokumentu. Przykład Compose włącza rozpoznawanie duplikatów przez Paperless. [Rozwiązywanie zacięć Brother](https://support.brother.com/g/b/faqend.aspx?c=pl&faqid=faq00000694_502onceyou&lang=pl&prod=ds940dw_us_eu_as) · [Opcje importu Paperless-ngx](https://docs.paperless-ngx.com/configuration/#document-consumption)
