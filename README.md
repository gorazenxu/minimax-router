# MiniMax Router

> MiniMax 全模态路由技能 — 图片（文生图 + 图生图）/ 视频（4 模式）/ 音乐 / 语音 / 对话，一套自然语言全搞定。

## 能力矩阵

| 能力 | 模型 | 计费池 | 亮点 |
|------|------|--------|------|
| 🖼️ 图片生成 | `image-01` / `image-01-live` | general | 文生图 + **图生图**（`subject_reference`，保人物一致） |
| 🎬 视频生成 | `MiniMax-Hailuo-2.3` / `-Fast` / `Hailuo-02` / `S2V-01` | video | **4 种模式**：文生 / 图生 / 首尾帧 / 主体参考（保人脸） |
| 🎵 作曲 | `music-2.6`（默认）/ `music-2.5`（fallback） | general | 智能反推 3 套候选，保护用户歌词 |
| 🔊 语音合成 | `speech-2.8-hd` / `speech-2.8-turbo` | general | 情绪控制 / 音色克隆 / 语气词 / 17+ 音色 |
| 💬 文本对话 | MiniMax-M 系列（M2.7 等） | general | — |
| 📊 配额查询 | — | — | `check_quota.py` 实时查双窗口余额 |

> **配额机制**：基于 Token Plan（Plus ¥49 / Max ¥119 / Ultra ¥469），**5 小时固定窗口 + 周窗口**双控制。额度不是固定数字，以 `check_quota.py` 实时查询为准。
>
> general 池（文本+语音+图+乐）按量计费价格折算，video 池按个数独立计费。

---

## 使用方式

### 自然语言（推荐）

`router.py` 自动识别意图，包括**图生图**（换风格/换背景/保持人物）和**主体参考视频**（让照片里的人动起来 / 保人脸）：

```
"帮我画一张海边日落图 16:9"        → 文生图
"用这张人像换成赛博朋克风格"         → 图生图（自动传 --ref）
"帮我做个日出视频"                  → 文生视频
"让这张照片里的人动起来，在花园漫步"  → 主体参考视频 S2V-01
"生成视频 https://a.com/first.jpg 到 https://a.com/last.jpg" → 首尾帧视频
"帮我写首轻快的民谣"                → 作曲
"把这段文字转语音"                  → TTS 合成
```

### 斜杠命令

```
/c <内容>   →  文本对话
/t <内容>   →  文本转语音
/v <内容>   →  文本/图片转视频
/m <内容>   →  作曲
/i <内容>   →  文本/图生图
```

---

## 视频生成 4 种模式

同一端点 `/v1/video_generation`，router 自动选择：

| 模式 | 触发条件 | 模型 | 参数 |
|------|---------|------|------|
| ① 文生视频 | 只有文字 | `MiniMax-Hailuo-2.3` | `prompt` |
| ② 图生视频 | 1 张图（首帧） | `MiniMax-Hailuo-2.3` / `-Fast` | `first_frame_image` |
| ③ 首尾帧视频 | 2 张图（首+尾） | `MiniMax-Hailuo-02` | `first_frame_image` + `last_frame_image` |
| ④ 主体参考视频 | 人脸照 + "动起来/保人脸" | `S2V-01` | `subject_reference`（保人脸一致） |

---

## 交互流程

有配额的 API 严格执行**"一次一调"**：

```
用户描述意图 → router 识别模式 + 构造参数 → 展示确认提示
用户说"生成" → 透传参数调底层脚本 → 等待结果 → 展示产物
```

参数齐全时直接执行，不全时追问。**生成前先跑 `check_quota.py` 查看余额，避免打到上限。**

---

## 脚本速查

| 脚本 | 用途 |
|------|------|
| `scripts/router.py` | 自动路由主入口（智能识别意图 + 参数透传） |
| `scripts/image.py` | 文生图 + 图生图（`--ref` / `-s` / `-n` / `--optimize` / `--seed`） |
| `scripts/video.py` | 视频 4 模式（`-i` / `--last-frame` / `--subject-ref` / `-d` / `-r`） |
| `scripts/music.py` | 作曲（`-p` / `-l` / `--instrumental` / `--lyrics-optimizer`） |
| `scripts/tts.py` | 语音合成（`-v` / `-e` / `--clone-url` / `--filler-words`） |
| `scripts/check_quota.py` | 查询当前双窗口配额余额 |
| `scripts/video_with_audio.py` | 视频+配音+音乐合并（FFmpeg） |

### 手动调用示例

```bash
# 图生图（本地人像 → 换风格）
python scripts/image.py "换成水墨画风格" --ref ./face.jpg -o out.png

# 主体参考视频 S2V-01（保人脸）
python scripts/video.py "让这个人在花园漫步" --subject-ref ./face.jpg -o out.mp4

# 首尾帧视频
python scripts/video.py "小女孩长大" -i start.jpeg --last-frame end.jpeg -o out.mp4

# 作曲（带歌词，默认 music-2.6）
python scripts/music.py -p "Mandopop, Emotional, Male vocal" -l "[Chorus]\n副歌内容" -o out.mp3

# TTS（指定音色 + 情绪）
python scripts/tts.py "今天天气真好" -v presenter_male -e happy -o out.mp3
```

---

## 配置

```bash
export MINIMAX_API_KEY=sk-cp-...
```

API Key 来源：MiniMax 开放平台 → 账户管理 → 接口密钥（订阅 Key 为 `sk-cp-` 前缀）。

国内版 `api.minimaxi.com`（备用 `api-bj.minimaxi.com`）。国际版 `api.minimax.io` 不同（音色 ID / 域名都不一样）。

---

## 文档参考

| 文档 | 说明 |
|------|------|
| `SKILL.md` | 完整使用手册（路由规则、作曲流程、TTS 引导、配额机制） |
| `references/api.md` | API 参考（4 模式视频、图生图 subject_reference、音色/情绪/模型参数） |
| `references/voices.md` | 国内版 17+ 音色 ID 速查（短格式 `male-qn-qingse` 等） |
| `references/video-controls.md` | 视频运镜指令（`[左移][推进]` 等） |
| `references/voice-cloning.md` | 音色克隆详细流程 |
| `references/async-tts.md` | 异步长文本 TTS（>10000 字符） |
| `references/error-codes.md` | 错误码速查 |