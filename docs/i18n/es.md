# Configurar el Brother DS-940DW en Synology DSM 7

[Guía en inglés](../synology.md) · [README del proyecto](../../README.md)

Enciende el escáner e introduce una hoja. El receptor del NAS guarda ambas caras en un único PDF. Puedes usar una carpeta SMB, una instalación existente de Paperless-ngx o una instancia nueva junto al receptor.

## 1. Preparar el escáner y el NAS

1. Instala **Container Manager** desde el **Centro de paquetes**. El controlador de este proyecto requiere un NAS x86-64. El comando `uname -m` debe devolver `x86_64`.
2. Conecta el escáner a tu red local en modo Wi-Fi y reserva su dirección IPv4 en el router. El NAS debe poder acceder al escáner por la LAN. La instalación de referencia usaba TCP 54921 y UDP 161.
3. Crea la carpeta `/volume1/docker/ds-940-paperless-scanner` en **File Station**. Copia allí el contenido del repositorio, incluidos `Dockerfile`, `compose.yaml`, `ds940/` y `.env.example`.
4. En la primera instalación, crea `work` y `consume` y copia la plantilla a `.env`.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

Introduce la dirección en `SCANNER_IP`. Para `SCAN_UID` y `SCAN_GID`, usa los identificadores de un usuario y un grupo con permiso de escritura en ambas carpetas. Puedes consultarlos por SSH con `id -u` e `id -g`. Guarda `.env` localmente en el NAS.

## 2. Guardar en un recurso SMB o en un Paperless existente

Para SMB, pon en `SCAN_OUTPUT_DIR` la ruta de la carpeta compartida en el NAS. Para Paperless, consulta en Container Manager la ruta **del host** montada en `/usr/src/paperless/consume`. Pon esa ruta en `SCAN_OUTPUT_DIR`. Los dos contenedores deben tener acceso a la misma carpeta. Si Paperless no detecta los archivos nuevos del recurso compartido, configura `PAPERLESS_CONSUMER_POLLING_INTERVAL=15` en su entorno.

En Container Manager elige **Proyecto → Crear**, selecciona la carpeta del código e importa `compose.yaml`. Construye la imagen y arranca el proyecto. Si el asistente no lee `.env`, inicia el receptor por SSH.

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 3. Iniciar un nuevo Paperless-ngx

Crea `export` y comprueba que los identificadores elegidos permiten escribir en `work`, `consume` y `export`. Guarda dos valores aleatorios distintos en `POSTGRES_PASSWORD` y `PAPERLESS_SECRET_KEY` dentro de `.env`. Puedes generar cada valor con `openssl rand -hex 32`. Para acceder desde otro dispositivo, configura `PAPERLESS_BIND_IP` con la dirección LAN del NAS. El puerto predeterminado es 8010.

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

Abre Paperless en la dirección configurada y crea el primer administrador. También puedes ejecutar una sola vez los comandos de la variante elegida como `root` en el **Programador de tareas** de DSM, en un script definido por el usuario. Conserva la línea `cd` y omite `sudo`.

## 4. Comprobar el primer escaneo

1. Enciende el Brother y espera a que aparezca `Ready for paper` en el registro del contenedor `scanner`. El archivo `work/auto-status.json` indica `waiting_for_paper` cuando está listo.
2. Marca el anverso y el reverso de una hoja de prueba. Introdúcela con el anverso hacia arriba. Espera a que salga por completo antes de introducir la siguiente.
3. Abre el PDF en la carpeta compartida o en Paperless y comprueba las dos caras. Deja que finalicen la importación y el OCR. Apaga el escáner al terminar la tanda.

El perfil predeterminado es `SCAN_PAPER_SIZE=a4`. El modo `auto` detecta el tamaño y `legal` usa un área fija de unos 355,6 mm de largo. Aún queda por comprobar un escaneo físico completo de un recibo largo en modo Legal. Para papel más largo que A4, cierra la guía superior de salida. Tras cambiar el perfil, ejecuta `docker compose up -d scanner` con el mismo nombre de proyecto y los mismos archivos `-f`.

## Solución de problemas

- Con `scanner_offline`, comprueba el Wi-Fi, la dirección reservada y el acceso desde el NAS.
- Con `scanner_busy` o `-NG 401`, cierra otros programas de escaneo. Espera el siguiente intento o apaga y vuelve a encender el Brother.
- Con `paper_blocked`, abre la tapa superior, retira la hoja con cuidado y cierra la tapa.
- Si el documento no aparece en Paperless, revisa la ruta, los permisos y el registro. En `work/spool`, `ready` indica una entrega pendiente y `forwarded` confirma la escritura en el destino. Archiva las carpetas antiguas después de verificar la importación y conservar las copias necesarias.
