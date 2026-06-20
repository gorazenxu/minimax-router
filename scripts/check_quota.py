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
    print("📊 Token Plan 配额剩余（实时数据）")
    print("=" * 65)
    print()
    print(f"{'模型池':<30} {'当前窗口剩余':<20} {'本周剩余':<20}")
    print("-" * 65)
    
    # API 返回的是聚合后的池名（general / video 等），不是具体模型名
    name_map = {
        "general": "general 池（文本+语音+图+乐，按量折算）",
        "video": "video 池（视频，按个数计）",
    }
    
    for item in data:
        model = item.get("model_name", "")
        name = name_map.get(model, model)
        
        # ⚠️ 字段语义（易踩坑）：
        #   current_interval_total_count      = 当前窗口总额度
        #   current_interval_usage_count      = 当前窗口【剩余可用】数（字段名误导，非“已用”）
        #   current_interval_remaining_percent= 当前窗口剩余百分比
        # 验证：video total=3 usage=3 remaining%=100 → 剩余 3/3=100%，说明 usage 是“剩余”而非“已用”。
        curr_total = item.get("current_interval_total_count", 0)
        curr_remain = item.get("current_interval_usage_count", 0)
        
        weekly_total = item.get("current_weekly_total_count", 0)
        weekly_remain = item.get("current_weekly_usage_count", 0)
        
        curr_pct = item.get("current_interval_remaining_percent")
        weekly_pct = item.get("current_weekly_remaining_percent")
        
        # general 池按百分比管理（total 为 0），显示剩余百分比；
        # video 池按个数计，显示 剩余/总量。
        if curr_total > 0:
            curr_str = f"剩余 {curr_remain} / {curr_total} 个"
        elif curr_pct is not None:
            curr_str = f"剩余 {curr_pct}%"
        else:
            curr_str = "-"
        
        if weekly_total > 0:
            weekly_str = f"剩余 {weekly_remain} / {weekly_total} 个"
        elif weekly_pct is not None:
            weekly_str = f"剩余 {weekly_pct}%"
        else:
            weekly_str = "-"
        
        # 已用尽判断：剩余为 0
        exhausted = (curr_total > 0 and curr_remain == 0) or (curr_total == 0 and curr_pct is not None and curr_pct == 0)
        flag = " ⚠️已用尽" if exhausted else ""
        
        print(f"{name:<30} {curr_str:<20} {weekly_str:<20}{flag}")
    
    print("-" * 65)
    print("注：general 池按按量计费价格折算扣额度（百分比）；video 池按个数计。")
    print("    窗口：5 小时固定窗口 + 周窗口（周窗口含 1.5× 加成）。")

if __name__ == "__main__":
    main()
