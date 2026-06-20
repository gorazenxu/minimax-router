#!/usr/bin/env python3
"""
MiniMax Image (图像生成) 脚本
支持：文生图 (t2i) 与 图生图 (i2i，基于 subject_reference 人物/主体参考)

用法:
  # 文生图
  python image.py "海边日落" -o out.png -s 16:9 -n 1

  # 图生图（人物主体参考，保持人物一致性 / 换场景换风格）
  python image.py "女孩在图书馆窗边远眺" --ref https://example.com/face.jpg -o out.png -s 3:4

  # 图生图（本地图片，自动转 base64）
  python image.py "赛博朋克风格" --ref ./photo.png -o out.png
"""

import os
import sys
import json
import base64
import tempfile
import requests
import argparse
from pathlib import Path

MINIMAX_API_URL = "https://api.minimaxi.com/v1/image_generation"

# 官方支持的宽高比（21:9 仅 image-01）
VALID_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"]

def get_env(key, default=None):
    return os.environ.get(key, default)


def file_to_data_url(path):
    """把本地图片转成 base64 Data URL（API 接受公开 URL 或 base64 Data URL）。"""
    path = Path(path)
    if not path.exists():
        print(f"错误: 参考图片不存在: {path}", file=sys.stderr)
        sys.exit(1)
    ext = path.suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}.get(ext)
    if not mime:
        print(f"错误: 参考图片仅支持 jpg/jpeg/png，收到 .{ext}", file=sys.stderr)
        sys.exit(1)
    # 10MB 限制
    if path.stat().st_size > 10 * 1024 * 1024:
        print(f"错误: 参考图片超过 10MB 限制", file=sys.stderr)
        sys.exit(1)
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def resolve_reference(ref):
    """
    把用户给的参考图解析成 subject_reference 数组项。
    支持：http(s) URL、本地文件路径（转 base64 Data URL）。
    type 固定为 character（人物主体参考，官方文档唯一支持类型）。
    """
    if not ref:
        return None
    if ref.startswith("http://") or ref.startswith("https://"):
        image_file = ref
    else:
        image_file = file_to_data_url(ref)
    return [{"type": "character", "image_file": image_file}]


def create_image(prompt, output_path=None, aspect_ratio="1:1", n=1,
                 subject_reference=None, prompt_optimizer=False, seed=None):
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
        "aspect_ratio": aspect_ratio,
        "n": n,
        "response_format": "url",
        "prompt_optimizer": prompt_optimizer,
    }
    if subject_reference:
        payload["subject_reference"] = subject_reference
    if seed is not None:
        payload["seed"] = seed

    mode = "图生图 (subject_reference)" if subject_reference else "文生图"
    print(f"正在生成图像... [{mode}]", file=sys.stderr)
    print(f"描述: {prompt[:50]}{'...' if len(prompt) > 50 else ''} | 比例: {aspect_ratio} | 数量: {n}",
          file=sys.stderr)

    response = requests.post(MINIMAX_API_URL, headers=headers, json=payload, timeout=120)

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

    meta = result.get("metadata", {})
    print(f"成功: 生成了 {len(image_urls)} 张图像 "
          f"(success={meta.get('success_count', '?')}, failed={meta.get('failed_count', '?')})",
          file=sys.stderr)

    output_paths = []
    for i, url in enumerate(image_urls):
        if output_path:
            # 只有一个输出路径时，加序号
            ext = Path(output_path).suffix or ".png"
            if len(image_urls) == 1:
                path = output_path if Path(output_path).suffix else f"{output_path}.png"
            else:
                path = output_path.replace(ext, f"_{i+1}{ext}")
        else:
            path = os.path.join(tempfile.gettempdir(), f"image_{i+1}.png")

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
    parser = argparse.ArgumentParser(
        description="MiniMax 图像生成（文生图 / 图生图）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="图生图示例:\n  python image.py '女孩在图书馆窗边远眺' --ref https://x.com/face.jpg -s 3:4")
    parser.add_argument("prompt", help="图像描述（最长 1500 字符）")
    parser.add_argument("-o", "--output", help="输出文件路径（不填则存到系统临时目录 image_N.png）")
    parser.add_argument("-s", "--size", "--aspect-ratio", dest="aspect_ratio", default="1:1",
                       help=f"宽高比 (默认: 1:1，可选: {', '.join(VALID_RATIOS)})")
    parser.add_argument("-n", "--num", type=int, default=1, help="生成数量 1-9 (默认: 1)")
    parser.add_argument("--ref", "--reference", dest="ref",
                       help="图生图参考图：URL 或本地路径 (jpg/jpeg/png, ≤10MB)。传入即启用图生图。")
    parser.add_argument("--optimize", action="store_true",
                       help="开启 prompt 自动优化 (默认关闭)")
    parser.add_argument("--seed", type=int, help="随机种子，用于复现")

    args = parser.parse_args()

    if args.aspect_ratio not in VALID_RATIOS:
        print(f"错误: 不支持的比例 {args.aspect_ratio}，可选: {', '.join(VALID_RATIOS)}", file=sys.stderr)
        sys.exit(1)
    if not (1 <= args.num <= 9):
        print(f"错误: 生成数量必须在 1-9 之间，收到 {args.num}", file=sys.stderr)
        sys.exit(1)
    if len(args.prompt) > 1500:
        print(f"错误: 描述超过 1500 字符限制（当前 {len(args.prompt)}）", file=sys.stderr)
        sys.exit(1)

    # 防护：不允许直接调用
    if os.environ.get("FROM_ROUTER") != "1":
        print("错误: 不允许直接调用 image.py，请通过统一入口", file=sys.stderr)
        sys.exit(1)

    subject_reference = resolve_reference(args.ref)

    result = create_image(
        prompt=args.prompt,
        output_path=args.output,
        aspect_ratio=args.aspect_ratio,
        n=args.num,
        subject_reference=subject_reference,
        prompt_optimizer=args.optimize,
        seed=args.seed,
    )

    if result:
        print(result)

if __name__ == "__main__":
    main()
