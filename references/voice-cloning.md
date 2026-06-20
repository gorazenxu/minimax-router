# 音色克隆（Voice Cloning）

> 适用场景：用自己的声音做配音、角色专属音色、品牌专属音色
>
> 官方指南：<https://platform.minimaxi.com/docs/guides/speech-voice-clone>

## 三步流程

```
1. 上传参考音频    POST /v1/files/upload?GroupId=xxx     → file_id
2. 调用克隆接口    POST /v1/voice_clone?GroupId=xxx      → 试听音频 + voice_id
3. 使用克隆音色    在 T2A v2 / T2A Async v2 里把 voice_setting.voice_id 设为克隆的 ID
```

## 音频要求

| 项 | 要求 |
|------|------|
| 格式 | MP3 / M4A / WAV |
| 时长 | **10 秒 ~ 5 分钟**（10s 太短会失败，>5min 太长会失败）|
| 大小 | < 20 MB |
| 质量 | 清晰无背景噪音、无回声、无 BGM（**先降噪**）|
| 语种 | 中文 / 英文 / 17+ 语种 |

> ⚠️ 时长不符会触发错误码 **2037**。噪音大可能触发 **1043 ASR 相似度失败**。

## 接口 1：上传参考音频

```
POST https://api.minimaxi.com/v1/files/upload?GroupId=<group_id>
Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data

form-data:
  purpose: voice_clone
  file: <音频文件，mp3/m4a/wav>
```

**响应：**
```json
{
  "file": { "file_id": 196553532456675664 },
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

## 接口 2：克隆音色

```
POST https://api.minimaxi.com/v1/voice_clone?GroupId=<group_id>
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

### 请求体

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `file_id` | ✅ | integer | 上一步拿到的 file_id |
| `voice_id` | ✅ | string | **自定义 ID，必须 ≥8 字符、字母+数字、字母开头** |
| `noise_reduction` | ❌ | bool | 是否降噪，默认 `false` |
| `need_volume_normalization` | ❌ | bool | 是否音量归一化，默认 `false` |
| `text` | ❌ | string | 试听文本（≤300 字符），用克隆的音色读这段话返回试听音频 |
| `model` | ❌ | string | 试听用 TTS 模型，默认 `speech-01-turbo` |
| `accuracy` | ❌ | number | 文本验证阈值，默认 `0.7`（0-1）|

### voice_id 命名规则

| 规则 | 示例 |
|------|------|
| ≥8 字符 | ✅ `MarketingVoice123` |
| 字母开头 | ✅ `BrandA2026` |
| 字母+数字混合 | ❌ 只用数字（`12345678` 失败）|
| 唯一 | 不能和已有 voice_id 重复（错误码 2039）|

### 响应

```json
{
  "input_sensitive": false,
  "input_sensitive_type": null,
  "demo_audio": "1234567890abcdef...",   // 试听音频 hex
  "base_resp": { "status_code": 0, "status_msg": "success" }
}
```

> `demo_audio` 是 hex 编码的试听音频，前端拿到后 `bytes.fromhex()` 解码。

## 接口 3：使用克隆音色

把克隆得到的 `voice_id` 填到 T2A 接口的 `voice_setting.voice_id` 字段：

```json
{
  "model": "speech-2.8-hd",
  "text": "这段话会用我自己的声音读",
  "voice_setting": {
    "voice_id": "MarketingVoice123"
  }
}
```

## ⚠️ 重要约束：7 天保活

> **克隆后的 voice_id 必须在 7 天内至少使用一次，否则自动删除。**

"使用一次" = 在 T2A v2 / T2A Async v2 任意接口里传这个 `voice_id` 跑过一次合成。

**保活策略：**
- 长期项目：定时（每 6 天）用这个 voice_id 合成 1 秒的 dummy 文本
- 短期项目：忽略这个限制，7 天内用完即可

## 完整 Python 示例

```python
import os, requests, base64

api_key = os.environ["MINIMAX_API_KEY"]
group_id = os.environ["MINIMAX_GROUP_ID"]
headers = {"Authorization": f"Bearer {api_key}"}
BASE = "https://api.minimaxi.com/v1"

# 1. 上传参考音频
with open("/path/to/my_voice_sample.mp3", "rb") as f:
    up = requests.post(
        f"{BASE}/files/upload?GroupId={group_id}",
        headers=headers,
        data={"purpose": "voice_clone"},
        files={"file": f},
    )
file_id = up.json()["file"]["file_id"]

# 2. 克隆音色
resp = requests.post(
    f"{BASE}/voice_clone?GroupId={group_id}",
    headers=headers,
    json={
        "file_id": file_id,
        "voice_id": "MyCustomVoice2026",   # ≥8 字符，字母+数字
        "noise_reduction": True,
        "need_volume_normalization": True,
        "text": "这是一段试听文本，用来测试克隆效果。",
        "accuracy": 0.7,
    },
)
demo_hex = resp.json()["demo_audio"]

# 3. 保存试听音频
with open("preview.mp3", "wb") as f:
    f.write(bytes.fromhex(demo_hex))
print(f"Preview saved, voice_id=MyCustomVoice2026")
```

## 常见错误（克隆相关）

| 错误码 | 含义 | 解决 |
|------|------|------|
| **20132** | file_id 或 voice_id 参数错 | 检查上传返回的 file_id、voice_id 命名规则 |
| **2037** | 时长不符 | 音频在 10s-5min 范围 |
| **2038** | 克隆功能被禁用 | 账户需要完成个人/企业实名认证 |
| **2039** | voice_id 重复 | 换一个未用过的 voice_id |
| **2042** | 无权访问 | 只能用自己的 voice_id |
| **2048** | 提示音频太长 | 这是国际版字段，prompt_audio < 8s |
| **2049** | API Key 无效 | 检查环境变量 |
| **1043** | ASR 相似度检查失败 | 音频太模糊，重录一段更清晰的 |
| **1044** | 克隆提示词相似度检查失败 | prompt 文本和音频内容不匹配 |

## 国内版 vs 国际版

| 项 | 国内版（`api.minimaxi.com`）| 国际版（`api.minimax.io`）|
|------|---------------------------|--------------------------|
| URL 路径 | `/v1/voice_clone` | `/v1/voice_clone` |
| GroupId | 必填（拼 URL 末尾）| 必填 |
| 音频要求 | 10s-5min | 相同 |
| 7 天保活 | 是 | 是 |
| 认证要求 | 需个人/企业认证 | 需账号认证 |
