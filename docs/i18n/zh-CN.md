# 在 Synology DSM 7 上配置 Brother DS-940DW

[英文指南](../synology.md) · [项目 README](../../README.md)

打开扫描仪，放入一张纸，NAS 上的接收程序就会将正反两面保存到同一个 PDF。你可以把文件写入 SMB 共享文件夹、导入已有的 Paperless-ngx，或者同时启动一个新的 Paperless-ngx 实例。

## 1. 准备扫描仪和 NAS

1. 在**套件中心**安装 **Container Manager**。本项目使用的驱动需要 x86-64 架构的 NAS。运行 `uname -m`，预期输出为 `x86_64`。
2. 将扫描仪切换到 Wi-Fi 模式，接入家庭局域网，并在路由器上为它保留 IPv4 地址。NAS 必须能够通过局域网访问扫描仪。参考安装使用了 TCP 54921 和 UDP 161。
3. 在 **File Station** 中创建 `/volume1/docker/ds-940-paperless-scanner`，将仓库内容复制到该目录，包括 `Dockerfile`、`compose.yaml`、`ds940/` 和 `.env.example`。
4. 首次部署时创建 `work` 和 `consume`，并将配置模板复制为 `.env`。

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p work consume
cp .env.example .env
chmod 600 .env
```

将扫描仪地址填入 `SCANNER_IP`。`SCAN_UID` 和 `SCAN_GID` 应对应有权写入这两个目录的用户和组。可通过 SSH 运行 `id -u` 和 `id -g` 查看相应编号。请将 `.env` 保存在 NAS 本地。

## 2. 保存到 SMB 共享文件夹或已有的 Paperless

使用 SMB 时，将 NAS 上的共享目录路径填入 `SCAN_OUTPUT_DIR`。使用已有的 Paperless 时，在 Container Manager 中查看该容器的挂载设置，找到挂载到 `/usr/src/paperless/consume` 的**宿主机路径**，然后将其填入 `SCAN_OUTPUT_DIR`。两个容器都需要访问同一个目录。如果 Paperless 未发现共享目录中的新文件，请在其环境中设置 `PAPERLESS_CONSUMER_POLLING_INTERVAL=15`。

在 Container Manager 中选择**项目 → 新增**，选择源码所在目录并导入 `compose.yaml`，然后构建并启动项目。如果向导无法读取 `.env`，请通过 SSH 运行以下命令。

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 3. 启动新的 Paperless-ngx 实例

创建 `export`，并确认配置中的用户和组可以写入 `work`、`consume` 和 `export`。在本地 `.env` 中为 `POSTGRES_PASSWORD` 和 `PAPERLESS_SECRET_KEY` 设置两个不同的随机值。可以分别运行 `openssl rand -hex 32` 生成。若要从局域网内其他设备打开 Paperless，请将 `PAPERLESS_BIND_IP` 设为 NAS 的局域网地址。默认端口为 8010。

```sh
cd /volume1/docker/ds-940-paperless-scanner
mkdir -p export
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml config --quiet
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml -f compose.paperless.yaml up -d --build
```

打开配置好的 Paperless 地址并创建第一个管理员。你也可以在 DSM 的**任务计划**中创建用户定义的脚本，以 `root` 身份手动运行一次所选方案的命令。保留 `cd` 这一行，去掉 `sudo`。

## 4. 验证第一次扫描

1. 打开扫描仪，在 `scanner` 容器日志中等待 `Ready for paper`。此时 `work/auto-status.json` 中的状态为 `waiting_for_paper`。
2. 在测试纸的正反两面分别做标记，正面朝上放入。等纸张完全退出，再放入下一张。
3. 在共享文件夹或 Paperless 中打开 PDF，检查正反两面。使用 Paperless 时，请等待导入和 OCR 完成。批量扫描结束后关闭扫描仪。

默认配置为 `SCAN_PAPER_SIZE=a4`。`auto` 会检测纸张尺寸，`legal` 使用长度约为 355.6 毫米的固定扫描区域。Legal 模式下完整扫描一张长收据仍需在实体设备上验证。扫描比 A4 更长的纸张时，请合上顶部出纸导板。更改配置后，使用与安装时相同的项目名称和 `-f` 文件运行 `docker compose up -d scanner`。

## 更新接收器

将新版本的文件复制到 `/volume1/docker/ds-940-paperless-scanner` 并替换旧文件。仓库中不包含 `.env`、`work`、`consume` 和 `export`，因此你的设置和扫描文件会保留。然后通过 SSH 使用与安装时相同的项目名称和 `-f` 文件重新构建接收器。如果你使用本项目提供的 Paperless-ngx，请加上 `-f compose.paperless.yaml`。

```sh
cd /volume1/docker/ds-940-paperless-scanner
sudo docker compose -p ds-940-paperless-scanner -f compose.yaml up -d --build scanner
```

## 故障排查

- 出现 `scanner_offline` 时，检查 Wi-Fi 模式、保留地址和 NAS 到扫描仪的网络连接。
- 出现 `scanner_busy` 或 `-NG 401` 时，关闭其他扫描软件。等待接收程序重试，或关闭扫描仪后重新打开。
- 出现 `paper_blocked` 时，打开顶盖，轻轻取出纸张，再盖好顶盖。
- 如果 Paperless 中没有出现文档，请检查路径、权限和日志。在 `work/spool` 中，`ready` 表示等待交付，`forwarded` 表示 PDF 已写入目标目录。确认导入成功并保留所需副本后，再归档较早的任务目录。
