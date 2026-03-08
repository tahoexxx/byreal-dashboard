#!/usr/bin/env python3
"""
X/Twitter 采集 v2 — 6551 OpenTwitter API
功能：
1. 关注账号推文采集（user_tweets）
2. 行业热点关键词搜索（twitter_search）
3. 竞品动态深度采集
4. 互动数据（likes/views/retweets）完整保留

API: https://ai.6551.io
Token: 环境变量 TWITTER_TOKEN
输出: data/x_cache.json
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_PATH = BASE_DIR / "data" / "x_cache.json"
API_BASE = "https://ai.6551.io/open"
TOKEN = os.environ.get("TWITTER_TOKEN", "")

# ==================== 账号配置 ====================

ACCOUNTS = {
    # Byreal
    "byreal_io": {"type": "byreal", "max": 10},
    # 竞品 DEX — 重点监控
    "JupiterExchange": {"type": "competitor", "max": 10},
    "MeteoraAG": {"type": "competitor", "max": 10},
    "Raydium": {"type": "competitor", "max": 10},
    "orca_so": {"type": "competitor", "max": 10},
    # 生态
    "solana": {"type": "ecosystem", "max": 5},
    "SolanaFloor": {"type": "ecosystem", "max": 5},
    # KOL — 英文
    "CryptoHayes": {"type": "kol", "max": 5},
    "toly": {"type": "kol", "max": 5},
    "benbybit": {"type": "kol", "max": 5},
    # KOL — 中文
    "colinwu": {"type": "kol_cn", "max": 5},
    "hellosuoha": {"type": "kol_cn", "max": 5},
    "victalk6886": {"type": "kol_cn", "max": 5},
    "luyaoyuan": {"type": "kol_cn", "max": 5},
    "0xSunNFT": {"type": "kol_cn", "max": 5},
    "0xSleepinRain": {"type": "kol_cn", "max": 5},
    "ShanghaoJin": {"type": "kol_cn", "max": 5},
    "Michael_Liu93": {"type": "kol_cn", "max": 5},
}

# 热点搜索关键词
SEARCH_QUERIES = [
    # Solana DEX 热点
    {"keywords": "Solana DEX", "minLikes": 50, "maxResults": 15, "product": "Top", "tag": "solana_dex"},
    {"keywords": "Solana DeFi", "minLikes": 30, "maxResults": 15, "product": "Top", "tag": "solana_defi"},
    # RWA — Byreal 方向
    {"keywords": "RWA tokenization", "minLikes": 20, "maxResults": 10, "product": "Top", "tag": "rwa"},
    {"keywords": "real world assets crypto", "minLikes": 20, "maxResults": 10, "product": "Top", "tag": "rwa"},
    # CLMM/LP 策略
    {"keywords": "CLMM liquidity", "minLikes": 10, "maxResults": 10, "product": "Top", "tag": "clmm"},
    {"keywords": "concentrated liquidity Solana", "minLikes": 10, "maxResults": 10, "product": "Top", "tag": "clmm"},
    # 行业大事件
    {"keywords": "crypto regulation 2026", "minLikes": 50, "maxResults": 10, "product": "Top", "tag": "regulation"},
    # 中文热点
    {"keywords": "Solana 生态", "minLikes": 10, "maxResults": 10, "product": "Top", "lang": "zh", "tag": "cn_solana"},
    {"keywords": "DEX 流动性", "minLikes": 5, "maxResults": 10, "product": "Top", "lang": "zh", "tag": "cn_dex"},
]

# KOL 推文搜索补充（user_tweets 不返回互动数据，用 search 补采重要 KOL）
KOL_SEARCHES = [
    {"fromUser": "CryptoHayes", "maxResults": 5, "product": "Latest", "tag": "kol_search"},
    {"fromUser": "toly", "maxResults": 5, "product": "Latest", "tag": "kol_search"},
    {"fromUser": "colinwu", "maxResults": 5, "product": "Latest", "tag": "kol_search"},
    {"fromUser": "hellosuoha", "maxResults": 5, "product": "Latest", "tag": "kol_search"},
    {"fromUser": "benbybit", "maxResults": 5, "product": "Latest", "tag": "kol_search"},
]

# 竞品专项搜索 — 抓别人提到竞品的讨论
COMPETITOR_SEARCHES = [
    {"keywords": "Jupiter Exchange", "minLikes": 20, "maxResults": 10, "product": "Top", "excludeRetweets": True, "tag": "about_jupiter"},
    {"keywords": "Meteora DeFi OR Meteora DAMM", "minLikes": 10, "maxResults": 10, "product": "Top", "tag": "about_meteora"},
    {"keywords": "Raydium liquidity OR Raydium pool", "minLikes": 10, "maxResults": 10, "product": "Top", "tag": "about_raydium"},
    {"keywords": "Orca Solana DEX", "minLikes": 10, "maxResults": 10, "product": "Top", "tag": "about_orca"},
]


# ==================== API 调用 ====================

def api_call(endpoint, payload):
    """Call 6551 API endpoint"""
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"  ✗ API error {e.code}: {body}")
        return None
    except Exception as e:
        print(f"  ✗ Request error: {e}")
        return None


def parse_tweet(raw, source_type="account", source_handle="", tag=""):
    """Parse raw tweet from 6551 API into standardized format"""
    return {
        "handle": raw.get("userScreenName", source_handle),
        "name": raw.get("userName", source_handle),
        "type": source_type,
        "tag": tag,
        "content": raw.get("text", ""),
        "likes": raw.get("favoriteCount", 0) or 0,
        "retweets": raw.get("retweetCount", 0) or 0,
        "replies": raw.get("replyCount", 0) or 0,
        "views": raw.get("viewCount", 0) or 0,
        "quotes": raw.get("quoteCount", 0) or 0,
        "followers": raw.get("userFollowers", 0) or 0,
        "verified": raw.get("userVerified", False),
        "timestamp": raw.get("createdAt", ""),
        "id": raw.get("id", ""),
        "url": f"https://x.com/{raw.get('userScreenName', source_handle)}/status/{raw['id']}" if raw.get("id") else "",
        "is_quote": raw.get("isQuote", False),
        "is_reply": raw.get("isReply", False),
        "conversation_id": raw.get("conversationId", ""),
    }


def is_within_hours(created_at_str, hours=48):
    """Check if tweet is within the last N hours"""
    if not created_at_str:
        return True
    try:
        dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except (ValueError, TypeError):
        return True


# ==================== 采集模块 ====================

def fetch_account_tweets():
    """Module 1: 关注账号推文采集"""
    print("\n📡 [1/3] 采集关注账号推文...")
    all_tweets = []
    total_cost = 0
    errors = []

    for handle, config in ACCOUNTS.items():
        result = api_call("twitter_user_tweets", {
            "username": handle,
            "maxResults": config["max"],
            "product": "Latest",
            "includeReplies": False,
            "includeRetweets": False,
        })

        if not result:
            errors.append(f"@{handle}: API call failed")
            time.sleep(1)
            continue

        cost = int(result.get("cost", 1))
        total_cost += cost
        tweets = result.get("data", []) or []

        recent = [t for t in tweets if is_within_hours(t.get("createdAt"), 48)]
        for t in recent:
            all_tweets.append(parse_tweet(t, source_type=config["type"], source_handle=handle))

        print(f"  ✓ @{handle}: {len(recent)}/{len(tweets)} tweets (48h), cost={cost}")
        time.sleep(0.3)

    print(f"  📊 账号采集完成: {len(all_tweets)} tweets, cost={total_cost}")
    if errors:
        print(f"  ⚠️ {len(errors)} errors: {'; '.join(errors)}")
    return all_tweets, total_cost


def fetch_hot_topics():
    """Module 2: 行业热点关键词搜索"""
    print("\n🔥 [2/3] 搜索行业热点...")
    all_tweets = []
    total_cost = 0
    seen_ids = set()

    for q in SEARCH_QUERIES:
        payload = {
            "keywords": q["keywords"],
            "maxResults": q.get("maxResults", 10),
            "product": q.get("product", "Top"),
            "minLikes": q.get("minLikes", 0),
            "excludeRetweets": True,
        }
        if q.get("lang"):
            payload["lang"] = q["lang"]

        result = api_call("twitter_search", payload)
        if not result:
            time.sleep(1)
            continue

        cost = int(result.get("cost", 1)) if isinstance(result, dict) else 1
        total_cost += cost

        tweets = result.get("data", result) if isinstance(result, dict) else result
        if not isinstance(tweets, list):
            tweets = []

        count = 0
        for t in tweets:
            tid = t.get("id", "")
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            if is_within_hours(t.get("createdAt"), 72):
                parsed = parse_tweet(t, source_type="hot_topic", tag=q.get("tag", ""))
                all_tweets.append(parsed)
                count += 1

        print(f"  ✓ [{q.get('tag','')}] \"{q['keywords']}\": {count} tweets, cost={cost}")
        time.sleep(0.3)

    print(f"  📊 热点搜索完成: {len(all_tweets)} tweets, cost={total_cost}")
    return all_tweets, total_cost


def fetch_kol_search():
    """Module 2.5: KOL 推文搜索补采（带互动数据）"""
    print("\n👤 [2.5/3] 搜索 KOL 推文（补采互动数据）...")
    all_tweets = []
    total_cost = 0
    seen_ids = set()

    for q in KOL_SEARCHES:
        payload = {
            "fromUser": q["fromUser"],
            "maxResults": q.get("maxResults", 5),
            "product": q.get("product", "Latest"),
            "excludeRetweets": True,
        }

        result = api_call("twitter_search", payload)
        if not result:
            time.sleep(1)
            continue

        cost = int(result.get("cost", 1)) if isinstance(result, dict) else 1
        total_cost += cost

        tweets = result.get("data", result) if isinstance(result, dict) else result
        if not isinstance(tweets, list):
            tweets = []

        count = 0
        for t in tweets:
            tid = t.get("id", "")
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            if is_within_hours(t.get("createdAt"), 72):
                parsed = parse_tweet(t, source_type="kol", tag=q.get("tag", ""))
                all_tweets.append(parsed)
                count += 1

        print(f"  ✓ @{q['fromUser']}: {count} tweets, cost={cost}")
        time.sleep(0.3)

    print(f"  📊 KOL 补采完成: {len(all_tweets)} tweets, cost={total_cost}")
    return all_tweets, total_cost


def fetch_competitor_buzz():
    """Module 3: 竞品舆情搜索"""
    print("\n🏷️ [3/3] 搜索竞品舆情...")
    all_tweets = []
    total_cost = 0
    seen_ids = set()

    for q in COMPETITOR_SEARCHES:
        payload = {
            "keywords": q["keywords"],
            "maxResults": q.get("maxResults", 10),
            "product": q.get("product", "Top"),
            "minLikes": q.get("minLikes", 0),
            "excludeRetweets": q.get("excludeRetweets", True),
        }

        result = api_call("twitter_search", payload)
        if not result:
            time.sleep(1)
            continue

        cost = int(result.get("cost", 1)) if isinstance(result, dict) else 1
        total_cost += cost

        tweets = result.get("data", result) if isinstance(result, dict) else result
        if not isinstance(tweets, list):
            tweets = []

        count = 0
        for t in tweets:
            tid = t.get("id", "")
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            if is_within_hours(t.get("createdAt"), 72):
                parsed = parse_tweet(t, source_type="competitor_buzz", tag=q.get("tag", ""))
                all_tweets.append(parsed)
                count += 1

        print(f"  ✓ [{q.get('tag','')}] \"{q['keywords']}\": {count} tweets, cost={cost}")
        time.sleep(0.3)

    print(f"  📊 竞品舆情完成: {len(all_tweets)} tweets, cost={total_cost}")
    return all_tweets, total_cost


# ==================== 主流程 ====================

def fetch_all():
    """Run all collection modules"""
    if not TOKEN:
        print("❌ TWITTER_TOKEN 未设置")
        return []

    print(f"🚀 X/Twitter 采集 v2 启动 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    account_tweets, cost1 = fetch_account_tweets()
    hot_tweets, cost2 = fetch_hot_topics()
    kol_tweets, cost_kol = fetch_kol_search()
    competitor_tweets, cost3 = fetch_competitor_buzz()

    # Merge & deduplicate by tweet ID (KOL search overrides account data for same tweet)
    all_tweets = []
    seen_ids = set()
    # KOL search first (has engagement data), then others
    for t in kol_tweets + account_tweets + hot_tweets + competitor_tweets:
        tid = t.get("id", "")
        if tid and tid in seen_ids:
            continue
        if tid:
            seen_ids.add(tid)
        all_tweets.append(t)

    # Sort by engagement score
    all_tweets.sort(key=lambda x: (x.get("likes", 0) + x.get("retweets", 0) * 3 + x.get("quotes", 0) * 2), reverse=True)

    # Build output with metadata
    output = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_tweets": len(all_tweets),
        "total_cost": cost1 + cost2 + cost3,
        "sections": {
            "account_tweets": len(account_tweets),
            "hot_topics": len(hot_tweets),
            "competitor_buzz": len(competitor_tweets),
        },
        "tweets": all_tweets,
    }

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_cost = cost1 + cost2 + cost3
    print(f"\n{'='*50}")
    print(f"✅ 采集完成!")
    print(f"  📝 账号推文: {len(account_tweets)}")
    print(f"  🔥 行业热点: {len(hot_tweets)}")
    print(f"  🏷️ 竞品舆情: {len(competitor_tweets)}")
    print(f"  📊 总计: {len(all_tweets)} tweets (去重后)")
    print(f"  💰 API credits: {total_cost}")
    print(f"  💾 保存到: {OUTPUT_PATH}")

    return all_tweets


if __name__ == "__main__":
    fetch_all()
