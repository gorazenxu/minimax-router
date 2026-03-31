#!/usr/bin/env python3
"""
MiniMax Music (音乐生成) 脚本
用法: python music.py "歌词或描述" [output_path]
"""

import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path

MINIMAX_API_URL = "https://api.minimaxi.com/v1/music_generation"
MINIMAX_QUERY_URL = "https://api.minimaxi.com/v1/query/music_generation"

def get_env(key, default=None):
    return os.environ.get(key, default)

def create_music(text, output_path=None, lyrics=None):
    api_key = get_env("MINIMAX_API_KEY")
    
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 使用 music-2.5
    model = "music-2.5"
    
    payload = {
        "model": model,
        "prompt": text[:2000] if len(text) > 2000 else text,
        "output_format": "hex",
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3"
        }
    }
    
    # 纯音乐（is_instrumental）仅 music-2.5+ 支持，music-2.5 不支持此参数
    # 有歌词歌曲：lyrics 必填，若未提供则设 lyrics_optimizer=true 由系统根据 prompt 自动生成
    if lyrics:
        if len(lyrics) > 3500:
            print(f"警告: 歌词超过3500字符限制，已截断", file=sys.stderr)
            payload["lyrics"] = lyrics[:3500]
        else:
            payload["lyrics"] = lyrics
    else:
        # 未提供歌词，开启自动生成
        payload["lyrics_optimizer"] = True
        payload["lyrics"] = ""
    
    print(f"正在创建音乐任务...", file=sys.stderr)
    print(f"模型: {model}", file=sys.stderr)
    print(f"类型: {'纯音乐（由系统根据描述生成）' if not lyrics else '带歌词歌曲'}", file=sys.stderr)
    if not lyrics:
        print(f"歌词: 由系统根据描述自动生成", file=sys.stderr)
    print(f"描述: {text[:50]}{'...' if len(text) > 50 else ''}", file=sys.stderr)
    print(f"音频质量: 44100Hz / 256kbps / MP3", file=sys.stderr)
    
    response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=300)
    
    if response.status_code != 200:
        print(f"错误: API 返回状态码 {response.status_code}", file=sys.stderr)
        print(f"响应: {response.text}", file=sys.stderr)
        sys.exit(1)
    
    result = response.json()
    
    # 检查 base_resp
    if "base_resp" in result:
        err_code = result["base_resp"].get("status_code", 0)
        err_msg = result["base_resp"].get("status_msg", "")
        
        if err_code != 0:
            # 配额超限
            if "usage limit exceeded" in err_msg or err_code == 2056:
                print(f"错误: 音乐配额已用完（每天4首）", file=sys.stderr)
                sys.exit(1)
            print(f"错误: {err_msg}", file=sys.stderr)
            sys.exit(1)
    
    # 检查直接返回的音频（hex 格式）
    if "data" in result and result["data"]:
        audio_hex = result["data"].get("audio", "")
        if audio_hex:
            audio_bytes = bytes.fromhex(audio_hex)
            if output_path is None:
                output_path = "/tmp/music_output.mp3"
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"成功: 音乐已保存到 {output_path}", file=sys.stderr)
            print(f"音频大小: {len(audio_bytes)} bytes", file=sys.stderr)
            return output_path
    
    # 检查是否有 task_id（异步模式）
    if "task_id" in result and result["task_id"]:
        task_id = result["task_id"]
        print(f"任务 ID: {task_id}", file=sys.stderr)
        print(f"正在等待音乐生成（可能需要几分钟）...", file=sys.stderr)
        
        music_path = wait_for_completion(task_id, api_key, output_path)
        return music_path
    
    # 意外响应
    print(f"错误: 意外响应格式", file=sys.stderr)
    print(f"响应: {json.dumps(result, ensure_ascii=False)[:300]}", file=sys.stderr)
    sys.exit(1)

def wait_for_completion(task_id, api_key, output_path=None, max_wait=600, poll_interval=10):
    """轮询等待音乐生成完成"""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    elapsed = 0
    while elapsed < max_wait:
        try:
            response = requests.get(
                f"{MINIMAX_QUERY_URL}?task_id={task_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                status = result.get("status", "")
                
                print(f"状态: {status} (已等待 {elapsed}秒)", file=sys.stderr)
                
                if status == "Success":
                    outputs = result.get("output", {}).get("outputs", [])
                    if outputs and len(outputs) > 0:
                        url = outputs[0].get("url")
                        if url:
                            if output_path is None:
                                output_path = f"/tmp/music_{task_id}.mp3"
                            download_file(url, output_path)
                            print(f"成功: 音乐已保存到 {output_path}", file=sys.stderr)
                            return output_path
                
                elif status == "Fail":
                    err = result.get("base_resp", {}).get("status_msg", "unknown")
                    print(f"任务失败: {err}", file=sys.stderr)
                    return None
            
            elapsed += poll_interval
            time.sleep(poll_interval)
        except Exception as e:
            print(f"轮询异常: {e}", file=sys.stderr)
            time.sleep(poll_interval)
            elapsed += poll_interval
    
    print(f"等待超时 ({max_wait}秒)", file=sys.stderr)
    return None

def download_file(url, output_path):
    """下载文件"""
    response = requests.get(url, timeout=180)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"下载失败: {response.status_code}")

def main():
    parser = argparse.ArgumentParser(description="MiniMax 音乐生成")
    parser.add_argument("-p", "--prompt", required=True, help="歌曲描述（风格、情绪、场景）")
    parser.add_argument("-l", "--lyrics", default="", help="歌词（可选，不提供则自动生成）")
    parser.add_argument("-o", "--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    # 防护：不允许直接调用
    if os.environ.get("FROM_ROUTER") != "1":
        print("错误: 不允许直接调用 music.py，请通过统一入口", file=sys.stderr)
        sys.exit(1)
    
    result = create_music(
        text=args.prompt,
        output_path=args.output,
        lyrics=args.lyrics if args.lyrics else None
    )
    
    if result:
        print(result)

if __name__ == "__main__":
    main()
