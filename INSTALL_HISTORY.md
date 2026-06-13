# 安装历史

> **本文件是"已装了什么"的唯一真相来源**。
> 任何时候接手这个项目（重启 CCD / 换电脑 / 重装系统），先读这份文件，再决定装什么。
>
> 装过 → 跳过。**别重复装已经装过的**。

**最后更新**: 2026-06-13  
**环境**: Windows 11 + PowerShell 5.1+ + scoop  
**Python**: 3.12.10（**绝不能用 3.14**，AI 库不兼容）  
**硬件**: Core Ultra 7 255H / 32GB / Intel Arc 140T（QSV 可用）  
**用户**: 卡夏-Kasya

---

## 1. 一次性安装的清单（"装过的"主清单）

| 组件 | 版本 | 安装位置 | 来源/命令 | 备注 |
|---|---|---|---|---|
| **Python 3.12** | 3.12.10 | `C:\Users\艾莉\scoop\apps\python312\current\` | `scoop install python@3.12` | 3.14 **不能用** |
| **ffmpeg** | 8.1.1 | `C:\Users\艾莉\scoop\shims\ffmpeg.exe` | `scoop install ffmpeg` | 含 Intel QSV |
| **yt-dlp** | 2026.06.09 | `C:\Users\艾莉\scoop\shims\yt-dlp.exe` | `scoop install yt-dlp` | 也可装到 venv（可选） |
| **Node.js** | 24.16.0 LTS | `C:\Users\艾莉\scoop\apps\nodejs-lts\current\` | `scoop install nodejs-lts` | npm 11.13 包含 |
| **gh (GitHub CLI)** | latest | `C:\Users\艾莉\scoop\shims\gh.exe` | `scoop install gh` | 已登录 wohuishuo |
| **git** | current | `C:\Users\艾莉\scoop\apps\git\current\` | `scoop install git` | 跟 VS Code 自带 |
| **scoop 本身** | current | `C:\Users\艾莉\scoop\` | (见 [scoop.sh](https://scoop.sh)) | Windows 包管理器 |

---

## 2. venv 里的 AI 库（`tools\.venv`）

venv 用 `python3.12 -m venv tools\.venv` 创建。
**所有 AI 库都装在 venv 里**——绝对不装到系统 Python 3.14。

| 包 | 版本 | 安装命令 | 用途 | 备注重装 |
|---|---|---|---|---|
| **faster-whisper** | 1.2.1 | `pip install faster-whisper` | 99 种语言转录 | 首次跑自动下载 large-v3 (~3GB) |
| **funasr** | 1.3.9 | `pip install funasr` | 中文转录 | 首次跑自动下载 Paraformer (~1GB) |
| **torch** | 2.12.0+cpu | `pip install torch --index-url https://download.pytorch.org/whl/cpu` | FunASR/Whisper 依赖 | **必须 CPU 版**（无 NVIDIA GPU） |
| **torchaudio** | 2.11.0+cpu | `pip install torchaudio` | FunASR 依赖 | |
| **bilibili-api** | 17.4.1 | `pip install bilibili-api-python` | B 站数据抓取 | 较老，**page_index 是 0-based** |
| **edge-tts** | 7.2.8 | `pip install edge-tts` | 配音（免费、本地、中俄英日） | |
| **mediapipe** | 0.10.35 | `pip install mediapipe` | 人脸追踪重定向 | 首次跑自动下载 ~4MB 模型 |
| **opencv-python** | 4.13.0 | `pip install opencv-python` | 人脸追踪重定向 | |

### 卸载的库（不需要再装）
- ~~`yt_dlp` Python 包~~ —— 直接用 scoop 的 `yt-dlp.exe` 命令行版更稳

---

## 3. Remotion（`tools\remotion-hello`）

| 包 | 版本 | 安装命令 |
|---|---|---|
| **remotion** | latest (4.x) | `npm install`（在 `tools/remotion-hello/` 目录） |
| **@remotion/cli** | 4.x | 同上 |
| **@remotion/player** | 4.x | 同上 |
| **react** | ^18.3.0 | 同上 |
| **react-dom** | ^18.3.0 | 同上 |
| **typescript** | ^5.5.0 | 同上 |

**已生成产物**：`out.mp4`（5 秒 hello world 动画，~346KB）—— **已加 .gitignore**

---

## 4. Claude Desktop MCP 配（`claude_desktop_config.json`）

| MCP | 命令 | 用途 |
|---|---|---|
| **bilibili** | `npx -y @xzxzzx/bilibili-mcp` | CCD 内直接读 B 站字幕/数据/评论 |
| **playwright** | `npx -y @playwright/mcp@latest` | 浏览器控制（Edge 登录态） |

**重启 CCD 后生效**。`npx` 前要设：
```powershell
$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"
```
否则 npm cache 创建在 `C:\Users\艾莉\...\cache\_logs`（GBK 乱码）会 EPERM 失败。

---

## 5. 凭据

| 凭据 | 存储位置 | 已配？ |
|---|---|---|
| **B 站 cookies** | `C:\Users\艾莉\Videos\cc视频剪辑\reference\cookies.txt` | ✅ 2026-06-13 |
| **GitHub token (gh)** | 系统 keyring | ✅ 已登录 wohuishuo，scopes: `gist, read:org, repo, workflow` |
| **funasr model** | `C:\Users\艾莉\.cache\modelscope\hub\iic\SenseVoiceSmall\` | ✅ 首次跑时自动下载 |
| **whisper large-v3** | `C:\Users\艾莉\.cache\huggingface\hub\` | ✅ 首次跑时自动下载 |
| **mediapipe face_landmarker.task** | `C:\Users\艾莉\Videos\cc视频剪辑\.claude\skills\edit-ffmpeg\models\` | ✅ 4MB 首次跑自动下载 |
| **chromium headless shell** | `%LOCALAPPDATA%\ms-playwright\` | ✅ Playwright MCP 首次跑自动下载 |

**不在这里的东西**：
- ❌ 没有 OpenAI / Anthropic API key（纯本地）
- ❌ 没有付费转录 API key（用 FunASR/whisper 免费）

---

## 6. 已知可跳过的坑（再遇别重新踩）

### npm 中文路径
```powershell
# 每次跑 npx 前必设
$env:npm_config_cache = "C:\Users\艾莉\.npm-cache"
```

### 系统 Python 3.14 不可用
所有 AI 脚本都用 `.\tools\.venv\Scripts\python.exe`——**绝不用系统 `python`**。

### Edge cookie 数据库被锁
`yt-dlp --cookies-from-browser edge` 报错。改用手动导出的 `cookies.txt`。

### B 站画质默认最差
加 `--format-sort +vcodec:avc` 优先 AVC 编码。

### FunASR SenseVoiceSmall 首次跑会下载 19 个文件
约 200MB，等 ~1-3 分钟（视网速）。后续秒开。

### bigger models 下载到 HuggingFace
首次跑 `transcribe.py` 会下载 large-v3 (3GB)，需要较长时间。不想等可改用 `medium` 或 `small` 模型。

---

## 7. 如何重装这个项目（如果需要）

```powershell
# 1. 装系统级工具
scoop install python@3.12 ffmpeg yt-dlp nodejs-lts git gh

# 2. 装 venv
python3.12 -m venv C:\Users\艾莉\Videos\cc视频剪辑\tools\.venv
C:\Users\艾莉\Videos\cc视频剪辑\tools\.venv\Scripts\python.exe -m pip install --upgrade pip
C:\Users\艾莉\Videos\cc视频剪辑\tools\.venv\Scripts\python.exe -m pip install `
  faster-whisper `
  funasr `
  "torch --index-url https://download.pytorch.org/whl/cpu" `
  torchaudio `
  bilibili-api-python `
  edge-tts `
  mediapipe `
  opencv-python

# 3. 跑自检确认
C:\Users\艾莉\Videos\cc视频剪辑\tools\health_check.ps1

# 4. 装 Remotion 依赖
cd C:\Users\艾莉\Videos\cc视频剪辑\tools\remotion-hello
npm install

# 5. (可选) 配 B 站 cookies
#    浏览器装 "Get cookies.txt LOCALLY" 扩展 → 导出到 reference/cookies.txt

# 6. (可选) 配 CCD MCP
#    编辑 %APPDATA%\Claude\claude_desktop_config.json 加 bilibili/playwright MCP
#    重启 CCD
```

---

## 8. 安装历史

| 日期 | 事件 |
|---|---|
| 2026-06-12 (早期) | 装 Python 3.12 + ffmpeg + yt-dlp + nodejs + git + scoop |
| 2026-06-12 | 建 venv + 装 faster-whisper |
| 2026-06-12 | 装 FunASR 失败的依赖，**修了 torch 缺失**（pip install torch --index-url cpu） |
| 2026-06-12 | 装 torchaudio（FunASR 依赖） |
| 2026-06-12 | 装 bilibili-api-python（17.4.1） |
| 2026-06-12 | 装 mediapipe + opencv-python（人脸追踪） |
| 2026-06-12 | 装 edge-tts（配音） |
| 2026-06-12 | 跑 Remotion hello world 渲染通过 |
| 2026-06-12 | 装 gh CLI（GitHub 推送） |
| 2026-06-13 | 改仓库名 cc- → cc-video-pipeline |

---

## 9. **下次接手时最先做的事**

1. **读这个文件** —— 知道已有什么
2. **跑 `tools\health_check.ps1`** —— 知道现在还有什么在工作
3. **看 `CLAUDE.md`** —— 知道项目整体目标 + 约束
4. **看 `TOOLS.md`** —— 知道怎么用

不需要重复装任何在第 1、2、3 节列出来的东西。
