# fzbot

Python Discord Bot，包含 Codeforces 綁定、對戰、角色選單和 AI 功能。

## 在 Mac 使用 Docker

1. 開啟 Docker Desktop。
2. 首次設定：`cp .env.example .env`，在本機填入 `DC_TOKEN`；`NV_TOKEN` 僅 AI 功能需要。
3. 保護設定檔：`chmod 600 .env`。
4. 啟動：`docker compose up -d --build`。
5. 查看日誌：`docker compose logs -f --tail=100`。
6. 停止：`docker compose stop`；恢復：`docker compose up -d`。

Mac 必須保持開機、連網且不進入睡眠，Docker Desktop 也須運行。
容器以 UID 10001 的非 root 使用者執行，不開放主機埠，移除 Linux capabilities。
設定 `restart: unless-stopped`，異常退出時自動重啟；手動停止後不會自行恢復。

## Discord 權限

在 https://discord.com/developers/applications 選擇 Bot：

- Bot → Privileged Gateway Intents：啟用 Server Members Intent、Message Content Intent。
- 程式不要求 Presence Intent。
- OAuth2 邀請範圍：`bot` 和 `applications.commands`。
- 此 Bot 的最小權限邀請連結：https://discord.com/oauth2/authorize?client_id=1188420983061758002&permissions=275146460224&scope=bot%20applications.commands
- 伺服器權限：View Channels、Send Messages、Embed Links、Attach Files、Read Message History、Add Reactions、Manage Roles。
- 若在討論串使用指令，加上 Send Messages in Threads。
- 將 Bot 的角色放在它要管理的角色上方；頻道權限覆寫也須允許 Bot 存取。
- 使用者能否執行管理指令仍由既有指令的權限檢查決定；無需給 Bot Administrator。

參考：https://docs.discord.com/developers/topics/permissions

## 資料保存與備份

Compose 將 `fzbot_bot-data` named volume 掛載到 `/app/data`。
帳號綁定、對戰、排行榜、角色選單和自動角色設定都存放在此。
更新程式或重建容器會保留 volume；不要使用 `docker compose down -v`，它會刪除資料。
非 Docker 執行預設使用專案目錄，可透過 `DATA_DIR` 更改。

備份時先停止 Bot：

```bash
docker compose stop
mkdir -p backups
docker compose run --rm --no-deps bot tar -C /app/data -czf - . > backups/bot-data.tar.gz
docker compose up -d
```

若要帶入舊 JSON，先停止 Bot，再用 `docker compose cp <檔案> bot:/app/data/` 複製，並確認容器使用者可讀寫。

## GitHub 與機密

`.env`、本機資料、備份與日誌均排除於 Git；Docker build context 僅包含 Dockerfile、requirements.txt 和 Python 原始碼。
不將 Token 寫入程式、映像或 GitHub。Docker 管理員仍可讀取容器環境變數；不要分享 Docker inspect 或完整環境變數輸出。

更新部署：

```bash
git pull --ff-only
docker compose up -d --build
```
