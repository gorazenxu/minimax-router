# MiniMax API 错误码速查

> 完整文档：<https://platform.minimaxi.com/docs/api-reference/errorcode>
>
> 任何错误响应都包含 `base_resp.status_code` 和 `base_resp.status_msg`，**调通后请记下 trace_id（Header 里）便于排查**。

## 通用错误（所有接口）

| 错误码 | 含义 | 解决方法 |
|------|------|---------|
| 0 | 成功 | — |
| 1000 | 未知错误 / 系统默认错误 | 稍后重试 |
| 1001 | 请求超时 | 稍后重试；或调大客户端 timeout |
| 1002 | 请求频率超限 | 降低 QPS；查具体接口限流 |
| 1004 | 未授权 / Token 不匹配 / Cookie 缺失 | **检查 API Key**，确认 `MINIMAX_API_KEY` 环境变量正确 |
| 1008 | 余额不足 | **充值**账户 |
| 1024 | 内部错误 | 稍后重试；持续失败联系 support |
| 1026 | 输入内容涉敏 | 调整输入文本（涉政/涉黄/涉暴等）|
| 1027 | 输出内容涉敏 | 调整 prompt 让模型输出合规内容 |
| 1033 | 系统错误 / 下游服务错误 | 稍后重试 |
| 1039 | Token 限制 | 调小 `max_tokens` 参数 |
| 1041 | 连接数限制 | 联系 MiniMax 客服扩容 |
| 1042 | 不可见字符比例超限（非法字符 > 10%）| 检查输入文本，删除不可见字符 / 异常符号 |
| 2013 | 参数错误 | 检查必填字段、类型、取值范围 |
| 2045 | 请求频率增长超限 | 避免 QPS 骤增骤减，加平滑限流 |
| 2049 | 无效的 API Key | 检查 API Key 是否过期、是否复制完整 |
| 2056 | 超出 Token Plan 资源限制 | 等待下一个时间段（一般是下一天）资源释放 |

## TTS 语音合成相关

| 错误码 | 含义 | 解决方法 |
|------|------|---------|
| 20132 | 语音克隆样本或 voice_id 参数错误 | 检查 Voice Cloning 的 `file_id` 和 T2A v2 的 `voice_id` |
| 2037 | 语音时长不符 | voice_clone 的 file_id 时长需在 10s-5min |
| 2038 | 语音克隆功能被禁用 | 在「账户管理 → 账户信息」做个人/企业认证 |
| 2039 | 语音克隆 voice_id 重复 | 换一个未用过的 voice_id |
| 2042 | 无权访问该 voice_id | 必须是自己创建的 voice_id |
| 2048 | 语音克隆提示音频太长 | 国际版字段，`prompt_audio` < 8s |
| 1043 | ASR 相似度检查失败 | 检查 `file_id` 与 `text_validation` 匹配度（克隆时） |
| 1044 | 克隆提示词相似度检查失败 | 检查克隆提示音频和 prompt 文本的匹配度 |

## WebSocket TTS 特有

| 事件 | 含义 | 含义 |
|------|------|------|
| `task_failed` | 任务失败 | 看 `base_resp.status_code` 对应上表错误码 |
| `connected_success` | 建连成功 | — |

> WebSocket 没有自己的错误码表，复用 HTTP 的 `status_code`。

## 调试建议

### 1. 始终记录 trace_id

```
response.headers["trace_id"]  // 报错时附给客服
```

### 2. 按错误码速查表自查

| 现象 | 优先查 |
|------|------|
| 401 / 1004 / 2049 | API Key 问题 |
| 402 / 1008 | 充值 |
| 429 / 1002 / 2045 | 限流（降 QPS 或加 sleep）|
| 413 / 1042 | 文本太长或含非法字符 |
| 1008 | 余额 |
| 20132 / 2037 / 2039 | 克隆相关（看 `voice-cloning.md`）|
| 1001 | 网络/超时 |

### 3. 配额 vs 限流 vs 余额

| 错误 | 含义 |
|------|------|
| 1002 | 单接口 QPS 超限（按接口计算）|
| 2045 | QPS 增长率超限（防突发）|
| 2056 | Token Plan 总量超限（日/总量）|
| 1008 | 余额不足（需充值）|

查询实时配额：
```bash
curl -H "Authorization: Bearer <API_KEY>" \
  "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains"
```

或用 skill 自带的脚本：
```bash
python scripts/check_quota.py
```

### 4. 报错时给用户看的友好提示模板

```
❌ 语音合成失败 (错误码 1008)
原因：账户余额不足
解决：请到 https://platform.minimaxi.com/user-center 充值
Trace ID: 01b8bf9bb7433cc75c18eee6cfa8fe21（请联系客服时附上）
```
