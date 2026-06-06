# minimax-router skill 改进 changelog

## 2026-06-06 改进

### 背景
用户实际使用 music.py 写歌时发现：
1. 旧 SKILL.md "作曲流程" 只问 2 个问题（纯音乐/有歌词），导致风格随机
2. 默认模型是 music-2.5，但最新版是 2.6 且无配额限制
3. `lyrics_optimizer` 默认开启，会改掉用户辛苦写的词
4. music.py 没有 `is_instrumental` 参数支持
5. CLI 防护太严，无法直接调用

### 改动清单

#### SKILL.md
- **重写"作曲流程"章节**（第 60-200 行）
  - 新增 D 方案：智能反推 + 三选一
  - Step 1: 识别意图 + 反推（不堆问询清单）
  - Step 2: 反推不全时给 3 套候选方案让用户选
  - Step 3: 只在用户没明确说时问"人声/纯音乐"
  - Step 4: 歌词处理（默认保护用户歌词，4 种场景处理）
  - Step 5: 参数确认 + 生成
  - 新增歌词模板（强制 `[Verse]/[Chorus]` 标签）
  - 新增失败重试策略表
  - 新增一句话总结
- **更新"模型对应"表格**（第 348-356 行）
  - 默认模型从 music-2.5 → music-2.6
  - 配额从"4 首/天" → "无限制"
  - 保留 music-2.5 作为 fallback 行
- **扩充"脚本/music.py"说明**（第 367-401 行）
  - 标注新参数：`--model / --instrumental / --lyrics-optimizer`
  - 新增完整 CLI 用法示例
  - 新增"调用规范"段（保护机制 + 绕过方式）

#### music.py
- **第 41 行**：默认模型 `music-2.5` → `os.environ.get("MINIMAX_MUSIC_MODEL", "music-2.6")`
- **第 45-50 行**：新增 `is_instrumental` 参数支持（仅 music-2.6+）
- **第 56-60 行**：`lyrics_optimizer` 从默认开启 → 显式开启（`MINIMAX_MUSIC_LYRICS_OPTIMIZER` 默认 false）
- **第 141-156 行**：CLI 放宽
  - 新增 `--model / --instrumental / --lyrics-optimizer` 三个参数
  - 防护逻辑放宽：带 `-l/--instrumental/--model` 时允许直接调用
  - CLI 参数同步到环境变量供 `create_music()` 读取

### 验证
- ✅ Smoke test 4/4 通过
- ✅ CLI `--help` 输出与文档一致
- ✅ 实际生成测试：3.9MB / 2分02秒 / 256kbps 立体声 MP3
- ✅ 目标位置：`D:/Users/goraz/私有空间/88MyWay/01AI学习/AI时代-3句话-歌曲.mp3`

### 文件路径
- SKILL.md: `C:\Users\goraz\.pi\agent\skills\minimax-router\SKILL.md` (398 行)
- music.py: `C:\Users\goraz\.pi\agent\skills\minimax-router\scripts\music.py`
- 临时调试: `C:\Users\goraz\AppData\Local\Temp\music_gen\` (可清理)

## 2026-06-06 追加改进

### music.py 新增 `--bitrate` 参数

- 之前 `audio_setting.bitrate` 硬编码 256000
- 现在可通过 `--bitrate <bps>`（CLI）或 `MINIMAX_MUSIC_BITRATE`（环境变量）覆盖
- 典型用法：`--bitrate 128000` 适合 Lo-fi / 语音 / 不在意高音质的场景
- 默认仍是 256000，向后兼容

