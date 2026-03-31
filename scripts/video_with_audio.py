#!/usr/bin/env python3
"""
MiniMax 视频生成 + 配音 + 背景音乐
用法: python video_with_audio.py "视频描述" "旁白文字" [音乐描述]
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def get_env(key, default=None):
    return os.environ.get(key, default)

def run_script(script_name, args, timeout=300):
    """运行其他脚本并返回输出"""
    script_path = Path(__file__).parent / script_name
    cmd = ["python3", str(script_path)] + args
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "MINIMAX_API_KEY": get_env("MINIMAX_API_KEY", "")}
    )
    
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        return None

def generate_video_with_audio(video_desc, narration_text, music_desc=None, image_path=None, output_path=None):
    """
    生成视频 + 配音 + 背景音乐，合并输出
    """
    if output_path is None:
        output_path = "/tmp/final_video.mp4"
    
    tmp_dir = "/tmp/video_wa"
    os.makedirs(tmp_dir, exist_ok=True)
    
    video_path = f"{tmp_dir}/video.mp4"
    narration_path = f"{tmp_dir}/narration.mp3"
    music_path = f"{tmp_dir}/music.mp3"
    mixed_audio_path = f"{tmp_dir}/mixed_audio.mp3"
    
    print("=== 步骤1: 生成视频 ===")
    video_args = [video_desc, "-o", video_path]
    if image_path:
        video_args.extend(["-i", image_path])
    
    video_result = run_script("video.py", video_args, timeout=600)
    
    if not video_result or not os.path.exists(video_path):
        print(f"错误: 视频生成失败")
        return None
    print(f"视频生成完成: {video_path}")
    
    print("\n=== 步骤2: 生成配音 ===")
    narration_result = run_script("tts.py", [
        narration_text,
        "-o", narration_path
    ], timeout=120)
    
    if not narration_result or not os.path.exists(narration_path):
        print(f"错误: 配音生成失败")
        return None
    print(f"配音生成完成: {narration_path}")
    
    if music_desc:
        print("\n=== 步骤3: 生成背景音乐 ===")
        music_result = run_script("music.py", [
            music_desc,
            "-o", music_path,
            "--instrumental"
        ], timeout=300)
        
        if music_result and os.path.exists(music_path):
            print(f"背景音乐生成完成: {music_path}")
            has_music = True
        else:
            print(f"警告: 背景音乐生成失败，将只使用配音")
            has_music = False
    else:
        has_music = False
    
    print("\n=== 步骤4: 合并音视频 ===")
    
    if has_music:
        # 先混合配音和背景音乐
        # 配音为主(1.0)，背景音乐为辅(0.3)
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", narration_path,
            "-i", music_path,
            "-filter_complex",
            "[0:a]volume=1.0[nar];[1:a]volume=0.25[bg];[nar][bg]amix=inputs=2:duration=first[mixed]",
            "-map", "[mixed]",
            "-t", str(get_duration(video_path)),
            mixed_audio_path
        ]
        
        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"警告: 音频混合失败: {result.stderr[:200]}")
            # 回退到只用配音
            mixed_audio_path = narration_path
    else:
        mixed_audio_path = narration_path
    
    # 合并视频和音频
    merge_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", mixed_audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-t", str(get_duration(video_path)),
        output_path
    ]
    
    result = subprocess.run(merge_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"错误: 合并失败: {result.stderr[:200]}")
        return None
    
    print(f"\n✅ 完成: {output_path}")
    return output_path

def get_duration(file_path):
    """获取音视频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except:
            pass
    return 6  # 默认6秒

def main():
    if len(sys.argv) < 3:
        print("用法: python video_with_audio.py \"视频描述\" \"旁白文字\" [音乐描述] [--image 图片路径]")
        print("示例: python video_with_audio.py \"海边日落\" \"今天天气真好\" \"轻快的钢琴曲\"")
        sys.exit(1)
    
    args = sys.argv[1:]
    image_path = None
    
    if "--image" in args:
        idx = args.index("--image")
        image_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
    
    video_desc = args[0]
    narration_text = args[1]
    music_desc = args[2] if len(args) > 2 else None
    
    result = generate_video_with_audio(video_desc, narration_text, music_desc, image_path)
    
    if result:
        print(result)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
