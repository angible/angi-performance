# RTSP Stream Simulator with QR Code Processing

模擬自助結帳機的 RTSP 串流，從影片讀取 QR code 並發送至 API。

## 功能說明

此程式使用 4 個執行緒來處理影片串流：

1. **Thread 1 (Video Decoder)**: 使用 FFmpeg 以 15 FPS 讀取影片，將影像分割為：
   - Frame 1: 主影像 (640x480)
   - Frame 2: QR code 區域 (右下角 160x160)

2. **Thread 2 (QR Processor)**: 解析 QR code 並分配影像
   - 解析 Frame 2 中的 QR code
   - 將 QR 資料送至 request_queue
   - 將 Frame 1 送至 frame_queue

3. **Thread 3 (API Sender)**: 透過 RESTful API 發送 QR code 資料
   - Timeout: 0.5 秒

4. **Thread 4 (RTSP Encoder)**: 使用 GStreamer 編碼並提供 RTSP 串流
   - 輸出 FPS: 15
   - 內建 RTSP 伺服器

## 系統需求

### 必要軟體

- Docker Engine (版本 20.10 或更高)
- Docker Compose (版本 2.0 或更高)
- Python 3.8+ (用於下載影片工具)

### 安裝 Docker 與 Docker Compose

#### Ubuntu/Debian

```bash
# 更新套件索引
sudo apt-get update

# 安裝必要套件
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 的官方 GPG 金鑰
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 設置 Docker 儲存庫
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安裝 Docker Engine 和 Docker Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 將當前使用者加入 docker 群組（避免每次都需要 sudo）
sudo usermod -aG docker $USER

# 啟動 Docker 服務
sudo systemctl enable docker
sudo systemctl start docker

# 登出後重新登入以套用群組變更，或執行：
newgrp docker
```

#### CentOS/RHEL/Fedora

```bash
# 移除舊版本
sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

# 安裝 yum-utils
sudo yum install -y yum-utils

# 設置 Docker 儲存庫
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安裝 Docker Engine 和 Docker Compose
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 啟動 Docker 服務
sudo systemctl enable docker
sudo systemctl start docker

# 將當前使用者加入 docker 群組
sudo usermod -aG docker $USER
newgrp docker
```

#### 驗證安裝

```bash
# 檢查 Docker 版本
docker --version

# 檢查 Docker Compose 版本
docker compose version

# 測試 Docker 是否正常運作
docker run hello-world
```

## 快速開始

### Step 1: 準備影片（全自動）

**無需手動下載！** 影片會在容器啟動時**完全自動**下載和驗證。

#### 🚀 自動下載機制

系統會自動處理所有影片檔案：

✅ **自動下載**
- 在 `config.yaml` 中配置 `google_drive_url`
- 容器啟動時自動檢查影片是否存在
- 如果缺失，自動從 Google Drive 下載

✅ **自動驗證**
- 每次啟動時驗證影片 MD5 hash
- 如果檔案損壞或 MD5 不符，自動重新下載
- 確保影片檔案完整性和一致性

✅ **智能跳過**
- 如果檔案存在且 MD5 正確 → 跳過下載
- 節省頻寬和啟動時間

#### 📝 配置方式

在 `config.yaml` 中為每個攝影機添加 `google_drive_url`：

```yaml
cameras:
  cam1:
    video: /app/videos/output.mp4
    google_drive_url: "https://drive.google.com/file/d/1uus7c_hA9N5GlPfFdBDgAZ6RaEhqoPbV/view?usp=sharing"
```

**就這麼簡單！** 配置完成後，直接啟動容器即可，系統會自動處理其餘工作。

### Step 2: 配置攝影機設定

編輯 `config.yaml` 檔案來設定所有攝影機的參數。這是推薦的配置方式，讓您可以集中管理所有設定：

```yaml
# RTSP Simulator Configuration
cameras:
  cam1:
    video: /app/videos/output.mp4
    api_url: http://10.10.70.75:3501/v1  # 修改為您的 API 服務 IP
    rtsp_port: 8554
    fps: 15
    google_drive_url: "https://drive.google.com/file/d/.../view?usp=sharing"  # 自動下載用
  
  cam2:
    video: /app/videos/output.mp4
    api_url: http://10.10.70.75:3502/v1
    rtsp_port: 8554
    fps: 15
    google_drive_url: "https://drive.google.com/file/d/.../view?usp=sharing"
  
  # 更多攝影機...

# 預設影片處理設定
defaults:
  original_width: 800
  original_height: 640
  frame_width: 640
  frame_height: 480
  qrcode_size: 160
  queue_size: 30
  warmup_frames: 90
  timezone: "Asia/Taipei"  # 時區設定
```

**主要配置項目：**
- **api_url**: 修改為您的 AI 服務 IP 位址和埠號
- **video**: 影片檔案路徑（在容器內）
- **fps**: 影格率（預設 15）
- **rtsp_port**: RTSP 伺服器埠號（容器內部，預設 8554）
- **google_drive_url**: Google Drive 分享連結（選填，用於自動下載影片）
- **timezone**: 時區設定（預設 "Asia/Taipei"，可用值如 "UTC", "America/New_York", "Europe/London" 等）

### Step 3: 啟動所有攝影機模擬器

一個命令啟動所有服務（自動建立映像檔並啟動容器）：

```bash
docker compose up --build -d
```

這個命令會：
- 自動建立 Docker 映像檔
- 啟動所有 7 個攝影機容器
- 自動下載缺失的影片（如已配置 Google Drive URL）
- 在背景執行（`-d` 參數）

**查看日誌：**
```bash
# 查看所有攝影機日誌
docker compose logs -f

# 查看特定攝影機日誌
docker compose logs -f simulator-cam1
```

**啟動特定攝影機：**
```bash
# 僅啟動 cam1 和 cam2
docker compose up --build -d simulator-cam1 simulator-cam2
```

## Docker Compose 配置

`docker-compose.yml` 已預先配置 7 個攝影機模擬器，每個攝影機有獨立的 RTSP 埠號：

| 攝影機 | RTSP 埠號 | RTSP 串流 URL | API 端點 |
|-------|----------|--------------|---------|
| **cam1** | 28551 | `rtsp://<主機IP>:28551/simulation` | `http://<AI服務IP>:3501/v1` |
| **cam2** | 28552 | `rtsp://<主機IP>:28552/simulation` | `http://<AI服務IP>:3502/v1` |
| **cam3** | 28553 | `rtsp://<主機IP>:28553/simulation` | `http://<AI服務IP>:3503/v1` |
| **cam4** | 28554 | `rtsp://<主機IP>:28554/simulation` | `http://<AI服務IP>:3504/v1` |
| **cam5** | 28555 | `rtsp://<主機IP>:28555/simulation` | `http://<AI服務IP>:3505/v1` |
| **cam6** | 28556 | `rtsp://<主機IP>:28556/simulation` | `http://<AI服務IP>:3506/v1` |
| **cam7** | 28557 | `rtsp://<主機IP>:28557/simulation` | `http://<AI服務IP>:3507/v1` |

**說明：**
- `<主機IP>`: 運行 Docker 容器的主機 IP 位址
- `<AI服務IP>`: AI 服務後端的 IP 位址（在 `config.yaml` 中設定）
- 所有攝影機使用統一的 RTSP 路徑 `/simulation`

### 自訂配置

所有配置都在 `config.yaml` 檔案中管理。編輯此檔案來變更攝影機設定：

```yaml
cameras:
  cam1:
    video: /app/videos/output.mp4
    api_url: http://your-api-server:3501/v1  # 修改 API URL
    rtsp_port: 8554
    fps: 15  # 修改影格率
    google_drive_url: "https://drive.google.com/file/d/.../view?usp=sharing"
  
  cam2:
    video: /app/videos/output.mp4
    api_url: http://your-api-server:3502/v1
    rtsp_port: 8554
    fps: 15
    google_drive_url: "https://drive.google.com/file/d/.../view?usp=sharing"

# 預設設定適用於所有攝影機
defaults:
  original_width: 800
  original_height: 640
  frame_width: 640
  frame_height: 480
  qrcode_size: 160
  queue_size: 30
  warmup_frames: 90
  timezone: "Asia/Taipei"  # 時區設定
```

**修改配置後重啟容器：**
```bash
# 重啟單一攝影機
docker-compose restart simulator-cam1

# 重啟所有攝影機
docker-compose restart
```

**注意：** 所有設定都從 `config.yaml` 讀取，無需修改 `docker-compose.yml`。

## 連線 RTSP 串流

使用 VLC 或其他 RTSP 客戶端連線：

```bash
# VLC 命令列
vlc rtsp://localhost:28551/simulation

# ffplay
ffplay rtsp://localhost:28551/simulation

# 其他攝影機
vlc rtsp://localhost:28552/simulation  # cam2
vlc rtsp://localhost:28553/simulation  # cam3
```

或使用 VLC GUI：
1. 媒體 → 開啟網路串流
2. 輸入：`rtsp://localhost:28551/simulation`
3. 播放

**注意：** RTSP 路徑現在統一為 `/simulation`，而非攝影機名稱。使用不同的埠號來區分不同的攝影機。

## 容器管理

```bash
# 停止所有容器
docker-compose down

# 停止特定容器
docker-compose stop simulator-cam1

# 重啟容器
docker-compose restart simulator-cam1

# 查看容器狀態
docker-compose ps

# 查看即時日誌
docker-compose logs -f
```

## 監控與除錯

程式會定期輸出統計資訊：
- `frames_read`: 讀取的影格數
- `qr_decoded`: 成功解析的 QR code 數
- `api_sent`: 成功發送的 API 請求數
- `frames_streamed`: 成功串流的影格數
- `errors`: 錯誤次數

查看特定容器的日誌：
```bash
docker-compose logs -f simulator-cam1
```

## API Payload 格式

發送至 API 的 JSON 格式：

```json
{
  "timestamp": 1696723200.123,
  "qr_data": {
    // QR code 解析後的 JSON 資料
    // 或是字串 (如果 QR code 不是 JSON 格式)
  }
}
```

## 影片格式要求

- 解析度: 640x480
- QR code 位置: 右下角 160x160 區域
- 格式: 任何 FFmpeg 支援的格式 (MP4, AVI, MKV 等)

## 常見問題

### 下載影片失敗
- 確認 Google Drive 連結是公開或可分享的
- 檢查網路連線
- 確認已安裝 `gdown` 套件

### Docker 建立失敗
- 確認 Docker 已安裝並執行（參考「系統需求」章節）
- 檢查 Docker 服務狀態：`sudo systemctl status docker`
- 檢查 Dockerfile 中的相依套件
- 清除舊的映像檔：`docker system prune -a`

### 容器無法啟動
- 檢查影片檔案是否存在於 `cam1/output.mp4`
- 檢查埠號是否被占用
- 查看容器日誌：`docker-compose logs simulator-cam1`

### RTSP 連線失敗
- 確認容器正在執行：`docker-compose ps`
- 檢查埠號映射是否正確
- 檢查防火牆設定
- 使用 `telnet localhost 8551` 測試埠號連線

### API 連線失敗
- 確認 API 伺服器已啟動並可連線
- 檢查 API URL 是否正確
- API 需要在 0.5 秒內回應
- 檢查網路連線和防火牆設定

### QR code 無法解析
- 確認影片的 QR code 位於右下角 160x160 區域
- QR code 需清晰可見，解析度足夠
- 檢查影片品質和幀率

### 影片自動下載失敗
- 檢查 Google Drive URL 是否正確且可公開存取
- 確認網路連線正常
- 檢查容器日誌查看詳細錯誤：`docker logs simulator-cam1`
- 確認 `/app/videos` 目錄有寫入權限（不是只讀掛載）
- 手動測試下載：`docker exec -it simulator-cam1 gdown "URL" -O /tmp/test.mp4`

## 進階功能

### 手動下載影片（選用）

如果您需要在容器外手動下載影片，可使用 `download_video.py` 工具。

**安裝依賴：**
```bash
pip install gdown
```

**下載影片：**
```bash
# 下載單一攝影機
python3 download_video.py --customer Central --store westgate --camera cam1 --output output.mp4

# 下載多個攝影機
python3 download_video.py --customer Central --store westgate --camera cam1 cam2 cam3 cam4 cam5 cam6 cam7 --output output.mp4
```

這會將影片下載到各自的目錄（如 `cam1/output.mp4`, `cam2/output.mp4`）。

**注意：** 
- 使用容器自動下載功能時，**無需手動執行此步驟**
- 容器內已包含所有必要套件
