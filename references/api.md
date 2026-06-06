# MiniMax API 参考

## 基础信息

- **Base URL**: `https://api.minimax.chat`
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
    "voice_id": "Chinese (Mandarin)_Gentle_Youth",
    "speed": 1.0,
    "vol": 1.0,
    "pitch": 0,
    "emotion": "happy",
    "voice_url": "https://example.com/reference.mp3"
  },
  "audio_setting": {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1
  },
  "filler_words": true
}
```

### 常用中文音色

| voice_id | 名称 |
|----------|------|
| `Chinese (Mandarin)_Gentle_Youth` | 温润青年 |
| `Chinese (Mandarin)_Reliable_Executive` | 沉稳高管 |
| `Chinese (Mandarin)_Radio_Host` | 电台男主播 |
| `Chinese (Mandarin)_News_Anchor` | 新闻女声 |
| `Chinese (Mandarin)_Sweet_Lady` | 甜美女声 |
| `Chinese (Mandarin)_Warm_Girl` | 温暖少女 |
| `Chinese (Mandarin)_Male_Announcer` | 播报男声 |

### 常用英文音色

| voice_id | 名称 |
|----------|------|
| `English_expressive_narrator` | 英文叙述者 |
| `male-qn-qingse` | 男声青年 |
| `female-shaonv` | 女声少女 |

### 情绪标签 (Speech 2.8 新增)

| emotion | 名称 | 使用场景 |
|---------|------|----------|
| `happy` | 开心 | 正面、积极的内容 |
| `sad` | 悲伤 | 抒情、感人的内容 |
| `angry` | 愤怒 | 激动、批评的内容 |
| `bright` | 明亮 | 活泼、轻松的内容 |
| `relaxed` | 放松 | 休闲、冥想内容 |
| `serious` | 严肃 | 正式、专业的场合 |
| `nervous` | 紧张 | 悬念、焦虑的场景 |
| `disgusted` | 厌恶 | 反感、嫌弃的语气 |
| `fearful` | 恐惧 | 恐怖、惊悚内容 |
| `surprised` | 惊讶 | 意外、感叹的场景 |
| `gentle` | 温柔 | 安慰、关怀的语气 |
| `calm` | 平静 | 沉稳、冷静的表达 |

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

**端点**: `POST /v1/video_generation`

**Text-to-Video 请求体**:
```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "生成视频的描述",
  "duration": 6,
  "resolution": "768P"
}
```

**模型选项**:
- `MiniMax-Hailuo-2.3` — 推荐，支持 6s/10s
- `MiniMax-Hailuo-02` — 需要订阅支持
- `T2V-01` — 标准版
- `T2V-01-Director` — 导演版

**分辨率**: `720P`, `768P`, `1080P`

**响应**: 返回 task_id，通过 `GET /v1/query/video_generation?task_id={task_id}` 查询进度

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

**请求体**:
```json
{
  "model": "image-01",
  "prompt": "图像描述",
  "image_size": "1:1",
  "num_images": 1
}
```

**image_size 选项**: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`

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
