#!/usr/bin/env python3
"""
MiniMax 自动路由脚本
根据用户输入自动判断意图并调用对应模型
"""

import re
import sys
import os
import json
import subprocess
import shutil
import tempfile
import requests
from pathlib import Path

# Python 解释器：Windows 上 python3 可能是 App Store 别名 stub（rc=9009），需实际执行验证
def _detect_py_bin():
    for cand in ("python3", "python"):
        if not shutil.which(cand):
            continue
        try:
            r = subprocess.run([cand, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
            if r.returncode == 0:
                return cand
        except Exception:
            continue
    return sys.executable or "python3"

PY_BIN = _detect_py_bin()

# 临时目录(跨平台:Linux/Mac 是 /tmp,Windows 是 %TEMP%)
TMP_DIR = tempfile.gettempdir()

# 待确认状态文件
PENDING_FILE = os.path.join(TMP_DIR, "minimax_router_pending.json")
CONFIRM_KEYWORDS = ["生成", "确认", "是", "好", "执行", "做吧", "开始"]

def get_pending():
    """读取待确认状态"""
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def save_pending(action, original_input, voice_id=None, params=None):
    """保存待确认状态"""
    from datetime import datetime
    data = {
        "action": action,
        "original_input": original_input,
        "saved_at": datetime.now().isoformat()
    }
    if voice_id:
        data["voice_id"] = voice_id
    if params:
        data["params"] = params
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f)

def clear_pending():
    """清除待确认状态"""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

LOG_FILE = os.path.join(TMP_DIR, "minimax_router_log.json")

def log_action(action, desc):
    """记录操作日志"""
    from datetime import datetime
    entry = {
        "time": datetime.now().strftime("%H:%M"),
        "action": action,
        "desc": desc[:50]
    }
    try:
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        logs.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, ensure_ascii=False)
    except:
        pass

def is_confirm(text):
    """检查是否为确认指令"""
    return any(kw in text for kw in CONFIRM_KEYWORDS)

# 意图关键词定义
INTENT_KEYWORDS = {
    "image": [
        r"生成图片", r"画一张", r"画张", r"生成一张", r"生成图", r"画个图",
        r"帮我画", r"帮我生成图", r"做个图", r"图片", r"图像",
        r"生成图像", r"画一幅", r"画幅", r"生成一幅",
        # "生成N张...图"/"N张...图"这类中间隔着字的匹配
        r"生成.{0,8}图", r"\d+\s*[张幅份个].{0,6}图",
        # 图生图触发词(换风格/换背景/保持人物/角色变体)
        r"换背景", r"换场景", r"换成.*风", r"改成.*风", r"换.*风格", r"转换.*风格",
        r"保持.*人", r"保持.*角色", r"同一个角色", r"同一角色", r"换姿势", r"换衣服",
    ],
    "video": [
        r"生成视频", r"做个视频", r"生成段视频", r"拍一段",
        r"帮我做视频", r"生成视频", r"视频", r"做个短视频",
        # 主体参考视频触发词(让照片动起来/保人脸)
        r"让.*动起", r"动起来", r"让.*走", r"让.*跑", r"让.*跳",
        r"保.*人脸", r"保持.*脸", r"照片.*动", r"照片.*活",
    ],
    "video_audio": [
        r"生成视频.*配音", r"视频.*旁白", r"视频.*音乐",
        r"配音.*视频", r"旁白.*视频", r"音乐.*视频",
        r"生成视频并配音", r"做个.*视频.*配.*"
    ],
    "music": [
        r"写首歌", r"作曲", r"生成音乐", r"生成首歌",
        r"帮我写歌", r"做首歌", r"音乐", r"生成曲",
        r"歌曲", r"首歌", r"写首.*歌", r".*摇滚.*歌"
    ],
    "tts": [
        r"转语音", r"转成语音", r"语音合成", r"读出来",
        r"配音", r"文字转语音", r"转音频", r"生成语音",
        r"播放出来", r"说出来", r"读.*话", r"念.*话",
        r"读这段", r"念这段", r"把这.*读出来"
    ]
}

# 链接词(表示混合意图)
CHAIN_CONNECTORS = [
    r"[,\s]+然后[,\s]+", r"[,\s]+并且[,\s]+", r"[,\s]+再[,\s]+",
    r"[,\s]+接着[,\s]+", r"[,\s]+然后[,\s]+", r"[,\s]+并且[,\s]+",
    r"[\s]+and[\s]+", r"[\s]+&[\s]+", r"[\s]+\+[\s]+",
    r"[--]\s*然后\s*[--]", r"[--]\s*并且\s*[--]"
]

def detect_intent(text):
    """检测单个意图"""
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text, re.IGNORECASE):
                return intent
    return "chat"

def has_chain_pattern(text):
    """检测是否包含链接词"""
    for connector in CHAIN_CONNECTORS:
        if re.search(connector, text, re.IGNORECASE):
            return True
    return False

def split_chain(text):
    """分割混合意图文本"""
    # 使用链接词分割
    pattern = "|".join(CHAIN_CONNECTORS)
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    # 清理每个部分
    result = []
    for part in parts:
        part = part.strip()
        if part:
            result.append(part)
    return result

def detect_intent_for_part(text):
    """检测某部分文本的意图"""
    # 先看是否匹配混合关键词
    intent = detect_intent(text)
    if intent != "chat":
        return intent

    # 特殊处理:看看是不是有"帮我..."开头的请求
    if re.match(r"帮我", text):
        return detect_intent(text)

    return "chat"

def build_image_task(text, img_path=None):
    """构造图片生成任务元组(自动判断文生图/图生图,提取比例/数量)。
    返回 ("__NEED_CONFIRM__", "image", text, params_dict)
    """
    params = {}
    # 图生图:用户有参考图(传入或最近图片)且表达换风格/换背景/保持人物意图
    is_i2i = detect_image_i2i(text)
    ref = None
    if is_i2i:
        urls = extract_image_url(text)
        ref = urls[0] if urls else img_path
        if ref:
            params["ref_path"] = ref
    params["aspect_ratio"] = detect_aspect_ratio(text)
    n = detect_num_images(text)
    if n:
        params["num"] = n
    # 去掉空值
    params = {k: v for k, v in params.items() if v is not None}
    return ("__NEED_CONFIRM__", "image", text, params)

def build_video_task(text, img_path=None):
    """构造视频生成任务元组(自动判断文生/图生/首尾帧/主体参考)。
    返回 ("__NEED_CONFIRM__", "video", text, params_dict)
    """
    params = {}
    urls = extract_image_url(text)
    # 主体参考视频(保人脸)优先级最高
    if detect_video_subject(text):
        ref = urls[0] if urls else img_path
        if ref:
            params["subject_ref"] = ref
    else:
        # 首尾帧:文本里有两个图片 URL
        if len(urls) >= 2:
            params["image_path"] = urls[0]  # execute_video 用 image_path 作首帧
            params["last_frame"] = urls[1]
        elif img_path:
            # 单张图:图生视频首帧
            params["image_path"] = img_path
    # 去掉空值
    params = {k: v for k, v in params.items() if v is not None}
    return ("__NEED_CONFIRM__", "video", text, params)

def get_api_key():
    """获取 API Key"""
    return os.environ.get("MINIMAX_API_KEY", "")

def get_weather_info(location):
    """获取天气信息"""
    try:
        import urllib.request
        url = f"wttr.in/{location}?format=%l:+%c+%t+%h+%w&lang=zh"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode('utf-8')
    except:
        return f"{location}的天气信息"

def execute_image(prompt, ref_path=None, aspect_ratio=None, num=None, prompt_optimizer=False):
    """执行图片生成

    Args:
        prompt: 图像描述
        ref_path: 图生图参考图路径/URL(传入即启用图生图)
        aspect_ratio: 宽高比,如 16:9
        num: 生成数量 1-9
    """
    log_action("image", prompt)
    mode = "图生图" if ref_path else "文生图"
    print(f"[Router] 生成图片({mode}): {prompt[:30]}...", file=sys.stderr)
    if ref_path:
        print(f"[Router] 参考图: {ref_path}", file=sys.stderr)

    # 调用 image.py
    script_path = Path(__file__).parent / "image.py"
    cmd = [PY_BIN, str(script_path), prompt]

    if ref_path:
        cmd.extend(["--ref", ref_path])
    if aspect_ratio:
        cmd.extend(["-s", aspect_ratio])
    if num:
        cmd.extend(["-n", str(num)])
    if prompt_optimizer:
        cmd.append("--optimize")
    cmd.extend(["-o", os.path.join(TMP_DIR, f"image_{os.getpid()}.png")])

    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "image"

    # 如果失败,返回错误
    return f"图片生成失败: {result.stderr}", "error"

# 情绪关键词映射(Speech 2.8 有效值 9 种;bright/relaxed/serious/nervous/gentle 已废弃)
EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "太好了", "哈哈", "耶", "兴奋", "好开心"],
    "sad": ["难过", "伤心", "悲伤", "哭了", "好伤心"],
    "angry": ["生气", "愤怒", "可恶", "讨厌", "气死了"],
    "fearful": ["紧张", "害怕", "担心", "焦虑", "恐惧", "恐怖"],
    "disgusted": ["厌恶", "嫌弃", "反感", "恶心"],
    "surprised": ["哇", "天哪", "真的吗", "惊讶", "震惊"],
    "calm": ["平静", "冷静", "淡定", "从容"],
    "fluent": ["活泼", "轻快", "明亮", "阳光", "生动"],
    "whisper": ["轻声", "低语", "耳语", "ASMR"],
}

# 音色关键词映射(国内版短格式 voice_id,与 references/voices.md 一致)
VOICE_KEYWORDS = {
    "播报男声": "presenter_male",
    "播报": "presenter_male",
    "播报男": "presenter_male",
    "电台男主播": "presenter_male",
    "电台主播": "presenter_male",
    "电台": "presenter_male",
    "新闻女声": "presenter_female",
    "新闻": "presenter_female",
    "温润青年": "male-qn-qingse",
    "温润": "male-qn-qingse",
    "沉稳高管": "male-qn-jingying",
    "沉稳": "male-qn-jingying",
    "甜美女声": "female-tianmei",
    "甜美": "female-tianmei",
    "少女": "female-shaonv",
    "男声": "male-qn-qingse",
    "女声": "female-shaonv",
    "青年": "male-qn-qingse",
    "高管": "male-qn-jingying",
    "Lady": "female-tianmei",
    "Girl": "female-shaonv",
}

def detect_emotion(text):
    """从文本中检测情绪,返回 emotion 值或 None"""
    text_lower = text.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return emotion
    return None

def detect_voice_preference(text):
    """从文本中提取音色偏好,返回 voice_id 或 None"""
    # 模式1: "用电台男主播音/音色/声音" - 提取关键词
    match = re.search(r"用(.+?)音[色声]?", text)
    if match:
        voice_hint = match.group(1).strip()
        for name, vid in VOICE_KEYWORDS.items():
            if name in voice_hint:
                return vid

    # 模式2: 音色:xxx 或 voice:xxx
    match = re.search(r"[音色voice::]+([\w \(\)\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def detect_clone_url(text):
    """从文本中提取音色克隆 URL"""
    # 匹配常见的 URL 格式
    url_pattern = r"https?://[^\s<>\[\]{}\"|^`\\]+"
    matches = re.findall(url_pattern, text)
    for url in matches:
        # 简单验证:看起来像音频文件的 URL
        if any(ext in url.lower() for ext in ['.mp3', '.wav', '.m4a', '.ogg', '.aac', 'voice', 'audio', 'speech']):
            return url
        # 或者包含常见的音频相关关键词
        if any(kw in url.lower() for kw in ['clone', 'reference', 'sample']):
            return url
    return None


# ========== 图片/视频模式意图分类 ==========

# 图生图触发词:用户想基于参考图改风格/换背景/保持人物
IMAGE_I2I_KEYWORDS = [
    r"换背景", r"换场景", r"换成.*风", r"改成.*风", r"转换.*风格", r"换.*风格",
    r"保持.*人", r"保持.*角色", r"这个人在", r"这张.*改成", r"这张.*换",
    r"参照.*图", r"参考.*图", r"基于.*图", r"用.*图.*生成", r"用.*人像",
    r"同一个角色", r"同一角色", r"角色.*变", r"换姿势", r"换衣服",
]

# 主体参考视频触发词:让照片里的人动起来 / 保人脸
VIDEO_SUBJECT_KEYWORDS = [
    r"让.*动起", r"动起来", r"让.*走", r"让.*跑", r"让.*跳",
    r"保.*人脸", r"保持.*脸", r"这个人.*动", r"这张脸",
    r"人脸.*视频", r"照片.*动", r"照片.*活",
]

# 宽高比提取
ASPECT_RATIO_MAP = {
    "1:1": [r"1:1", r"正方", r"方形"],
    "16:9": [r"16:9", r"横版", r"横屏", r"宽屏", r"宽图"],
    "9:16": [r"9:16", r"竖版", r"竖屏", r"手机图", r"抖音图"],
    "4:3": [r"4:3"],
    "3:4": [r"3:4", r"竖版照片"],
    "3:2": [r"3:2"],
    "2:3": [r"2:3"],
    "21:9": [r"21:9", r"超宽", r"电影宽屏"],
}

def detect_image_i2i(text):
    """判断是否为图生图意图(换风格/换背景/保持人物)"""
    for kw in IMAGE_I2I_KEYWORDS:
        if re.search(kw, text, re.IGNORECASE):
            return True
    return False

def detect_video_subject(text):
    """判断是否为主体参考视频意图(保人脸/让照片动起来)"""
    for kw in VIDEO_SUBJECT_KEYWORDS:
        if re.search(kw, text, re.IGNORECASE):
            return True
    return False

def detect_aspect_ratio(text):
    """从文本提取宽高比,返回如 '16:9' 或 None"""
    for ratio, patterns in ASPECT_RATIO_MAP.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return ratio
    return None

def detect_num_images(text):
    """从文本提取生成数量,如"生成4张""画3幅"返回对应数,否则 None"""
    m = re.search(r"(?:生成|画|做|出)?\s*(\d)\s*[张幅个]", text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 9:
            return n
    return None

def extract_image_url(text):
    """从文本中提取图片 URL(用于参考图/首尾帧/主体参考)"""
    matches = re.findall(r"https?://[^\s<>\[\]{}\"|^`\\]+", text)
    image_urls = []
    for url in matches:
        low = url.lower()
        if any(ext in low for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']) or 'image' in low or 'filecdn' in low:
            image_urls.append(url)
    return image_urls


def execute_tts(text, voice_id=None, emotion=None, clone_url=None, enable_filler_words=False):
    """执行语音合成

    Args:
        text: 要转换的文本
        voice_id: 音色 ID (可选)
        emotion: 情绪标签 (可选)
        clone_url: 音色克隆 URL (可选)
        enable_filler_words: 是否启用语气词 (可选)
    """
    # 如果未指定音色,尝试从文本中提取
    if voice_id is None:
        voice_id = detect_voice_preference(text)

    # 如果未指定情绪,尝试从文本中检测
    if emotion is None:
        detected = detect_emotion(text)
        if detected:
            emotion = detected
            print(f"[Router] 检测到情绪: {detected}", file=sys.stderr)

    # 如果未指定克隆 URL,尝试从文本中提取
    if clone_url is None:
        clone_url = detect_clone_url(text)

    print(f"[Router] 语音合成: {text[:30]}...", file=sys.stderr)
    if voice_id:
        print(f"[Router] 使用音色: {voice_id}", file=sys.stderr)
    if emotion:
        print(f"[Router] 使用情绪: {emotion}", file=sys.stderr)
    if clone_url:
        print(f"[Router] 使用音色克隆: {clone_url[:50]}...", file=sys.stderr)
    if enable_filler_words:
        print(f"[Router] 启用语气词", file=sys.stderr)

    script_path = Path(__file__).parent / "tts.py"
    cmd = [PY_BIN, str(script_path), text]

    if voice_id:
        cmd.extend(["-v", voice_id])
    if emotion:
        cmd.extend(["-e", emotion])
    if clone_url:
        cmd.extend(["--clone-url", clone_url])
    if enable_filler_words:
        cmd.append("--filler-words")

    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "tts"

    return f"语音生成失败: {result.stderr}", "error"

def execute_video(prompt, image_path=None, duration=6, resolution="1080P",
                     last_frame=None, subject_ref=None):
    """执行视频生成

    Args:
        prompt: 视频描述
        image_path: 首帧图(图生视频 / 首尾帧)
        last_frame: 尾帧图(首尾帧视频,需配合 image_path)
        subject_ref: 人脸照 URL(主体参考视频 S2V-01)
    """
    log_action("video", prompt)
    if subject_ref:
        mode = "主体参考视频(S2V-01,保人脸)"
    elif image_path and last_frame:
        mode = "首尾帧视频(Hailuo-02)"
    elif image_path:
        mode = "图生视频"
    else:
        mode = "文生视频"
    print(f"[Router] 生成视频({mode}): {prompt[:30]}...", file=sys.stderr)

    # 主体参考优先用 subject_ref;否则首帧图用 image_path 或最近图片
    if not subject_ref and not image_path:
        image_path = get_last_image()

    script_path = Path(__file__).parent / "video.py"
    cmd = [PY_BIN, str(script_path), prompt]

    if image_path:
        cmd.extend(["-i", image_path])
    if last_frame:
        cmd.extend(["--last-frame", last_frame])
    if subject_ref:
        cmd.extend(["--subject-ref", subject_ref])

    cmd.extend(["-d", str(duration), "-r", resolution])
    cmd.extend(["-o", os.path.join(TMP_DIR, f"video_{os.getpid()}.mp4")])

    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "video"

    return f"视频生成失败: {result.stderr}", "error"

def execute_video_audio(video_desc, narration_text, music_desc=None, image_path=None):
    """执行视频+配音+音乐生成"""
    log_action("video_audio", video_desc)
    print(f"[Router] 生成视频+配音+音乐: {video_desc[:30]}...", file=sys.stderr)

    # 如果没有指定图片,尝试使用最近的图片
    if not image_path:
        image_path = get_last_image()

    script_path = Path(__file__).parent / "video_with_audio.py"
    cmd = [PY_BIN, str(script_path), video_desc, narration_text]

    if music_desc:
        cmd.append(music_desc)

    if image_path:
        cmd.extend(["--image", image_path])

    cmd.extend(["-o", os.path.join(TMP_DIR, f"final_video_{os.getpid()}.mp4")])

    result = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "video_audio"

    return f"视频+音频生成失败: {result.stderr}", "error"

def execute_music(prompt):
    """执行音乐生成"""
    log_action("music", prompt)
    print(f"[Router] 生成音乐: {prompt[:30]}...", file=sys.stderr)

    script_path = Path(__file__).parent / "music.py"
    result = subprocess.run(
        [PY_BIN, str(script_path), "-p", prompt],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "music"

    return f"音乐生成失败: {result.stderr}", "error"

def execute_chat(text):
    """执行对话(直接返回文本)"""
    print(f"[Router] 对话模式: {text[:30]}...", file=sys.stderr)
    # 对话模式不需要在这里处理,由 Agent 决定
    return text, "text"

LAST_IMAGE_FILE = os.path.join(TMP_DIR, "last_received_image.jpg")

def save_last_image(image_path):
    """保存最近收到的图片路径"""
    try:
        import shutil
        shutil.copy(image_path, LAST_IMAGE_FILE)
        print(f"[Router] 已保存最近图片: {LAST_IMAGE_FILE}", file=sys.stderr)
    except Exception as e:
        print(f"[Router] 保存图片失败: {e}", file=sys.stderr)

def get_last_image():
    """获取最近收到的图片路径"""
    if os.path.exists(LAST_IMAGE_FILE):
        return LAST_IMAGE_FILE
    return None

def route(user_input, context_image_path=None):
    """
    主路由函数
    context_image_path: 最近收到的图片路径(用于自动使用)
    返回: (result, type) 或 [(result1, type1), (result2, type2), ...]
    """
    original_input = user_input.strip()

    # 检查是否以斜杠命令开头
    slash_match = re.match(r"^/(c|t|v|m|i)[\s]*(.*)$", original_input, re.DOTALL)
    if slash_match:
        cmd = slash_match.group(1)
        content = slash_match.group(2).strip()

        # 获取图片路径:优先用传入的,其次用最近的
        img_path = context_image_path or get_last_image()

        if cmd == "c":
            return [execute_chat(content)]
        elif cmd == "t":
            # 支持 /t voice_id:内容 格式,voice_id 允许包含空格和括号
            voice_match = re.match(r"^([\w \(\)\-]+):(.+)$", content)
            if voice_match:
                voice_id, text = voice_match.group(1), voice_match.group(2).strip()
                return [("__NEED_CONFIRM__", "tts", text, voice_id, voice_id)]
            voice_id = detect_voice_preference(content)
            voice_name = voice_id.split("_")[-1] if voice_id else "默认"
            return [("__NEED_CONFIRM__", "tts", content, voice_id, voice_name)]
        elif cmd == "v":
            return [build_video_task(content, img_path)]
        elif cmd == "m":
            return [("__NEED_CONFIRM__", "music", content)]
        elif cmd == "i":
            return [build_image_task(content, img_path)]

    # 检测混合意图
    if has_chain_pattern(original_input):
        parts = split_chain(original_input)
        if len(parts) > 1:
            print(f"[Router] 检测到混合意图,分成 {len(parts)} 部分", file=sys.stderr)
            results = []
            last_description = ""
            img_path = context_image_path or get_last_image()

            for i, part in enumerate(parts):
                intent = detect_intent_for_part(part)

                if intent == "tts" and last_description:
                    # TTS following another step - use the description from previous step
                    print(f"[Router] TTS 紧随生成步骤,使用描述: {last_description[:30]}...", file=sys.stderr)
                    results.append(execute_tts(last_description))
                elif intent == "image":
                    results.append(build_image_task(part, img_path))
                    last_description = part
                elif intent == "video":
                    results.append(build_video_task(part, img_path))
                    last_description = part
                    img_path = None  # 使用后清除
                elif intent == "music":
                    results.append(("__NEED_CONFIRM__", "music", part))
                elif intent == "tts":
                    results.append(execute_tts(part))
                else:
                    results.append(execute_chat(part))

            return results

    # 单意图
    img_path = context_image_path or get_last_image()
    intent = detect_intent(original_input)

    if intent == "image":
        # 需要确认,返回特殊标记
        return [build_image_task(original_input, img_path)]
    elif intent == "video_audio":
        # 需要确认,返回特殊标记
        return [("__NEED_CONFIRM__", "video_audio", original_input)]
    elif intent == "video":
        return [build_video_task(original_input, img_path)]
    elif intent == "music":
        return [("__NEED_CONFIRM__", "music", original_input)]
    elif intent == "tts":
        voice_id = detect_voice_preference(original_input)
        voice_name = voice_id.split("_")[-1] if voice_id else "默认"
        return [("__NEED_CONFIRM__", "tts", original_input, voice_id, voice_name)]
    else:
        # 检查是否需要先查天气等信息
        if any(kw in original_input for kw in ["天气", "weather", "查一下", "帮我查"]):
            location = extract_location(original_input)
            weather = get_weather_info(location)
            return [execute_tts(weather)]
        return [execute_chat(original_input)]

def parse_video_audio_request(text):
    """
    解析视频+配音+音乐的请求
    尝试提取:视频描述、旁白文字、背景音乐描述
    """
    # 移除意图关键词
    text = re.sub(r"生成视频.*?配音", "", text)
    text = re.sub(r"视频.*?旁白", "", text)
    text = re.sub(r"视频.*?音乐", "", text)
    text = re.sub(r"做个.*视频.*配.*", "", text)

    # 尝试分割各部分
    # 常见模式:描述 + 旁白 + 音乐
    parts = re.split(r"[,,、]", text)

    video_desc = text  # 默认整个作为视频描述
    narration = "这是一个精彩的视频"  # 默认旁白
    music_desc = "轻快的背景音乐"  # 默认背景音乐

    # 简单策略:前三部分分别作为视频、旁白、音乐
    if len(parts) >= 3:
        video_desc = parts[0].strip()
        narration = parts[1].strip()
        music_desc = parts[2].strip()
    elif len(parts) == 2:
        video_desc = parts[0].strip()
        narration = parts[1].strip()
        music_desc = None
    else:
        # 尝试从文本中提取
        narration_match = re.search(r"旁白[是为::]*([^.!!]+)", text)
        music_match = re.search(r"音乐[是为::]*([^.!!]+)", text)

        if narration_match:
            narration = narration_match.group(1).strip()
        if music_match:
            music_desc = music_match.group(1).strip()

    return video_desc, narration, music_desc

def extract_location(text):
    """提取地点"""
    # 简单的地点提取
    patterns = [
        r"(.*)的天气",
        r"天气怎么样",
        r"(.+)天气",
        r"(福州|北京|上海|深圳|广州|杭州|成都|武汉|西安|南京)"
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1) if m.lastindex else "福州"
    return "福州"  # 默认

def main():
    if len(sys.argv) < 2:
        print("用法: python router.py <用户输入>")
        print("      python router.py --save-image <图片路径>")
        print("      python router.py --image <图片路径> <用户输入>")
        sys.exit(1)

    args = sys.argv[1:]
    context_image = None

    # 处理特殊参数
    if "--save-image" in args:
        idx = args.index("--save-image")
        img_path = args[idx + 1]
        save_last_image(img_path)
        print(f"已保存最近图片: {img_path}")
        return

    if "--image" in args:
        idx = args.index("--image")
        context_image = args[idx + 1]
        # 移除这两个参数
        args = args[:idx] + args[idx + 2:]

    user_input = " ".join(args) if args else ""
    if not user_input:
        print("错误: 请提供输入内容")
        sys.exit(1)

    # 检查是否有待确认的生成任务
    pending = get_pending()
    if pending and is_confirm(user_input):
        # 用户确认了,执行之前保存的任务
        action = pending.get("action", "")
        original_input = pending.get("original_input", "")
        voice_id = pending.get("voice_id")
        params = pending.get("params", {}) or {}
        clear_pending()
        if action == "image":
            log_action("image", original_input)
            result, rtype = execute_image(
                original_input,
                ref_path=params.get("ref_path"),
                aspect_ratio=params.get("aspect_ratio"),
                num=params.get("num"),
            )
        elif action == "music":
            log_action("music", original_input)
            result, rtype = execute_music(original_input)
        elif action == "video" or action == "video_audio":
            log_action("video", original_input)
            # 主体参考/首尾帧优先用 pending 里的 params;否则用 context_image 作首帧
            result, rtype = execute_video(
                original_input,
                image_path=params.get("image_path") or context_image,
                last_frame=params.get("last_frame"),
                subject_ref=params.get("subject_ref"),
            )
        elif action == "tts":
            log_action("tts", original_input)
            result, rtype = execute_tts(original_input, voice_id=voice_id)
        else:
            result, rtype = execute_chat(original_input)
        # 直接执行并返回结果
        if rtype == "error":
            print(f"错误: {result}")
        elif rtype == "text":
            print(result)
        else:
            print(result)
        return

    # 正常路由流程
    results = route(user_input, context_image_path=context_image)

    # 检查结果中是否有需要确认的生成操作
    needs_confirm = False
    confirmed_action = None
    for i, item in enumerate(results):
        if item[0] == "__NEED_CONFIRM__":
            # 需要确认,先保存状态,不执行
            action = item[1]
            original_input = item[2]
            voice_id = None
            params = None
            # tts: item[3]=voice_id; image/video: item[3]=params_dict
            if action == "tts":
                voice_id = item[3] if len(item) > 3 else None
            elif action in ("image", "video"):
                params = item[3] if len(item) > 3 else None
            save_pending(action, original_input, voice_id=voice_id, params=params)
            needs_confirm = True
            confirmed_action = action
            break

    if needs_confirm:
        if confirmed_action == "tts":
            voice_name = None
            for item in results:
                if item[0] == "__NEED_CONFIRM__" and item[1] == "tts":
                    voice_name = item[4] if len(item) > 4 else "默认"
                    break
            print(f"⚠️ 语音合成已准备好(音色:{voice_name})。")
        else:
            action_names = {"image": "图片", "music": "音乐", "video": "视频", "video_audio": "视频+配音+音乐"}
            # 显示识别出的模式细节(图生图/主体参考/首尾帧等)
            detail = ""
            for item in results:
                if item[0] == "__NEED_CONFIRM__" and item[1] in ("image", "video") and len(item) > 3:
                    p = item[3] or {}
                    if item[1] == "image":
                        if p.get("ref_path"):
                            detail = f"[图生图]"
                        else:
                            detail = "[文生图]"
                        if p.get("aspect_ratio"):
                            detail += f" 比例:{p['aspect_ratio']}"
                    elif item[1] == "video":
                        if p.get("subject_ref"):
                            detail = "[主体参考视频 S2V-01 保人脸]"
                        elif p.get("last_frame"):
                            detail = "[首尾帧视频 Hailuo-02]"
                        elif p.get("image_path"):
                            detail = "[图生视频]"
                        else:
                            detail = "[文生视频]"
                    break
            suffix = f" {detail}" if detail else ""
            print(f"⚠️ {action_names.get(confirmed_action, confirmed_action)}生成已准备好{suffix}。")
        print(f"回复「生成」确认执行,其他内容取消。")
        return

    # 普通输出
    for i, (result, rtype) in enumerate(results):
        if rtype == "error":
            print(f"错误: {result}")
        elif rtype == "text":
            print(result)
        else:
            # 文件路径
            print(result)

if __name__ == "__main__":
    main()
