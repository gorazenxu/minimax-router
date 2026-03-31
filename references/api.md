# MiniMax API 参考

## 基础信息

- **Base URL**: `https://api.minimax.chat`
- **API Version**: `v1`
- **认证**: `Authorization: Bearer {API_KEY}`

## TTS (文本转语音)

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
    "pitch": 0
  },
  "audio_setting": {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1
  }
}
```

**常用中文音色**:
- `Chinese (Mandarin)_Gentle_Youth` — 温润青年
- `Chinese (Mandarin)_Reliable_Executive` — 沉稳高管
- `Chinese (Mandarin)_News_Anchor` — 新闻女声
- `Chinese (Mandarin)_Sweet_Lady` — 甜美女声
- `Chinese (Mandarin)_Warm_Girl` — 温暖少女

**常用英文音色**:
- `English_expressive_narrator` — 英文叙述者
- `male-qn-qingse` — 男声青年
- `female-shaonv` — 女声少女

**language_boost 选项**: `Chinese`, `English`, `auto`

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
