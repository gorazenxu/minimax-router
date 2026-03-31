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
import requests
from pathlib import Path

# 待确认状态文件
PENDING_FILE = "/tmp/minimax_router_pending.json"
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

def save_pending(action, original_input, voice_id=None):
    """保存待确认状态"""
    from datetime import datetime
    data = {
        "action": action,
        "original_input": original_input,
        "saved_at": datetime.now().isoformat()
    }
    if voice_id:
        data["voice_id"] = voice_id
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f)

def clear_pending():
    """清除待确认状态"""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

LOG_FILE = "/tmp/minimax_router_log.json"

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
        r"生成图片", r"画一张", r"生成一张", r"生成图", r"画个图",
        r"帮我画", r"帮我生成图", r"做个图", r"图片", r"图像",
        r"生成图像", r"画一幅", r"生成一幅"
    ],
    "video": [
        r"生成视频", r"做个视频", r"生成段视频", r"拍一段",
        r"帮我做视频", r"生成视频", r"视频", r"做个短视频"
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

# 链接词（表示混合意图）
CHAIN_CONNECTORS = [
    r"[,\s]+然后[,\s]+", r"[,\s]+并且[,\s]+", r"[,\s]+再[,\s]+",
    r"[,\s]+接着[,\s]+", r"[，\s]+然后[，\s]+", r"[，\s]+并且[，\s]+",
    r"[\s]+and[\s]+", r"[\s]+&[\s]+", r"[\s]+\+[\s]+",
    r"[-—]\s*然后\s*[-—]", r"[-—]\s*并且\s*[-—]"
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
    
    # 特殊处理：看看是不是有"帮我..."开头的请求
    if re.match(r"帮我", text):
        return detect_intent(text)
    
    return "chat"

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

def execute_image(prompt):
    """执行图片生成"""
    log_action("image", prompt)
    print(f"[Router] 生成图片: {prompt[:30]}...", file=sys.stderr)
    
    # 调用 image.py
    script_path = Path(__file__).parent / "image.py"
    result = subprocess.run(
        ["python3", str(script_path), prompt],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "image"
    
    # 如果失败，返回错误
    return f"图片生成失败: {result.stderr}", "error"

def detect_voice_preference(text):
    """从文本中提取音色偏好，返回 voice_id 或 None"""
    # 模式1: "用电台男主播音/音色/声音" - 提取关键词
    match = re.search(r"用(.+?)音[色声]?", text)
    if match:
        voice_hint = match.group(1).strip()
        KNOWN_VOICES = {
            "播报男声": "Chinese (Mandarin)_Male_Announcer",
            "播报": "Chinese (Mandarin)_Male_Announcer",
            "播报男": "Chinese (Mandarin)_Male_Announcer",
            "电台男主播": "Chinese (Mandarin)_Radio_Host",
            "电台主播": "Chinese (Mandarin)_Radio_Host",
            "电台": "Chinese (Mandarin)_Radio_Host",
            "新闻女声": "Chinese (Mandarin)_News_Anchor",
            "新闻": "Chinese (Mandarin)_News_Anchor",
            "温润青年": "Chinese (Mandarin)_Gentle_Youth",
            "温润": "Chinese (Mandarin)_Gentle_Youth",
            "沉稳高管": "Chinese (Mandarin)_Reliable_Executive",
            "沉稳": "Chinese (Mandarin)_Reliable_Executive",
            "甜美女声": "Chinese (Mandarin)_Sweet_Lady",
            "甜美": "Chinese (Mandarin)_Sweet_Lady",
            "少女": "female-shaonv",
            "男声": "male-qn-qingse",
            "女声": "female-shaonv",
        }
        for name, vid in KNOWN_VOICES.items():
            if name in voice_hint:
                return vid
    
    # 模式2: 音色:xxx 或 voice:xxx
    match = re.search(r"[音色voice:：]+([\w \(\)\-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None


def execute_tts(text, voice_id=None):
    """执行语音合成"""
    # 如果未指定音色，尝试从文本中提取
    if voice_id is None:
        voice_id = detect_voice_preference(text)
    
    print(f"[Router] 语音合成: {text[:30]}...", file=sys.stderr)
    if voice_id:
        print(f"[Router] 使用音色: {voice_id}", file=sys.stderr)
    
    script_path = Path(__file__).parent / "tts.py"
    cmd = ["python3", str(script_path), text]
    if voice_id:
        cmd.extend(["-v", voice_id])
    
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "tts"
    
    return f"语音生成失败: {result.stderr}", "error"

def execute_video(prompt, image_path=None, duration=6, resolution="768P"):
    """执行视频生成"""
    log_action("video", prompt)
    print(f"[Router] 生成视频: {prompt[:30]}...", file=sys.stderr)
    
    # 如果没有指定图片，尝试使用最近的图片
    if not image_path:
        image_path = get_last_image()
    
    script_path = Path(__file__).parent / "video.py"
    cmd = ["python3", str(script_path), prompt]
    
    if image_path:
        cmd.extend(["-i", image_path])
    
    cmd.extend(["-d", str(duration), "-r", resolution])
    cmd.extend(["-o", f"/tmp/video_{os.getpid()}.mp4"])
    
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=300,
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
    
    # 如果没有指定图片，尝试使用最近的图片
    if not image_path:
        image_path = get_last_image()
    
    script_path = Path(__file__).parent / "video_with_audio.py"
    cmd = ["python3", str(script_path), video_desc, narration_text]
    
    if music_desc:
        cmd.append(music_desc)
    
    if image_path:
        cmd.extend(["--image", image_path])
    
    cmd.extend(["-o", f"/tmp/final_video_{os.getpid()}.mp4"])
    
    result = subprocess.run(
        cmd,
        capture_output=True, text=True, timeout=600,
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
        ["python3", str(script_path), "-p", prompt],
        capture_output=True, text=True, timeout=300,
        env={**os.environ, "MINIMAX_API_KEY": get_api_key(), "FROM_ROUTER": "1"}
    )
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if output and not output.startswith("错误"):
            return output, "music"
    
    return f"音乐生成失败: {result.stderr}", "error"

def execute_chat(text):
    """执行对话（直接返回文本）"""
    print(f"[Router] 对话模式: {text[:30]}...", file=sys.stderr)
    # 对话模式不需要在这里处理，由 Agent 决定
    return text, "text"

LAST_IMAGE_FILE = "/tmp/last_received_image.jpg"

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
    context_image_path: 最近收到的图片路径（用于自动使用）
    返回: (result, type) 或 [(result1, type1), (result2, type2), ...]
    """
    original_input = user_input.strip()
    
    # 检查是否以斜杠命令开头
    slash_match = re.match(r"^/(c|t|v|m|i)[\s]*(.*)$", original_input, re.DOTALL)
    if slash_match:
        cmd = slash_match.group(1)
        content = slash_match.group(2).strip()
        
        # 获取图片路径：优先用传入的，其次用最近的
        img_path = context_image_path or get_last_image()
        
        if cmd == "c":
            return [execute_chat(content)]
        elif cmd == "t":
            # 支持 /t voice_id:内容 格式，voice_id 允许包含空格和括号
            voice_match = re.match(r"^([\w \(\)\-]+):(.+)$", content)
            if voice_match:
                voice_id, text = voice_match.group(1), voice_match.group(2).strip()
                return [("__NEED_CONFIRM__", "tts", text, voice_id, voice_id)]
            voice_id = detect_voice_preference(content)
            voice_name = voice_id.split("_")[-1] if voice_id else "默认"
            return [("__NEED_CONFIRM__", "tts", content, voice_id, voice_name)]
        elif cmd == "v":
            return [("__NEED_CONFIRM__", "video", content)]
        elif cmd == "m":
            return [("__NEED_CONFIRM__", "music", content)]
        elif cmd == "i":
            return [("__NEED_CONFIRM__", "image", content)]
    
    # 检测混合意图
    if has_chain_pattern(original_input):
        parts = split_chain(original_input)
        if len(parts) > 1:
            print(f"[Router] 检测到混合意图，分成 {len(parts)} 部分", file=sys.stderr)
            results = []
            last_description = ""
            img_path = context_image_path or get_last_image()
            
            for i, part in enumerate(parts):
                intent = detect_intent_for_part(part)
                
                if intent == "tts" and last_description:
                    # TTS following another step - use the description from previous step
                    print(f"[Router] TTS 紧随生成步骤，使用描述: {last_description[:30]}...", file=sys.stderr)
                    results.append(execute_tts(last_description))
                elif intent == "image":
                    results.append(("__NEED_CONFIRM__", "image", part))
                    last_description = part
                elif intent == "video":
                    results.append(("__NEED_CONFIRM__", "video", part))
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
        # 需要确认，返回特殊标记
        return [("__NEED_CONFIRM__", "image", original_input)]
    elif intent == "video_audio":
        # 需要确认，返回特殊标记
        return [("__NEED_CONFIRM__", "video_audio", original_input)]
    elif intent == "video":
        return [("__NEED_CONFIRM__", "video", original_input)]
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
    尝试提取：视频描述、旁白文字、背景音乐描述
    """
    # 移除意图关键词
    text = re.sub(r"生成视频.*?配音", "", text)
    text = re.sub(r"视频.*?旁白", "", text)
    text = re.sub(r"视频.*?音乐", "", text)
    text = re.sub(r"做个.*视频.*配.*", "", text)
    
    # 尝试分割各部分
    # 常见模式：描述 + 旁白 + 音乐
    parts = re.split(r"[，,、]", text)
    
    video_desc = text  # 默认整个作为视频描述
    narration = "这是一个精彩的视频"  # 默认旁白
    music_desc = "轻快的背景音乐"  # 默认背景音乐
    
    # 简单策略：前三部分分别作为视频、旁白、音乐
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
        narration_match = re.search(r"旁白[是为：:]*([^.！!]+)", text)
        music_match = re.search(r"音乐[是为：:]*([^.！!]+)", text)
        
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
        # 用户确认了，执行之前保存的任务
        action = pending.get("action", "")
        original_input = pending.get("original_input", "")
        voice_id = pending.get("voice_id")
        clear_pending()
        if action == "image":
            log_action("image", original_input)
            result, rtype = execute_image(original_input)
        elif action == "music":
            log_action("music", original_input)
            result, rtype = execute_music(original_input)
        elif action == "video" or action == "video_audio":
            log_action("video", original_input)
            result, rtype = execute_video(original_input, context_image)
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
            # 需要确认，先保存状态，不执行
            action = item[1]
            original_input = item[2]
            voice_id = item[3] if len(item) > 3 else None
            save_pending(action, original_input, voice_id=voice_id)
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
            print(f"⚠️ 语音合成已准备好（音色：{voice_name}）。")
        else:
            action_names = {"image": "图片", "music": "音乐", "video": "视频", "video_audio": "视频+配音+音乐"}
            print(f"⚠️ {action_names.get(confirmed_action, confirmed_action)}生成已准备好。")
        print(f"回复「生成」确认执行，其他内容取消。")
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
