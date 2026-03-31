#!/usr/bin/env python3
"""
MiniMax Image (图像生成) 脚本
用法: python image.py "图像描述" [output_path]
"""

import os
import sys
import json
import requests
import argparse
from pathlib import Path

MINIMAX_API_URL = "https://api.minimax.chat/v1/image_generation"

def get_env(key, default=None):
    return os.environ.get(key, default)

def create_image(prompt, output_path=None, size="1:1", num_images=1):
    api_key = get_env("MINIMAX_API_KEY")
    
    if not api_key:
        print("错误: 未设置 MINIMAX_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "image-01",
        "prompt": prompt,
        "image_size": size,
        "num_images": num_images
    }
    
    print(f"正在生成图像...", file=sys.stderr)
    print(f"描述: {prompt[:50]}{'...' if len(prompt) > 50 else ''}", file=sys.stderr)
    
    response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=60)
    
    if response.status_code != 200:
        print(f"错误: API 返回状态码 {response.status_code}", file=sys.stderr)
        print(f"响应: {response.text}", file=sys.stderr)
        sys.exit(1)
    
    result = response.json()
    
    # 检查 base_resp 状态
    if result.get("base_resp", {}).get("status_code", 0) != 0:
        err_msg = result.get("base_resp", {}).get("status_msg", "unknown error")
        print(f"错误: {err_msg}", file=sys.stderr)
        sys.exit(1)
    
    # 图像在 data.image_urls 中
    data = result.get("data", {})
    image_urls = data.get("image_urls", [])
    
    if not image_urls:
        print(f"错误: 未找到图像 URL", file=sys.stderr)
        sys.exit(1)
    
    print(f"成功: 生成了 {len(image_urls)} 张图像", file=sys.stderr)
    
    output_paths = []
    for i, url in enumerate(image_urls):
        if output_path:
            # 只有一个输出路径时，加序号
            ext = Path(output_path).suffix or ".png"
            path = output_path.replace(ext, f"_{i+1}{ext}")
        else:
            path = f"/tmp/image_{i+1}.png"
        
        download_file(url, path)
        print(f"已下载到: {path}", file=sys.stderr)
        output_paths.append(path)
    
    # 返回第一个路径（主要输出）
    return output_paths[0] if output_paths else None

def download_file(url, output_path):
    """下载文件"""
    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception(f"下载失败: {response.status_code}")

def main():
    parser = argparse.ArgumentParser(description="MiniMax 图像生成")
    parser.add_argument("prompt", help="图像描述")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-s", "--size", default="1:1", 
                       help="图像比例 (默认: 1:1, 可选: 16:9, 9:16, 4:3, 3:4)")
    parser.add_argument("-n", "--num", type=int, default=1, help="生成数量 (默认: 1)")
    
    args = parser.parse_args()
    
    # 防护：不允许直接调用
    if os.environ.get("FROM_ROUTER") != "1":
        print("错误: 不允许直接调用 image.py，请通过统一入口", file=sys.stderr)
        sys.exit(1)
    
    result = create_image(
        prompt=args.prompt,
        output_path=args.output,
        size=args.size,
        num_images=args.num
    )
    
    if result:
        print(result)

if __name__ == "__main__":
    main()
