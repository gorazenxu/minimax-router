#!/usr/bin/env python3
"""
MiniMax Video (视频生成) 脚本
用法: python video.py "视频描述"
      python video.py -i 图片路径 "视频描述"
      python video.py -i 图片路径 -d 10 -r 1080P "视频描述"
"""

import os
import sys
import json
import time
import base64
import requests
import argparse
from pathlib import Path

MINIMAX_API_URL = "https://api.minimax.chat/v1/video_generation"
MINIMAX_QUERY_URL = "https://api.minimax.chat/v1/query/video_generation"
MINIMAX_FILE_URL = "https://api.minimax.chat/v1/files/retrieve"

def get_env(key, default=None):
    return os.environ.get(key, default)

def create_video(text, image_url=None, model=None, output_path=None, duration=6, resolution="768P"):
    """
    创建视频，自动选择模型：
    - 有图片 → 优先 2.3，失败自动切换 Fast
    - 无图片 → 使用 2.3（纯文字模式）
    """
    api_key = get_env("MINIMAX_API_KEY")
    
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 自动选择模型：有图片优先 Fast，无图片用 2.3
    if model is None:
        if image_url:
            model = "MiniMax-Hailuo-2.3-Fast"
        else:
            model = "MiniMax-Hailuo-2.3"
    
    payload = {
        "model": model,
        "prompt": text,
        "duration": duration,
        "resolution": resolution
    }
    
    # 处理图片
    if image_url:
        img_data = download_and_encode_image(image_url)
        if img_data:
            payload["first_frame_image"] = img_data
        else:
            print("错误: 图片下载失败", file=sys.stderr)
            sys.exit(1)
    
    print(f"正在创建视频任务...", file=sys.stderr)
    print(f"模型: {model}", file=sys.stderr)
    if image_url:
        print(f"模式: 图生视频", file=sys.stderr)
    else:
        print(f"模式: 文生视频", file=sys.stderr)
    print(f"描述: {text[:50]}{'...' if len(text) > 50 else ''}", file=sys.stderr)
    print(f"分辨率: {resolution} | 时长: {duration}秒", file=sys.stderr)
    
    response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=30)
    result = response.json() if response.content else {}
    
    # 检查错误
    if "base_resp" in result:
        err_code = result["base_resp"].get("status_code", 0)
        err_msg = result["base_resp"].get("status_msg", "")
        
        if err_code != 0:
            # 2.3 配额满，尝试 Fast（如果有图片）
            if "usage limit exceeded" in err_msg and model == "MiniMax-Hailuo-2.3" and image_url:
                print(f"2.3 配额已用完，尝试 Fast 模型...", file=sys.stderr)
                return create_video(text, image_url, "MiniMax-Hailuo-2.3-Fast", output_path)
            
            # Fast 模型不支持纯文字，自动切换 2.3
            if "does not support Text-to-Video" in err_msg and model == "MiniMax-Hailuo-2.3-Fast" and not image_url:
                print("Fast 模型需要图片，自动切换到 2.3 模型...", file=sys.stderr)
                return create_video(text, image_url, "MiniMax-Hailuo-2.3", output_path)
            
            print(f"错误: {err_msg}", file=sys.stderr)
            sys.exit(1)
    
    if "task_id" not in result or not result["task_id"]:
        print(f"错误: 响应中未找到 task_id", file=sys.stderr)
        print(f"响应: {json.dumps(result, ensure_ascii=False)[:200]}", file=sys.stderr)
        sys.exit(1)
    
    task_id = result["task_id"]
    print(f"任务 ID: {task_id}", file=sys.stderr)
    print(f"正在等待视频生成（预计30-60秒）...", file=sys.stderr)
    
    video_path = wait_for_completion(task_id, api_key, output_path)
    return video_path

def download_and_encode_image(url):
    """下载图片并转为 base64 data URL"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            img_b64 = base64.b64encode(response.content).decode('utf-8')
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            return f"data:{content_type};base64,{img_b64}"
        else:
            print(f"图片下载失败: HTTP {response.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"图片下载异常: {e}", file=sys.stderr)
    return None

def wait_for_completion(task_id, api_key, output_path=None, max_wait=600, poll_interval=10):
    """轮询等待视频生成完成"""
    headers = {"Authorization": f"Bearer {api_key}"}
    
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
                
                status_display = {"Preparing": "准备中", "Processing": "生成中", "Success": "完成", "Fail": "失败"}
                print(f"状态: {status_display.get(status, status)} (已等待 {elapsed}秒)", file=sys.stderr)
                
                if status == "Success":
                    file_id = result.get("file_id")
                    if file_id:
                        video_url = get_file_url(file_id, api_key)
                        if video_url:
                            output_path = output_path or f"/tmp/video_{task_id}.mp4"
                            download_file(video_url, output_path)
                            print(f"成功: {output_path}", file=sys.stderr)
                            return output_path
                
                elif status == "Fail":
                    print(f"任务失败: {result.get('base_resp', {}).get('status_msg', 'unknown')}", file=sys.stderr)
                    return None
            
            elapsed += poll_interval
            time.sleep(poll_interval)
        except Exception as e:
            print(f"轮询异常: {e}", file=sys.stderr)
            time.sleep(poll_interval)
            elapsed += poll_interval
    
    print(f"等待超时 ({max_wait}秒)", file=sys.stderr)
    return None

def get_file_url(file_id, api_key):
    """通过 file_id 获取下载 URL"""
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            f"{MINIMAX_FILE_URL}?file_id={file_id}",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("file", {}).get("download_url")
    except Exception as e:
        print(f"获取文件 URL 失败: {e}", file=sys.stderr)
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
    parser = argparse.ArgumentParser(description="MiniMax 视频生成")
    parser.add_argument("text", help="视频描述文本")
    parser.add_argument("-i", "--image", help="起始图片路径或 URL (可选，用于图生视频)")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-m", "--model", default=None,
                       choices=["MiniMax-Hailuo-2.3", "MiniMax-Hailuo-2.3-Fast"],
                       help="模型: 2.3 (质量好) / Fast (速度快, 仅图生视频)")
    parser.add_argument("-d", "--duration", type=int, default=6, choices=[6, 10],
                       help="视频时长: 6秒(默认) 或 10秒")
    parser.add_argument("-r", "--resolution", default="768P",
                       choices=["512P", "720P", "768P", "1080P"],
                       help="分辨率: 512P/720P/768P(默认)/1080P")
    
    args = parser.parse_args()
    
    # 防护：不允许直接调用
    if os.environ.get("FROM_ROUTER") != "1":
        print("错误: 不允许直接调用 video.py，请通过统一入口", file=sys.stderr)
        sys.exit(1)
    
    result = create_video(
        text=args.text,
        image_url=args.image,
        model=args.model,
        output_path=args.output,
        duration=args.duration,
        resolution=args.resolution
    )
    
    if result:
        print(result)

if __name__ == "__main__":
    main()
