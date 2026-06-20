#!/usr/bin/env python3
"""
MiniMax TTS (文本转语音) 脚本 v2.0
支持: 情绪控制、音色克隆、语气词、语速/音高/音量调整

用法:
  python tts.py "要转换的文本" [output_path]

  # 指定音色
  python tts.py "文本" -v "male-qn-qingse"

  # 指定情绪 (happy/sad/angry/fearful/disgusted/surprised/calm/fluent/whisper)
  python tts.py "文本" -e happy

  # 音色克隆 (提供参考音频 URL)
  python tts.py "文本" --clone-url "https://example.com/voice.mp3"

  # 调整语速/音高
  python tts.py "文本" -s 1.2 -p 0.5

  # 启用语气词
  python tts.py "文本" --filler-words

  # 列出可用音色
  python tts.py --list
"""

import os
import sys
import json
import requests
import argparse
import re
from pathlib import Path
from typing import Optional, List

MINIMAX_API_URL = "https://api.minimaxi.com/v1/t2a_v2"

# 中文音色选项（国内版 api.minimaxi.com 用短格式 voice_id，与 references/voices.md 一致）
# ⚠️ 不要用 "Chinese (Mandarin)_xxx" 长格式，那是国际版 api.minimax.io 的格式，国内版会报错。
VOICE_OPTIONS_CN = {
    "gentle_youth": ("male-qn-qingse", "温润青年"),
    "reliable_executive": ("male-qn-jingying", "沉稳高管"),
    "radio_host": ("presenter_male", "电台男主播"),
    "news_anchor": ("presenter_female", "新闻女声"),
    "sweet_lady": ("female-tianmei", "甜美女声"),
    "warm_girl": ("female-shaonv", "温暖少女"),
    "male_announcer": ("presenter_male", "播报男声"),
}

# 英文音色选项（国内版可用，短格式）
VOICE_OPTIONS_EN = {
    "male_youth": ("male-qn-qingse", "男声青年"),
    "female_girl": ("female-shaonv", "女声少女"),
}

# 情绪选项（Speech 2.8 官方支持 9 种）
EMOTION_OPTIONS = {
    "happy": "开心",
    "sad": "悲伤",
    "angry": "愤怒",
    "fearful": "害怕",
    "disgusted": "厌恶",
    "surprised": "惊讶",
    "calm": "中性/平静",
    "fluent": "生动",
    "whisper": "低语",
}

def get_env(key, default=None):
    return os.environ.get(key, default)

def is_chinese(text: str) -> bool:
    """检测文本是否包含中文"""
    return any('\u4e00' <= c <= '\u9fff' for c in text)

def detect_emotion(text: str) -> Optional[str]:
    """从文本中检测情绪关键词"""
    text_lower = text.lower()
    
    # 正面情绪
    positive_words = ["开心", "高兴", "快乐", "太好了", "哈哈", "耶", "兴奋", "happy", "joy"]
    if any(w in text_lower for w in positive_words):
        return "happy"
    
    # 悲伤情绪
    sad_words = ["难过", "伤心", "悲伤", "哭了", "sad", "crying"]
    if any(w in text_lower for w in sad_words):
        return "sad"
    
    # 愤怒情绪
    angry_words = ["生气", "愤怒", "可恶", "讨厌", "angry", "mad"]
    if any(w in text_lower for w in angry_words):
        return "angry"
    
    # 惊讶情绪
    surprise_words = ["哇", "天哪", "真的吗", "惊讶", "wow", "omg", "surprised"]
    if any(w in text_lower for w in surprise_words):
        return "surprised"
    
    # 害怕/紧张情绪 → fearful（2.8 有效值，nervous 已废弃）
    fearful_words = ["紧张", "害怕", "担心", "恐惧", "nervous", "worried", "fearful", "scared"]
    if any(w in text_lower for w in fearful_words):
        return "fearful"
    
    # 厌恶情绪 → disgusted
    disgusted_words = ["恶心", "厌恶", "讨厌透", "disgusted", "gross"]
    if any(w in text_lower for w in disgusted_words):
        return "disgusted"
    
    return None

def text_to_speech(
    text: str,
    output_path: Optional[str] = None,
    voice_id: Optional[str] = None,
    speed: float = 1.0,
    pitch: float = 0.0,
    vol: float = 1.0,
    language: Optional[str] = None,
    emotion: Optional[str] = None,
    clone_url: Optional[str] = None,
    clone_file: Optional[str] = None,
    enable_filler_words: bool = False,
    output_format: str = "mp3",
    sample_rate: int = 32000,
):
    """
    调用 MiniMax TTS API 生成语音
    
    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        voice_id: 音色 ID
        speed: 语速 (0.5-2.0)
        pitch: 音高 (-500 to 500)
        vol: 音量 (0-2.0)
        language: 语言 (Chinese/English/auto)
        emotion: 情绪标签
        clone_url: 音色克隆参考音频 URL
        clone_file: 音色克隆参考音频文件路径
        enable_filler_words: 启用语气词
        output_format: 输出格式 (mp3/wav)
        sample_rate: 采样率
    """
    api_key = get_env("MINIMAX_API_KEY")
    
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 自动检测语言
    if language is None:
        language = "Chinese" if is_chinese(text) else "English"
    
    # 自动选择音色（国内版短格式 voice_id）
    if voice_id is None and clone_url is None and clone_file is None:
        voice_id = "male-qn-qingse" if language == "Chinese" else "male-qn-qingse"
    
    # 构建请求体
    payload = {
        "model": "speech-2.8-hd",
        "text": text,
        "stream": False,
        "output_format": "hex",
        "language_boost": language,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": vol,
            "pitch": int(pitch)
        },
        "audio_setting": {
            "sample_rate": sample_rate,
            "bitrate": 128000,
            "format": output_format,
            "channel": 1
        }
    }
    
    # 添加情绪参数 (MiniMax Speech 2.8 支持)
    if emotion:
        payload["voice_setting"]["emotion"] = emotion
    
    # 添加语气词支持 (MiniMax Speech 2.8 支持)
    if enable_filler_words:
        payload["filler_words"] = True
    
    # 音色克隆 (提供参考音频 URL 或文件)
    if clone_url:
        payload["voice_setting"]["voice_id"] = "clone"  # 使用克隆音色
        payload["voice_setting"]["voice_url"] = clone_url
    elif clone_file:
        # 需要上传文件获取 URL (这里简化处理，假设提供的是已上传的 URL)
        print(f"提示: 音色克隆请使用 --clone-url 参数提供参考音频的 URL", file=sys.stderr)
    
    print(f"正在调用 MiniMax TTS API...", file=sys.stderr)
    print(f"文本: {text[:50]}{'...' if len(text) > 50 else ''}", file=sys.stderr)
    print(f"语言: {language}", file=sys.stderr)
    
    if voice_id:
        print(f"音色: {voice_id}", file=sys.stderr)
    if emotion:
        emotion_name = EMOTION_OPTIONS.get(emotion, emotion)
        print(f"情绪: {emotion_name}", file=sys.stderr)
    if enable_filler_words:
        print(f"语气词: 已启用", file=sys.stderr)
    if clone_url:
        print(f"音色克隆: {clone_url[:50]}...", file=sys.stderr)
    
    print(f"语速: {speed} | 音高: {pitch} | 音量: {vol}", file=sys.stderr)
    
    try:
        response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=120)
        
        if response.status_code != 200:
            print(f"错误: API 返回状态码 {response.status_code}", file=sys.stderr)
            print(f"响应: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        result = response.json()
        
        # 检查是否有音频数据
        if "data" in result and "audio" in result.get("data", {}):
            audio_hex = result["data"]["audio"]
            audio_bytes = bytes.fromhex(audio_hex)
            
            if output_path is None:
                output_path = os.path.join(os.environ.get("TEMP", "/tmp"), f"tts_output_{os.getpid()}.{output_format}")
            
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            
            print(f"成功: 音频已保存到 {output_path}", file=sys.stderr)
            print(f"音频大小: {len(audio_bytes):,} bytes", file=sys.stderr)
            return output_path
        
        # 检查错误
        if "base_resp" in result:
            err = result["base_resp"]
            print(f"错误: {err.get('status_msg', 'unknown error')}", file=sys.stderr)
            sys.exit(1)
        
        # 返回完整响应供调试
        print(f"响应: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        return result
        
    except requests.exceptions.Timeout:
        print("错误: 请求超时，请稍后重试", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"错误: 网络请求失败 - {e}", file=sys.stderr)
        sys.exit(1)

def list_voices(voice_type: str = "all"):
    """列出可用的音色（本地字典，无需 API Key）"""
    print("=" * 50)
    print("MiniMax Speech 2.8 可用音色列表")
    print("=" * 50)
    
    print("\n【中文音色】")
    for key, (voice_id, name) in VOICE_OPTIONS_CN.items():
        print(f"  {voice_id}")
        print(f"    别名: {name}")
    
    print("\n【英文音色】")
    for key, (voice_id, name) in VOICE_OPTIONS_EN.items():
        print(f"  {voice_id}")
        print(f"    别名: {name}")
    
    print("\n【情绪标签】")
    for emotion, name in EMOTION_OPTIONS.items():
        print(f"  {emotion:12} - {name}")
    
    print("\n【参数说明】")
    print("  --speed   语速 (0.5-2.0, 默认 1.0)")
    print("  --pitch   音高 (-500 to 500, 默认 0)")
    print("  --vol     音量 (0-2.0, 默认 1.0)")
    print("  --emotion 情绪 (见上方列表)")
    print("  --clone-url 音色克隆参考音频 URL")
    print("  --filler-words 启用语气词(嗯/呃/哎)")
    print("  --output-format mp3/wav (默认 mp3)")
    print("  --sample-rate 采样率 (默认 32000)")
    
    print("\n【音色克隆】")
    print("  提供一段人声音频 URL (10秒以上效果最佳)")
    print("  系统会自动提取音色特征并生成相似声音")
    print("  示例: python tts.py '文本' --clone-url 'https://example.com/voice.mp3'")


def main():
    parser = argparse.ArgumentParser(
        description="MiniMax 文本转语音 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python tts.py "你好，欢迎使用 MiniMax 语音合成"

  # 选择音色
  python tts.py "你好" -v "presenter_female"

  # 带情绪
  python tts.py "太开心了！" -e happy

  # 音色克隆
  python tts.py "你好" --clone-url "https://example.com/reference.mp3"

  # 调整语速和音高
  python tts.py "快速播报" -s 1.5 -p 50

  # 启用语气词 (更自然的停顿)
  python tts.py "让我想想..." --filler-words

  # 指定输出格式
  python tts.py "文本" -o output.wav --output-format wav
"""
    )
    parser.add_argument("text", nargs="?", help="要转换的文本")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-v", "--voice", help="音色 ID")
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="语速 (0.5-2.0, 默认: 1.0)")
    parser.add_argument("-p", "--pitch", type=float, default=0.0, help="音高 (-500 to 500, 默认: 0)")
    parser.add_argument("--vol", type=float, default=1.0, help="音量 (0-2.0, 默认: 1.0)")
    parser.add_argument("-l", "--lang", help="语言 (Chinese/English/auto, 默认: 自动检测)")
    parser.add_argument("-e", "--emotion", help="情绪标签 (happy/sad/angry/fearful/disgusted/surprised/calm/fluent/whisper)")
    parser.add_argument("--clone-url", help="音色克隆参考音频 URL (10秒以上)")
    parser.add_argument("--clone-file", help="音色克隆参考音频文件路径")
    parser.add_argument("--filler-words", action="store_true", help="启用语气词 (嗯/呃/哎等自然停顿)")
    parser.add_argument("--output-format", default="mp3", choices=["mp3", "wav"], help="输出格式 (默认: mp3)")
    parser.add_argument("--sample-rate", type=int, default=32000, help="采样率 (默认: 32000)")
    parser.add_argument("--list", action="store_true", help="列出所有可用音色")
    parser.add_argument("--emotions", action="store_true", help="列出所有情绪选项")
    
    args = parser.parse_args()
    
    # 列出音色
    if args.list:
        list_voices()
        return
    
    # 列出情绪
    if args.emotions:
        print("可用情绪标签:")
        for emotion, name in EMOTION_OPTIONS.items():
            print(f"  {emotion:12} - {name}")
        return
    
    # 需要文本
    if not args.text:
        parser.print_help()
        print("\n错误: 请提供要转换的文本")
        print("或使用 --list 查看可用音色")
        sys.exit(1)
    
    # 验证参数
    if not 0.5 <= args.speed <= 2.0:
        print(f"警告: 语速 {args.speed} 超出范围 (0.5-2.0)，将使用默认值 1.0", file=sys.stderr)
        args.speed = 1.0
    
    if not -500 <= args.pitch <= 500:
        print(f"警告: 音高 {args.pitch} 超出范围 (-500 to 500)，将使用默认值 0", file=sys.stderr)
        args.pitch = 0
    
    if not 0 <= args.vol <= 2.0:
        print(f"警告: 音量 {args.vol} 超出范围 (0-2.0)，将使用默认值 1.0", file=sys.stderr)
        args.vol = 1.0
    
    # 自动检测情绪
    detected_emotion = detect_emotion(args.text)
    if args.emotion:
        emotion = args.emotion
    elif detected_emotion:
        print(f"提示: 检测到文本情绪: {EMOTION_OPTIONS.get(detected_emotion, detected_emotion)}", file=sys.stderr)
        emotion = detected_emotion
    else:
        emotion = None
    
    result = text_to_speech(
        text=args.text,
        output_path=args.output,
        voice_id=args.voice,
        speed=args.speed,
        pitch=args.pitch,
        vol=args.vol,
        language=args.lang,
        emotion=emotion,
        clone_url=args.clone_url,
        clone_file=args.clone_file,
        enable_filler_words=args.filler_words,
        output_format=args.output_format,
        sample_rate=args.sample_rate,
    )
    
    # 只输出文件路径到 stdout，供 Agent 捕获
    if isinstance(result, str):
        print(result)

if __name__ == "__main__":
    main()
