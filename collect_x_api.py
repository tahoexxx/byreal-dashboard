#!/usr/bin/env python3
"""
X/Twitter 采集 — 用 6551 OpenTwitter API 拉取关注账号的最近推文
API: https://ai.6551.io/open/twitter_user_tweets
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
API_URL = "https://ai.6551.io/open/twitter_user_tweets"
TOKEN = os.environ.get("TWITTER_TOKEN", "")

# 关注账号及分类
ACCOUNTS = {
    "byreal_io": "byreal",
    "JupiterExchange": "competitor",
    "MeteoraAG": "competitor",
    "Raydium": "competitor",
    "orca_so": "competitor",
    "solana": "ecosystem",
    "SolanaFloor": "ecosystem",
    "CryptoHayes": "kol",
    "toly": "kol",
    "benbybit": "kol",
    "colinwu": "kol",
    "hellosuoha": "kol",
    "victalk6886": "kol",
    "luyaoyuan": "kol",
    "0xSunNFT": "kol",
    "0xSleepinRain": "kol",
    "ShanghaoJin": "kol",
    "Michael_Liu93": "kol",
}


def fetch_user_tweets(username, max_results=10):
    """Fetch recent tweets from a user via 6551 API"""
    payload = json.dumps({
        "username": username,
        "maxResults": max_results,
        "product": "Latest",
        "includeReplies": False,
        "includeRetweets": False,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode())


def is_within_hours(created_at_str, hours=24):
    """Check if tweet is within the last N hours"""
    if not created_at_str:
        return True  # include if no date
    try:
        # 6551 format: "Sat Feb 28 04:12:48 +0000 2026"
        dt = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except (ValueError, TypeError):
        return True


def fetch_all():
    """Fetch tweets from all tracked accounts"""
    if not TOKEN:
        print("❌ TWITTER_TOKEN 未设置")
        return []

    all_tweets = []
    errors = []
    total_cost = 0

    for handle, acct_type in ACCOUNTS.items():
        try:
            result = fetch_user_tweets(handle, max_results=10)
            cost = int(result.get("cost", 1))
            total_cost += cost
            tweets = result.get("data", []) or []

            # Filter to last 24h
            recent = [t for t in tweets if is_within_hours(t.get("createdAt"), 24)]

            for t in recent:
                all_tweets.append({
                    "handle": handle,
                    "name": t.get("userName", handle),
                    "type": acct_type,
                    "content": t.get("text", ""),
                    "likes": t.get("favoriteCount", 0),
                    "retweets": t.get("retweetCount", 0),
                    "replies": t.get("replyCount", 0),
                    "views": t.get("viewCount", 0),
                    "timestamp": t.get("createdAt", ""),
                    "url": f"https://x.com/{handle}/status/{t['id']}" if t.get("id") else "",
                })

            print(f"  ✓ @{handle}: {len(recent)}/{len(tweets)} tweets (24h), cost={cost}")
            time.sleep(0.5)  # Be nice

        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            errors.append(f"@{handle}: HTTP {e.code} - {body}")
            print(f"  ✗ @{handle}: HTTP {e.code}")
            time.sleep(1)
        except Exception as e:
            errors.append(f"@{handle}: {e}")
            print(f"  ✗ @{handle}: {e}")
            time.sleep(0.5)

    # Sort by engagement
    all_tweets.sort(key=lambda x: x["likes"] + x["retweets"] * 2, reverse=True)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_tweets, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(all_tweets)} tweets saved to {OUTPUT_PATH}")
    print(f"📊 Total API cost: {total_cost} credits")
    if errors:
        print(f"⚠️ {len(errors)} errors:")
        for e in errors:
            print(f"   {e}")

    return all_tweets


if __name__ == "__main__":
    fetch_all()
