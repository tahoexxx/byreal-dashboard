#!/usr/bin/env python3
"""
X/Twitter API 采集 — 用官方 API 拉取关注账号的最近推文
凭证: ~/.openclaw/workspace/.x_api_keys.json (OAuth 1.0a)
输出: data/x_cache.json
"""

import json
import base64
import hmac
import hashlib
import time
import urllib.request
import urllib.parse
import urllib.error
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
KEYS_PATH = Path.home() / ".openclaw" / "workspace" / ".x_api_keys.json"
OUTPUT_PATH = BASE_DIR / "data" / "x_cache.json"

# 关注账号及分类
ACCOUNTS = {
    # handle → type
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
    "laolu": "kol",
    "0xSunNFT": "kol",
    "0xSleepinRain": "kol",
    "ShanghaoJin": "kol",
    "Michael_Liu93": "kol",
}

# Free tier: 100 reads/month for v2. Basic: 10k reads/month.
# We do ~18 user lookups + 18 timeline reads = ~36 reads per day.
# Basic tier should be fine.

def load_keys():
    with open(KEYS_PATH) as f:
        return json.load(f)


def oauth_request(method, url, keys, params=None):
    """Make an OAuth 1.0a signed request to X API v2"""
    params = params or {}

    oauth_params = {
        "oauth_consumer_key": keys["consumer_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": keys["access_token"],
        "oauth_version": "1.0",
    }

    # All params for signature
    all_params = {**oauth_params, **params}
    params_str = "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )

    base_url = url.split("?")[0]
    base_str = f"{method}&{urllib.parse.quote(base_url, safe='')}&{urllib.parse.quote(params_str, safe='')}"
    signing_key = (
        f"{urllib.parse.quote(keys['consumer_secret'], safe='')}"
        f"&{urllib.parse.quote(keys['access_token_secret'], safe='')}"
    )
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = sig

    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )

    full_url = base_url
    if params:
        qs = urllib.parse.urlencode(params)
        full_url = f"{base_url}?{qs}"

    req = urllib.request.Request(full_url, headers={"Authorization": auth_header})
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode())


def get_user_id(handle, keys):
    """Get user ID from handle"""
    url = f"https://api.x.com/2/users/by/username/{handle}"
    data = oauth_request("GET", url, keys, {"user.fields": "name"})
    user = data.get("data", {})
    return user.get("id"), user.get("name", handle)


def get_user_tweets(user_id, keys, since_hours=24, max_results=10):
    """Get recent tweets from a user"""
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://api.x.com/2/users/{user_id}/tweets"
    params = {
        "max_results": str(min(max_results, 100)),
        "start_time": since,
        "tweet.fields": "created_at,public_metrics,text",
        "exclude": "retweets,replies",
    }
    return oauth_request("GET", url, keys, params)


def fetch_all():
    """Fetch tweets from all tracked accounts"""
    keys = load_keys()
    all_tweets = []
    errors = []

    for handle, acct_type in ACCOUNTS.items():
        try:
            user_id, name = get_user_id(handle, keys)
            if not user_id:
                errors.append(f"{handle}: user not found")
                continue

            result = get_user_tweets(user_id, keys)
            tweets = result.get("data", [])

            for t in tweets:
                metrics = t.get("public_metrics", {})
                all_tweets.append({
                    "handle": handle,
                    "name": name,
                    "type": acct_type,
                    "content": t.get("text", ""),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "views": metrics.get("impression_count", 0),
                    "timestamp": t.get("created_at", ""),
                    "url": f"https://x.com/{handle}/status/{t['id']}",
                })

            print(f"  ✓ @{handle}: {len(tweets)} tweets")
            time.sleep(1)  # Rate limit courtesy

        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            errors.append(f"@{handle}: HTTP {e.code} - {body}")
            print(f"  ✗ @{handle}: HTTP {e.code}")
            if e.code == 429:
                print("    Rate limited, waiting 60s...")
                time.sleep(60)
            else:
                time.sleep(1)
        except Exception as e:
            errors.append(f"@{handle}: {e}")
            print(f"  ✗ @{handle}: {e}")
            time.sleep(1)

    # Sort by engagement
    all_tweets.sort(key=lambda x: x["likes"] + x["retweets"] * 2, reverse=True)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_tweets, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(all_tweets)} tweets saved to {OUTPUT_PATH}")
    if errors:
        print(f"⚠️ {len(errors)} errors:")
        for e in errors:
            print(f"   {e}")

    return all_tweets


if __name__ == "__main__":
    fetch_all()
