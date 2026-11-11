# Brother DS-940DW na Synology DSM 7

[Instrukcja angielska](../synology.md) · [README projektu](../../README.md)

Po włączeniu skanera i wsunięciu kartki NAS zapisuje obie strony w jednym PDF-ie. Możesz zapisywać na udział SMB, do istniejącego Paperless-ngx albo uruchomić nową instancję razem z odbiornikiem.

## 1. Przygotuj skaner i NAS

1. Zainstaluj **Container Manager** z **Centrum pakietów**. Sterownik w tym projekcie wymaga Synology z procesorem x86-64. Polecenie `uname -m` powinno zwrócić `x86_64`.
2. Ustaw skaner w trybie Wi-Fi, połącz go z domową siecią i zarezerwuj jego adres IPv4 w routerze. NAS musi mieć dostęp do skanera w LAN. W instalacji referencyjnej sterownik używał TCP 54921 i UDP 161.
3. W **File Station** utwórz katalog `/volume1/docker/ds-940-paperless-scanner` i umieść w nim zawartość pobranego repozytorium, w tym `Dockerfile`, `compose.yaml`, `ds940/` i `.env.example`.
4. Przy pierwszej konfiguracji utwórz `work` i `consume`, a następnie skopiuj szablon do `.env`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

Wpisz adres skanera do `SCANNER_IP`. Ustaw `SCAN_UID` i `SCAN_GID` na identyfikatory użytkownika i grupy z prawem zapisu do obu katalogów. Możesz je sprawdzić przez SSH poleceniami `id -u` i `id -g`. Przechowuj `.env` lokalnie na NAS.

## 2. Zapisuj na udział lub do istniejącego Paperless

Dla udziału SMB podaj w `SCAN_OUTPUT_DIR` ścieżkę katalogu na NAS. Dla Paperless odczytaj w Container Managerze ścieżkę hosta zamontowaną jako `/usr/src/paperless/consume` i wpisz ją w `SCAN_OUTPUT_DIR`. Oba kontenery muszą mieć dostęp do tego samego katalogu. Gdy Paperless pomija pliki dodane na udział sieciowy, ustaw w jego środowisku `PAPERLESS_CONSUMER_POLLING_INTERVAL=15`.

W Container Managerze wybierz **Projekt → Utwórz**, wskaż katalog źródeł i wgraj `compose.yaml`. Zbuduj i uruchom projekt. Jeśli kreator nie odczyta `.env`, uruchom odbiornik przez SSH.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 3. Uruchom nowy stos Paperless-ngx

Utwórz `export` i zapewnij wybranemu UID/GID zapis do `work`, `consume` oraz `export`. W lokalnym `.env` ustaw osobne losowe wartości `POSTGRES_PASSWORD` i `PAPERLESS_SECRET_KEY`. Każdą możesz wygenerować poleceniem `openssl rand -hex 32`. Aby otwierać Paperless z innych urządzeń, ustaw `PAPERLESS_BIND_IP` na adres NAS w LAN. Domyślny port to 8010.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

Otwórz Paperless na skonfigurowanym adresie i utwórz pierwszego administratora. Polecenia danego wariantu możesz też wykonać raz jako `root` w **Panel sterowania → Harmonogram zadań → Skrypt zdefiniowany przez użytkownika**. Zachowaj `cd` do katalogu projektu i pomiń `sudo`.

## 4. Zrób pierwszy skan

1. Włącz Brothera i zaczekaj na `Ready for paper` w dzienniku kontenera `scanner`. W `work/auto-status.json` gotowość oznacza `waiting_for_paper`.
2. Zaznacz przód i tył kartki testowej. Wsuń ją stroną przednią do góry, a przed podaniem następnej zaczekaj na pełne wysunięcie.
3. Otwórz PDF w udziale lub w Paperless i sprawdź obie strony. W Paperless zaczekaj na import i OCR. Wyłącz skaner po serii.

Domyślny profil to `SCAN_PAPER_SIZE=a4`. Tryb `auto` wykrywa rozmiar, a `legal` ustawia obszar o długości około 355,6 mm. Pełny fizyczny skan długiego paragonu w Legal pozostaje do potwierdzenia. Przy dłuższym papierze zamknij górną prowadnicę. Po zmianie profilu wykonaj `docker compose up -d scanner` z tymi samymi parametrami projektu i plikami `-f`.

## Diagnostyka

- Przy `scanner_offline` sprawdź adres, tryb Wi-Fi i połączenie z LAN.
- Przy `scanner_busy` lub `-NG 401` zamknij inne programy skanujące. Zaczekaj na ponowienie lub wyłącz i włącz Brothera.
- Przy `paper_blocked` otwórz górną pokrywę, delikatnie wyjmij kartkę i zamknij pokrywę.
- Jeśli PDF nie dotarł do Paperless, sprawdź ścieżkę, uprawnienia i jego dziennik. W `work/spool` stan `ready` oznacza oczekiwanie na przekazanie, a `forwarded` zapis w katalogu docelowym. Archiwizuj starsze foldery dopiero po sprawdzeniu importu i zachowaniu potrzebnej kopii.
