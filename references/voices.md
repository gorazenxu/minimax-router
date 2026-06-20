# TTS 音色 ID 速查表

> 完整文档：<https://platform.minimaxi.com/docs/api-reference/speech-t2a-http>
>
> 本表只列国内版（`api.minimaxi.com`）常用音色。国际版（`api.minimax.io`）的 voice_id 完全不同（如 `English_expressive_narrator`），详见官方文档。

## SKILL.md 推荐名 → voice_id 映射

SKILL.md 引导流程里用的 5 个"中文营销名"对应的真实 `voice_id`：

| 序号 | 推荐名（SKILL.md 用） | voice_id（API 参数） | 音色气质 |
|------|---------------------|--------------------|---------|
| ① | 电台男主播 | `presenter_male` | FM 财经播报，节奏专业 |
| ② | 沉稳高管 | `male-qn-jingying` | 精英青年，商务权威 |
| ③ | 新闻女声 | `presenter_female` | 正式播音，信任感强 |
| ④ | 温润青年 | `male-qn-qingse` | 青涩男声，亲切自然 |
| ⑤ | 甜美女声 | `female-tianmei` | 甜美女性，柔和舒适 |

> ⚠️ AI 推荐音色后，调用 API 时必须用 `voice_id` 字段传真实 ID（如 `presenter_male`），不要传中文名。

## 完整 voice_id 列表（国内版）

### 通用男声

| voice_id | 名称 | 适合 |
|----------|------|------|
| `male-qn-qingse` | 青涩青年音色 | 通用男声 / 故事 |
| `male-qn-jingying` | 精英青年音色 | 商务 / 演讲 |
| `male-qn-badao` | 霸道青年音色 | 角色 / 影视 |
| `male-qn-daxuesheng` | 青年大学生音色 | 学生 / 校园 |

### 通用女声

| voice_id | 名称 | 适合 |
|----------|------|------|
| `female-shaonv` | 少女音色 | 通用女声 / 活泼 |
| `female-yujie` | 御姐音色 | 成熟 / 强势 |
| `female-chengshu` | 成熟女性音色 | 沉稳 / 优雅 |
| `female-tianmei` | 甜美女性音色 | 温柔 / 治愈 |

### 主持人 / 播报

| voice_id | 名称 | 适合 |
|----------|------|------|
| `presenter_male` | 男性主持人 | 新闻 / 财经播报 |
| `presenter_female` | 女性主持人 | 新闻 / 公告 |

### 有声书

| voice_id | 名称 | 适合 |
|----------|------|------|
| `audiobook_male_1` | 男性有声书 1 | 长文朗读 |
| `audiobook_male_2` | 男性有声书 2 | 长文朗读 |
| `audiobook_female_1` | 女性有声书 1 | 长文朗读 |
| `audiobook_female_2` | 女性有声书 2 | 长文朗读 |

### 儿童

| voice_id | 名称 | 适合 |
|----------|------|------|
| `clever_boy` | 聪明男童 | 儿童内容 |
| `cute_boy` | 可爱男童 | 儿童内容 |
| `lovely_girl` | 萌萌女童 | 儿童内容 |

### 角色 / 二次元

| voice_id | 名称 | 适合 |
|----------|------|------|
| `cartoon_pig` | 卡通猪小琪 | 动画 |
| `bingjiao_didi` | 病娇弟弟 | 角色 |
| `junlang_nanyou` | 俊朗男友 | 言情 |
| `chunzhen_xuedi` | 纯真学弟 | 言情 |
| `lengdan_xiongzhang` | 冷淡学长 | 言情 |
| `badao_shaoye` | 霸道少爷 | 言情 |

### 精品 beta（*-jingpin 后缀）

在通用音色 ID 后加 `-jingpin` 后缀是"精品版"（音质更细、表现力更强），如 `male-qn-qingse-jingpin`、`female-tianmei-jingpin` 等。所有通用音色都有对应的精品版。

## 音色克隆（voice cloning）

用户想用自己的声音时：

1. 先在 MiniMax 平台「音色复刻」页面上传参考音频（建议 10 秒以上、清晰无噪音）
2. 平台训练完成后会给一个**复刻音色 ID**
3. 调用 API 时把 `voice_setting.voice_id` 设为这个 ID
4. 配额按平台「复刻音色」档位计算（不一定算在通用语音配额内）

完整流程：<https://platform.minimaxi.com/docs/api-reference/voice-cloning>

## 常用参数取值

| 字段 | 取值范围 | 默认 | 说明 |
|------|---------|------|------|
| `speed` | [0.5, 2] | 1.0 | 语速，1.0 为原速 |
| `vol` | (0, 10] | 1.0 | 音量，1.0 为原音量 |
| `pitch` | [-12, 12] | 0 | 语调，0 为原音色（**必须整数**） |
| `emotion` | `happy` / `sad` / `angry` / `fearful` / `disgusted` / `surprised` / `calm` / `fluent` / `whisper` | — | Speech 2.8 支持 9 种；默认 calm |

## 文本特殊标记

| 标记 | 效果 |
|------|------|
| `\n` | 段落切换（换行） |
| `<#x#>` | 字间停顿 x 秒（0.01-99.99），**必须放在两个可发音文本之间** |
| `(laughs)` | 插入笑声 |
| `(sighs)` | 插入叹气 |
| `(breath)` | 插入呼吸声 |

> 文本长度限制 **<10000 字符**（HTTP 同步接口）。超长文本用异步任务接口 `speech-t2a-async-create`。
