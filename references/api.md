# MiniMax API 参考

## 基础信息

- **Base URL**: `https://api.minimaxi.com`（国内版；备用 `https://api-bj.minimaxi.com`）
- **API Version**: `v1`
- **认证**: `Authorization: Bearer {API_KEY}`

## TTS (文本转语音) — Speech 2.8

**端点**: `POST /v1/t2a_v2`

**请求体**:
```json
{
  "model": "speech-2.8-hd",
  "text": "要转换的文本内容",
  "stream": false,
  "output_format": "hex",
  "language_boost": "Chinese",
  "voice_setting": {
    "voice_id": "male-qn-qingse",
    "speed": 1.0,
    "vol": 1.0,
    "pitch": 0,
    "emotion": "happy"
  },
  "audio_setting": {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1
  },
  "filler_words": true,
  "subtitle_enable": false
}
```

**模型选项**: `speech-2.8-hd`（推荐，高质量）/ `speech-2.8-turbo`（更快）/ `speech-2.6-hd` / `speech-02-hd` 等。
**备用端点**: `https://api-bj.minimaxi.com/v1/t2a_v2`
**发音字典** `pronunciation_dict.tone`：如 `["处理/(chu3)(li3)", "危险/dangerous"]`。
**文本特殊标记**: `(laughs)` 笑声、`(sighs)` 叹气、`<#x#>` 停顿 x 秒。

### 常用中文音色（国内版短格式 voice_id）

> ⚠️ 国内版 `api.minimaxi.com` 用短格式 voice_id（如 `male-qn-qingse`）。
> 不要用 `Chinese (Mandarin)_xxx` 长格式——那是国际版 `api.minimax.io` 的格式，国内版会报错。
> 完整列表见 `references/voices.md`。

| voice_id | 名称 |
|----------|------|
| `male-qn-qingse` | 温润青年 |
| `male-qn-jingying` | 沉稳高管 |
| `presenter_male` | 电台男主播 / 播报男声 |
| `presenter_female` | 新闻女声 |
| `female-tianmei` | 甜美女声 |
| `female-shaonv` | 温暖少女 |

### 常用英文音色（国内版）

| voice_id | 名称 |
|----------|------|
| `male-qn-qingse` | 男声青年（中文音色可跨语种） |
| `female-shaonv` | 女声少女 |

> 国际版 `api.minimax.io` 的 voice_id 完全不同（如 `English_expressive_narrator`），详见官方文档。

### 情绪标签 (Speech 2.8，9 种)

| emotion | 名称 | 使用场景 |
|---------|------|----------|
| `happy` | 开心 | 正面、积极的内容 |
| `sad` | 悲伤 | 抒情、感人的内容 |
| `angry` | 愤怒 | 激动、批评的内容 |
| `fearful` | 害怕 | 恐怖、惊悚内容 |
| `disgusted` | 厌恶 | 反感、嫌弃的语气 |
| `surprised` | 惊讶 | 意外、感叹的场景 |
| `calm` | 中性/平静 | 沉稳、默认表达（推荐默认） |
| `fluent` | 生动 | 活泼、流畅的讲述 |
| `whisper` | 低语 | 轻声、私密、ASMR 感 |

> ⚠️ `bright/relaxed/serious/nervous/gentle` 是旧版 speech-01/02 的值，2.8 不支持。

### 语言选项

- `Chinese` — 中文（默认）
- `English` — 英文
- `auto` — 自动检测

### 输出格式

| format | 说明 |
|--------|------|
| `mp3` | 默认，推荐 |
| `wav` | 无损格式 |

### 采样率

- `8000` — 电话质量
- `16000` — 标准
- `24000` — 高质量
- `32000` — 默认（推荐）
- `48000` — 录音棚级

### 音色克隆 (Speech 2.8 新增)

提供参考音频 URL，系统会自动提取音色特征：

```json
{
  "voice_setting": {
    "voice_id": "clone",
    "voice_url": "https://example.com/reference.mp3"
  }
}
```

**要求**：
- 推荐 10 秒以上音频
- 支持 MP3、WAV 格式
- 音频应清晰、无噪音
- 支持跨语言克隆（用中文声音说英文）

## Video (视频生成)

**端点**: `POST /v1/video_generation`（异步：创建任务 → 轮询状态 → 取 file_id 下载）

官方支持 **4 种模式**（同一端点，靠参数区分）：

### 模式 1：文生视频（text-to-video）
```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "生成视频的描述",
  "duration": 6,
  "resolution": "1080P"
}
```

### 模式 2：图生视频（image-to-video，首帧）
```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "描述从首帧开始的动态演变",
  "first_frame_image": "https://.../start.png",
  "duration": 6,
  "resolution": "1080P"
}
```

### 模式 3：首尾帧视频（first-and-last-frame）
```json
{
  "model": "MiniMax-Hailuo-02",
  "prompt": "小女孩长大",
  "first_frame_image": "https://.../start.jpeg",
  "last_frame_image": "https://.../end.jpeg",
  "duration": 6,
  "resolution": "1080P"
}
```

### 模式 4：主体参考视频（subject-reference，保人脸一致）
```json
{
  "model": "S2V-01",
  "prompt": "镜头描述",
  "subject_reference": [
    { "type": "character", "image": ["https://.../face.PNG"] }
  ],
  "duration": 6,
  "resolution": "1080P"
}
```

**模型选项**:
- `MiniMax-Hailuo-2.3` — 推荐，文生/图生视频
- `MiniMax-Hailuo-2.3-Fast` — 图生视频加速版（不支持纯文字）
- `MiniMax-Hailuo-02` — 首尾帧视频
- `S2V-01` — 主体参考视频（subject-reference，保人脸）

**参数**:
- `duration`: `6` 或 `10`
- `resolution`: `720P` / `768P` / `1080P`
- `first_frame_image` / `last_frame_image`: 图片 URL
- `subject_reference`: 主体参考，`type=character`，`image` 为 URL 数组

**响应**: 返回 task_id，通过 `GET /v1/query/video_generation?task_id={task_id}` 轮询；成功后用 `file_id` 调 `GET /v1/files/retrieve?file_id=` 取下载链接。

## Music (音乐生成)

**端点**: `POST /v1/music_generation`

**请求体**:
```json
{
  "model": "music-2.5+",
  "prompt": "音乐描述（风格、情绪）",
  "lyrics": "[Verse]\n歌词内容\n[Hook]\n副歌",
  "is_instrumental": false,
  "output_format": "hex"
}
```

**注意**: 
- `lyrics` 对非纯音乐是**必填**的
- `is_instrumental: true` **只有 `music-2.5+` 支持**
- Token Plan 限额：4首/天（music-2.5+）

**模型**: `music-2.5+` (推荐，支持更多功能)

## Image (图像生成)

**端点**: `POST /v1/image_generation`

> 文生图 (t2i) 与图生图 (i2i) **共用同一端点**，区别仅在于是否传 `subject_reference`。
> 官方文档：
> - 文生图 https://platform.minimaxi.com/docs/api-reference/image-generation-t2i
> - 图生图 https://platform.minimaxi.com/docs/api-reference/image-generation-i2i

### 文生图请求体

```json
{
  "model": "image-01",
  "prompt": "图像描述（最长 1500 字符）",
  "aspect_ratio": "1:1",
  "n": 1,
  "response_format": "url",
  "prompt_optimizer": false
}
```

### 图生图请求体（加 subject_reference）

```json
{
  "model": "image-01",
  "prompt": "女孩在图书馆窗边远眺",
  "aspect_ratio": "3:4",
  "n": 2,
  "subject_reference": [
    {
      "type": "character",
      "image_file": "https://example.com/face.jpg"
    }
  ]
```

### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | string | 必填。`image-01` 或 `image-01-live` |
| `prompt` | string | 必填。图像描述，最长 1500 字符 |
| `aspect_ratio` | string | 宽高比，默认 `1:1` |
| `n` | int | 生成数量 1-9，默认 1 |
| `subject_reference` | object[] | **图生图专用**，人物/主体参考 |
| `response_format` | enum | `url`（默认，24h 有效）/ `base64` |
| `prompt_optimizer` | bool | prompt 自动优化，默认 `false` |
| `seed` | int | 随机种子，用于复现 |
| `width` / `height` | int | 仅 `image-01`，512-2048 且为 8 的倍数；与 `aspect_ratio` 同时设则优先用 `aspect_ratio` |
| `style` | object | 画风设置，仅 `image-01-live` 生效 |

### aspect_ratio 选项

`1:1` (1024×1024)、`16:9` (1280×720)、`4:3` (1152×864)、`3:2` (1248×832)、`2:3` (832×1248)、`3:4` (864×1152)、`9:16` (720×1280)、`21:9` (1344×576，仅 `image-01`)

### subject_reference（图生图核心参数）

人物主体参考，用于保持人物一致性、换场景/换风格、角色变体。

```json
"subject_reference": [
  {
    "type": "character",
    "image_file": "<公开图片 URL 或 base64 Data URL>"
  }
]
```

- `type`：`character`（人物主体）
- `image_file`：公开 URL，或 `data:image/...;base64,...` 形式的 Data URL
- 参考图要求：jpg/jpeg/png，≤10MB
- 建议使用清晰正脸、光线良好的单人照

### 响应

```json
{
  "id": "...",
  "data": {
    "image_urls": ["...", "..."]
  },
  "metadata": {
    "failed_count": "0",
    "success_count": "3"
  },
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

图像直接同步返回在 `data.image_urls` 中（注意：不同于 video/music，无需轮询任务状态）。`base_resp.status_code != 0` 表示失败。

## 查询任务状态

**端点**: `GET /v1/query/{task_type}?task_id={task_id}`

**task_type**: `video_generation`, `music_generation`

**响应**:
```json
{
  "task_id": "xxx",
  "status": "Success",
  "output": {
    "url": "https://output.mp4"
  }
}
```

**status 状态**: `Pending`, `Processing`, `Success`, `Fail`
