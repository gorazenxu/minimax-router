#!/usr/bin/env python3
"""
MiniMax 套餐配额查询 - 真实API版本
接口: https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains
"""

import os
import sys
import requests
import json

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
BASE_URL = "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains"

def query_real_quota():
    """调用真实API查询配额"""
    if not MINIMAX_API_KEY:
        return None, "未设置 MINIMAX_API_KEY 环境变量"
    
    try:
        resp = requests.get(
            BASE_URL,
            headers={
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
        
        result = resp.json()
        
        if "base_resp" in result and result["base_resp"].get("status_code") != 0:
            return None, f"API错误: {result['base_resp'].get('status_msg', 'unknown')}"
        
        return result.get("model_remains", []), None
        
    except Exception as e:
        return None, str(e)

def main():
    print("正在查询真实配额...")
    
    data, error = query_real_quota()
    
    if error:
        print(f"错误: {error}")
        sys.exit(1)
    
    print()
    print("=" * 65)
    print("📊 Token Plan Max 套餐剩余（真实数据）")
    print("=" * 65)
    print()
    print(f"{'模型':<30} {'当前已用':<18} {'本周已用':<18}")
    print("-" * 65)
    
    # 模型名称映射（API名 -> 中文名）
    name_map = {
        "MiniMax-M*": "文字（MiniMax-M*）",
        "speech-hd": "语音（speech-hd）",
        "MiniMax-Hailuo-2.3-Fast-6s-768p": "视频 Fast（2.3-Fast）",
        "MiniMax-Hailuo-2.3-6s-768p": "视频（2.3）",
        "music-2.5": "音乐（music-2.5）",
        "image-01": "图片（image-01）",
    }
    
    for item in data:
        model = item.get("model_name", "")
        name = name_map.get(model, model)
        
        curr_total = item.get("current_interval_total_count", 0)
        curr_usage = item.get("current_interval_usage_count", 0)
        curr_remain = curr_total - curr_usage
        
        weekly_total = item.get("current_weekly_total_count", 0)
        weekly_usage = item.get("current_weekly_usage_count", 0)
        weekly_remain = weekly_total - weekly_usage
        
        curr_str = f"{curr_total - curr_usage:,} / {curr_total:,}"
        weekly_str = f"{weekly_total - weekly_usage:,} / {weekly_total:,}"
        
        flag = " !" if curr_usage == 0 else ""
        
        print(f"{name:<30} {curr_str:<18} {weekly_str:<18}{flag}")
    
    print("-" * 65)

if __name__ == "__main__":
    main()
