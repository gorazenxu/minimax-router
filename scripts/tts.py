#!/usr/bin/env python3
"""
MiniMax TTS (文本转语音) 脚本
用法: python tts.py "要转换的文本" [output_path]
"""

import os
import sys
import json
import requests
import argparse
from pathlib import Path

MINIMAX_API_URL = "https://api.minimax.chat/v1/t2a_v2"

# 中文语音默认
DEFAULT_VOICE_CN = "Chinese (Mandarin)_Gentle_Youth"
# 英文语音默认
DEFAULT_VOICE_EN = "English_expressive_narrator"

def get_env(key, default=None):
    return os.environ.get(key, default)

def is_chinese(text):
    """检测文本是否包含中文"""
    return any('\u4e00' <= c <= '\u9fff' for c in text)

def text_to_speech(text, output_path=None, voice_id=None, speed=1.0, language=None):
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
    
    # 自动选择音色
    if voice_id is None:
        voice_id = DEFAULT_VOICE_CN if language == "Chinese" else DEFAULT_VOICE_EN
    
    payload = {
        "model": "speech-2.8-hd",
        "text": text,
        "stream": False,
        "output_format": "hex",
        "language_boost": language,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
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
    
    print(f"正在调用 MiniMax TTS API...", file=sys.stderr)
    print(f"文本: {text[:50]}{'...' if len(text) > 50 else ''}", file=sys.stderr)
    print(f"音色: {voice_id}", file=sys.stderr)
    
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
            output_path = "/tmp/tts_output.mp3"
        
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        print(f"成功: 音频已保存到 {output_path}", file=sys.stderr)
        print(f"音频大小: {len(audio_bytes)} bytes", file=sys.stderr)
        return output_path
    
    # 检查错误
    if "base_resp" in result:
        err = result["base_resp"]
        print(f"错误: {err.get('status_msg', 'unknown error')}", file=sys.stderr)
        sys.exit(1)
    
    # 返回完整响应供调试
    print(f"响应: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
    return result

def list_voices():
    """列出可用的音色"""
    api_key = get_env("MINIMAX_API_KEY")
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY 环境变量", file=sys.stderr)
        return
    
    resp = requests.post(
        'https://api.minimax.chat/v1/get_voice',
        headers={'Authorization': f"Bearer {api_key}"},
        json={'voice_type': 'all'},
        timeout=30
    )
    d = resp.json()
    
    print("中文音色:")
    for v in d.get('system_voice', []):
        if 'Chinese' in v.get('voice_id', ''):
            print(f"  {v['voice_id']} - {v.get('voice_name', '')}")
    
    print("\n英文音色 (前10个):")
    count = 0
    for v in d.get('system_voice', []):
        if 'Chinese' not in v.get('voice_id', '') and count < 10:
            print(f"  {v['voice_id']}")
            count += 1

def main():
    parser = argparse.ArgumentParser(description="MiniMax 文本转语音")
    parser.add_argument("text", help="要转换的文本")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-v", "--voice", help="音色 ID")
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="语速 (默认: 1.0)")
    parser.add_argument("-l", "--lang", help="语言 (Chinese/English, 默认: 自动检测)")
    parser.add_argument("--list", action="store_true", help="列出所有可用音色")
    
    args = parser.parse_args()
    
    if args.list:
        list_voices()
        return
    
    result = text_to_speech(
        text=args.text,
        output_path=args.output,
        voice_id=args.voice,
        speed=args.speed,
        language=args.lang
    )
    
    # 只输出文件路径到 stdout，供 Agent 捕获
    if isinstance(result, str):
        print(result)

if __name__ == "__main__":
    main()
