# 异步长文本语音合成（T2A Async v2）

> 适用场景：单次文本 > 10000 字符、批量合成、长文朗读
>
> 官方文档：<https://platform.minimaxi.com/docs/api-reference/speech-t2a-async-create>
>
> 与 HTTP 同步接口（`t2a_v2`）的区别：**单请求最大 1M 字符**（同步接口是 10K）

## 三步流程

```
1. 上传文件（可选）       POST /v1/files/upload      → file_id
2. 创建合成任务           POST /v1/t2a_async_v2      → task_id
3. 轮询任务状态           GET  /v1/query/t2a_async_query_v2?task_id=xxx
   成功后拿到 file_id
4. 下载音频文件           GET  /v1/files/retrieve?file_id=xxx
```

## 接口 1：上传文本文件（可选）

如果你的文本超过 100K 字符，建议先上传文件再传 file_id（避免请求体过大）：

```
POST https://api.minimaxi.com/v1/files/upload?GroupId=<group_id>
Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data

form-data:
  purpose: t2a_async_input
  file: <text/zip 文件，UTF-8 编码的 .txt 或多个 .txt 打包的 .zip>
```

**响应：**
```json
{
  "file": {
    "file_id": 196553532456675664
  },
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

## 接口 2：创建合成任务

```
POST https://api.minimaxi.com/v1/t2a_async_v2
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

### 请求体

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `model` | ✅ | string | 见下表 |
| `text` | △ | string | 直接传文本（与 `file_id` 二选一）|
| `file_id` | △ | integer | 上传的文本文件 ID（与 `text` 二选一）|
| `language_boost` | ❌ | string | 语言强化，`auto` 或具体语言（如 `Chinese`、`English`）|
| `voice_setting` | ✅ | object | 同同步接口，见 `voices.md` |
| `pronunciation_dict` | ❌ | object | 同步接口 |
| `audio_setting` | ❌ | object | 同步接口 |
| `voice_modify` | ❌ | object | 声音后处理（国际版字段）|

**voice_setting 子字段：**
- `voice_id` — 音色 ID（系统音色或复刻音色）
- `speed` — [0.5, 2]，默认 1.0
- `vol` — (0, 10]，默认 1.0
- `pitch` — [-12, 12]，默认 0
- `emotion` — 同步接口

**audio_setting 子字段：**
- `sample_rate` — 8000 / 16000 / 22050 / 24000 / 32000 / 44100
- `bitrate` — 64000 / 96000 / 128000 / 256000
- `format` — `mp3` / `pcm` / `flac` / `wav`
- `channel` — 1 / 2

### 支持的模型

| 模型 | 特性 |
|------|------|
| `speech-2.8-hd` | 最新 HD，韵律出色、复刻相似度极佳 |
| `speech-2.8-turbo` | 最新 Turbo，40 语种支持 |
| `speech-2.6-hd` | 超低延迟、智能解析、自然度提升 |
| `speech-2.6-turbo` | 更快、更便宜，适合 Agent 场景 |
| `speech-02-hd` | 稳定版 HD |
| `speech-02-turbo` | 稳定版 Turbo，多语种增强 |

### 响应

```json
{
  "task_id": 196553532456675664,
  "task_token": "eyJhbGc...",
  "file_id": 196553532456788801,
  "usage_characters": 101,
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

**关键字段：**
- `task_id` — 任务 ID，**轮询时用**
- `task_token` — JWT 签名，部分场景需要
- `file_id` — 音频文件 ID，**成功后下载用**（不是上传的 file_id）
- `usage_characters` — 实际计费字符数

## 接口 3：查询任务状态

```
GET https://api.minimaxi.com/v1/query/t2a_async_query_v2?task_id=<task_id>
Authorization: Bearer <API_KEY>
```

> ⚠️ **限流：最多 10 次/秒**

**响应：**
```json
{
  "task_id": 196553532456675664,
  "status": "Success",        // Processing | Success | Failed | Expired
  "file_id": 196553532456788801,  // 仅 Success 时返回
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

**状态说明：**

| 状态 | 含义 | 下一步 |
|------|------|--------|
| `Processing` | 合成中 | 继续轮询（建议 2-5 秒间隔） |
| `Success` | 成功 | 用 `file_id` 调下载接口 |
| `Failed` | 失败 | 看 `base_resp.status_msg` 或 `status_code` |
| `Expired` | 任务过期 | 重新创建任务 |

## 接口 4：下载音频文件

```
GET https://api.minimaxi.com/v1/files/retrieve?file_id=<file_id>
Authorization: Bearer <API_KEY>
```

> 返回二进制音频流。详细见 `file-management-retrieve` 接口。

## 实战示例（Python）

```python
import os, time, requests

api_key = os.environ["MINIMAX_API_KEY"]
group_id = os.environ["MINIMAX_GROUP_ID"]
headers = {"Authorization": f"Bearer {api_key}"}
BASE = "https://api.minimaxi.com/v1"

# 1. 创建任务
resp = requests.post(
    f"{BASE}/t2a_async_v2?GroupId={group_id}",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "model": "speech-2.8-hd",
        "text": "第一章 ...（超长文本）...",
        "voice_setting": {"voice_id": "presenter_male", "speed": 1, "vol": 1, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    },
)
task_id = resp.json()["task_id"]
print(f"Task created: {task_id}")

# 2. 轮询
while True:
    q = requests.get(f"{BASE}/query/t2a_async_query_v2", headers=headers, params={"task_id": task_id})
    data = q.json()
    status = data["status"]
    print(f"Status: {status}")
    if status == "Success":
        file_id = data["file_id"]
        break
    elif status in ("Failed", "Expired"):
        raise RuntimeError(f"Task {status}: {data}")
    time.sleep(3)  # 避免触发 10/s 限流

# 3. 下载音频
audio = requests.get(f"{BASE}/files/retrieve", headers=headers, params={"file_id": file_id})
with open("output.mp3", "wb") as f:
    f.write(audio.content)
print(f"Saved output.mp3 ({len(audio.content)} bytes)")
```

## 配额与限制

| 项 | 限制 |
|------|------|
| 单请求最大文本 | **1,000,000 字符**（1M） |
| 上传文件大小 | <100 MB（建议） |
| 任务结果保留 | 一般 24 小时（具体看平台） |
| 查询接口限流 | 10 次/秒 |
| 字符数计费 | `usage_characters` 字段（响应里返回） |
