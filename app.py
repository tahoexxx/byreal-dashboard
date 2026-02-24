#!/usr/bin/env python3
"""
Byreal Ops Dashboard — Streamlit 版
"""

import json
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================
st.set_page_config(
    page_title="Byreal Ops Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).parent / "data"


# ============================================================
# 自动采集（Streamlit Cloud 上没有本地数据）
# ============================================================
import subprocess
import sys

def auto_collect():
    """如果没有最新数据，自动运行 collect.py"""
    summary_path = DATA_DIR / "latest" / "summary.json"
    if summary_path.exists():
        # 检查数据是否是今天的
        try:
            with open(summary_path) as f:
                d = json.load(f)
            if d.get("date") == datetime.now().strftime("%Y-%m-%d"):
                return  # 今天的数据已存在
        except Exception:
            pass
    
    with st.spinner("⏳ 正在采集数据，首次加载约需 30 秒..."):
        collect_script = Path(__file__).parent / "collect.py"
        result = subprocess.run(
            [sys.executable, str(collect_script)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            st.error(f"采集失败: {result.stderr}")

auto_collect()


# ============================================================
# 样式
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');
    
    .stApp { background-color: #0a0e17; }
    .block-container { padding-top: 2rem; max-width: 1400px; }
    
    h1, h2, h3, h4, h5, h6, p, span, div, li { color: #f1f5f9 !important; }
    
    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #22d3ee !important;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8 !important;
        margin-top: 0.3rem;
    }
    .metric-change-up { color: #10b981 !important; font-size: 0.85rem; }
    .metric-change-down { color: #ef4444 !important; font-size: 0.85rem; }
    
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #22d3ee !important;
        margin: 1.5rem 0 0.8rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1e293b;
    }
    
    .alert-red { background: #ef444420; border-left: 3px solid #ef4444; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    .alert-orange { background: #f59e0b20; border-left: 3px solid #f59e0b; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    .alert-green { background: #10b98120; border-left: 3px solid #10b981; padding: 0.6rem 1rem; border-radius: 6px; margin: 0.3rem 0; }
    
    .pool-table { width: 100%; }
    .pool-table th { 
        background: #151d2e; 
        color: #94a3b8 !important; 
        padding: 0.6rem 0.8rem; 
        font-size: 0.8rem; 
        text-align: right;
        border-bottom: 1px solid #1e293b;
    }
    .pool-table th:first-child { text-align: left; }
    .pool-table td { 
        padding: 0.6rem 0.8rem; 
        font-family: 'JetBrains Mono', monospace; 
        font-size: 0.85rem;
        text-align: right;
        border-bottom: 1px solid #1e293b10;
    }
    .pool-table td:first-child { 
        text-align: left; 
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
    }
    .pool-table tr:hover { background: #1c2840; }
    
    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    
    div[data-testid="stMetric"] { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 1rem; }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #22d3ee !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 数据加载
# ============================================================
@st.cache_data(ttl=300)
def load_data():
    summary_path = DATA_DIR / "latest" / "summary.json"
    if not summary_path.exists():
        return None
    with open(summary_path) as f:
        return json.load(f)


def fmt_usd(val):
    if val >= 1_000_000_000:
        return f"${val/1e9:.2f}B"
    if val >= 1_000_000:
        return f"${val/1e6:.2f}M"
    if val >= 1_000:
        return f"${val/1e3:.1f}K"
    return f"${val:.0f}"


def fmt_pct(val):
    if val is None:
        return "—"
    arrow = "▲" if val >= 0 else "▼"
    return f"{arrow} {abs(val)*100:.1f}%"


# ============================================================
# 主页面
# ============================================================
data = load_data()

if not data:
    st.error("❌ 未找到数据，请先运行 `python3 collect.py`")
    st.stop()

p = data["platform"]
m = data.get("market") or {}
if not isinstance(m, dict):
    m = {}
alerts = data.get("alerts", [])

# Header
st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1.5rem;">
    <div>
        <h1 style="font-size:1.8rem; font-weight:700; margin:0;">⚡ Byreal Ops Dashboard</h1>
        <p style="color:#64748b !important; font-size:0.9rem; margin:0.3rem 0 0 0;">{data['date']} · 更新于 {data.get('ts', '')[:19].replace('T', ' ')} UTC</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ━━━━ AI 总结 ━━━━
ai_insight = data.get("aiInsight", "")
ai_public = data.get("aiPublic", "")

if ai_insight or ai_public:
    ai_cols = st.columns(2)
    with ai_cols[0]:
        st.markdown('<div class="section-title">🧠 运营洞察</div>', unsafe_allow_html=True)
        if ai_insight:
            st.markdown(f"""
            <div style="background:#111827; border:1px solid #22d3ee30; border-radius:12px; padding:1.2rem; line-height:1.8; font-size:0.95rem;">
                {ai_insight}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#64748b;">暂无数据</div>', unsafe_allow_html=True)
    
    with ai_cols[1]:
        st.markdown('<div class="section-title">📰 平台快报</div>', unsafe_allow_html=True)
        if ai_public:
            st.markdown(f"""
            <div style="background:#111827; border:1px solid #10b98130; border-radius:12px; padding:1.2rem; line-height:1.8; font-size:0.95rem;">
                {ai_public}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#64748b;">暂无数据</div>', unsafe_allow_html=True)

# ━━━━ 运营日报 ━━━━
daily_report_content = data.get("dailyReport", "")

if not daily_report_content:
    # fallback: 尝试本地文件
    daily_report_path = Path(f"/Users/martis/.openclaw/workspace/byreal-daily/daily-{data['date']}.txt")
    if daily_report_path.exists():
        try:
            with open(daily_report_path) as f:
                daily_report_content = f.read()
        except Exception:
            pass

if not daily_report_content:
    daily_report_content = "_暂无今日日报数据_"

with st.expander("📋 运营日报", expanded=False):
    st.markdown(f"""
    <div style="background:#111827; border:1px solid #1e293b; border-radius:12px; padding:1.2rem; line-height:1.8; font-size:0.9rem; white-space:pre-wrap; font-family:monospace;">
{daily_report_content}
    </div>
    """, unsafe_allow_html=True)

# ━━━━ 预警 ━━━━
red_alerts = [a for a in alerts if a["lv"] == "red"]
orange_alerts = [a for a in alerts if a["lv"] == "orange"]
green_alerts = [a for a in alerts if a["lv"] == "green"]

if red_alerts or orange_alerts or green_alerts:
    st.markdown('<div class="section-title">⚠️ 行动项</div>', unsafe_allow_html=True)

    # 按类别分组合并，减少版面占用
    from collections import defaultdict
    grouped = defaultdict(list)
    for a in red_alerts + orange_alerts + green_alerts:
        grouped[a.get("cat", "other")].append(a)

    for cat, items in grouped.items():
        if cat == "reward" and len(items) > 1:
            # 激励到期：合并成一行汇总 + 折叠详情
            names_by_days = defaultdict(list)
            for a in items:
                # 从 msg 提取天数和池名
                msg = a["msg"]
                import re
                m = re.match(r"(.+?) 激励 (\d+) 天后到期", msg)
                if m:
                    names_by_days[m.group(2)].append(m.group(1))
                else:
                    names_by_days["?"].append(msg)
            summary_parts = []
            for days, names in sorted(names_by_days.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99):
                summary_parts.append(f"**{days}天内到期({len(names)}个):** {', '.join(names)}")
            st.markdown(f'<div class="alert-red">🔴 激励到期提醒 — 共 {len(items)} 个池子需续期</div>', unsafe_allow_html=True)
            with st.expander(f"查看详情", expanded=False):
                for part in summary_parts:
                    st.markdown(part)

        elif cat == "pool" and len(items) > 1:
            # 高APR：合并成一行
            pool_info = []
            for a in items:
                pool_info.append(a["msg"].replace("，注意监控", ""))
            st.markdown(f'<div class="alert-orange">🟠 异常高 APR ({len(items)}个池子): {" | ".join(pool_info)}</div>', unsafe_allow_html=True)

        else:
            # 其他类别正常逐条显示
            for a in items:
                lv = a["lv"]
                icon = {"red": "🔴", "orange": "🟠", "green": "🟢"}.get(lv, "⚪")
                st.markdown(f'<div class="alert-{lv}">{icon} {a["msg"]}</div>', unsafe_allow_html=True)

# ━━━━ 平台概览 ━━━━
st.markdown('<div class="section-title">📊 平台概览</div>', unsafe_allow_html=True)

cols = st.columns(6)
metrics = [
    ("TVL", fmt_usd(p["tvl"]), fmt_pct(p.get("tvlChange")) if p.get("tvlChange") is not None else None),
    ("24h 交易量", fmt_usd(p["vol24h"]), fmt_pct(p.get("volChange")) if p.get("volChange") is not None else None),
    ("7d 交易量", fmt_usd(p["vol7d"]), None),
    ("24h 手续费", fmt_usd(p["fee24h"]), None),
    ("24h 协议收入", fmt_usd(p["rev24h"]), None),
    ("活跃池", f"{p['active']}/{p['total']}", None),
]

for col, (label, value, change) in zip(cols, metrics):
    with col:
        change_html = ""
        if change:
            cls = "metric-change-up" if "▲" in change else "metric-change-down"
            change_html = f'<div class="{cls}">{change}</div>'
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """, unsafe_allow_html=True)

# ━━━━ 市场环境 ━━━━
st.markdown('<div class="section-title">🌍 市场环境</div>', unsafe_allow_html=True)

mcols = st.columns(4)
sol = m.get("sol", {})
btc = m.get("btc", {})
eth = m.get("eth", {})
fng = m.get("fearGreed", {})

market_items = [
    ("SOL", f"${sol.get('price', 0):.2f}", sol.get("change24h", 0)),
    ("BTC", f"${btc.get('price', 0):,.0f}", btc.get("change24h", 0)),
    ("ETH", f"${eth.get('price', 0):,.0f}", eth.get("change24h", 0)),
    ("Fear & Greed", str(fng.get("value", "?")), None),
]

for col, (label, value, change) in zip(mcols, market_items):
    with col:
        change_html = ""
        if change is not None:
            color = "#10b981" if change >= 0 else "#ef4444"
            arrow = "▲" if change >= 0 else "▼"
            change_html = f'<div style="color:{color} !important; font-size:0.85rem;">{arrow} {abs(change):.1f}%</div>'
        elif label == "Fear & Greed":
            fg_val = fng.get("value", 50)
            color = "#ef4444" if fg_val < 25 else "#f59e0b" if fg_val < 50 else "#10b981" if fg_val < 75 else "#22d3ee"
            change_html = f'<div style="color:{color} !important; font-size:0.85rem;">{fng.get("label", "")}</div>'
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """, unsafe_allow_html=True)

# ━━━━ 业务线 ━━━━
st.markdown('<div class="section-title">📦 业务线分布（点击展开查看池子详情）</div>', unsafe_allow_html=True)

biz = data.get("bizLines", {})
all_pools = data.get("pools", [])

for key in ["xStocks", "Gold_RWA", "Major", "Stablecoin", "Other"]:
    b = biz.get(key)
    if not b or b["tvl"] <= 0:
        continue
    share = b["tvl"] / p["tvl"] * 100 if p["tvl"] > 0 else 0
    
    header = f"**{key}** — TVL {fmt_usd(b['tvl'])} ({share:.1f}%) | Vol {fmt_usd(b['vol24h'])} | Fee {fmt_usd(b['fee24h'])} | {b['count']}池"
    
    with st.expander(header):
        # 该业务线下的池子，按 TVL 降序
        cat_pools = sorted(
            [pool for pool in all_pools if pool.get("biz") == key],
            key=lambda x: x["tvl"], reverse=True
        )
        if cat_pools:
            rows_html = '<table class="pool-table"><tr><th>交易对</th><th>TVL</th><th>24h Vol</th><th>24h Fee</th><th>APR</th><th>价格</th><th>24h 变化</th></tr>'
            for pool in cat_pools:
                chg = pool.get("pc1d", 0)
                if chg:
                    chg_color = "#10b981" if chg >= 0 else "#ef4444"
                    chg_str = f'<span style="color:{chg_color}">{"▲" if chg >= 0 else "▼"} {abs(chg)*100:.1f}%</span>'
                else:
                    chg_str = "—"
                apr_str = f"{pool['apr']*100:.1f}%" if pool.get("apr") else "—"
                px_str = f"${pool['px']:.2f}" if pool["px"] < 1000 else f"${pool['px']:,.0f}" if pool["px"] > 0 else "—"
                
                rows_html += f'<tr><td>{pool["name"]}</td><td>{fmt_usd(pool["tvl"])}</td><td>{fmt_usd(pool["v24h"])}</td><td>{fmt_usd(pool["f24h"])}</td><td>{apr_str}</td><td>{px_str}</td><td>{chg_str}</td></tr>'
            rows_html += '</table>'
            st.markdown(rows_html, unsafe_allow_html=True)
        else:
            st.write("暂无池子数据")

# ━━━━ 竞品对比 ━━━━
st.markdown('<div class="section-title">🏆 竞品对比</div>', unsafe_allow_html=True)

comps = data.get("competitors", {})
comp_rows = []
for slug, c in sorted(comps.items(), key=lambda x: x[1].get("tvl", 0), reverse=True):
    marker = " ⭐" if slug == "byreal" else ""
    comp_rows.append({
        "协议": c.get("name", slug) + marker,
        "TVL": fmt_usd(c.get("tvl", 0)),
        "24h Vol": fmt_usd(c.get("vol24h", 0)) if c.get("vol24h") else "—",
        "7d Vol": fmt_usd(c.get("vol7d", 0)) if c.get("vol7d") else "—",
    })

if comp_rows:
    comp_html = '<table class="pool-table"><tr>'
    for h in comp_rows[0].keys():
        comp_html += f'<th>{h}</th>'
    comp_html += '</tr>'
    for row in comp_rows:
        comp_html += '<tr>'
        for v in row.values():
            comp_html += f'<td>{v}</td>'
        comp_html += '</tr>'
    comp_html += '</table>'
    st.markdown(comp_html, unsafe_allow_html=True)

# ━━━━ X/Twitter 热点 ━━━━
st.markdown('<div class="section-title">𝕏 Twitter 热点</div>', unsafe_allow_html=True)

x_trends = data.get("xTrends", [])
with st.expander(f"📱 X/Twitter 动态 ({len(x_trends)} 条)", expanded=True):
    if x_trends:
        for tweet in x_trends[:10]:
            # 竞品推文橙色边框
            border_color = "#f59e0b" if tweet.get("type") == "competitor" else "#1e293b"
            type_emoji = {
                "byreal": "⭐",
                "competitor": "🔶",
                "ecosystem": "🌐",
                "kol": "👤"
            }.get(tweet.get("type", ""), "")
            
            st.markdown(f"""
            <div style="background:#111827; border:1px solid {border_color}; border-radius:8px; padding:1rem; margin:0.5rem 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                    <span style="color:#22d3ee; font-weight:600;">{type_emoji} @{tweet['handle']}</span>
                    <span style="color:#64748b; font-size:0.85rem;">{tweet.get('name', '')}</span>
                </div>
                <div style="color:#e2e8f0; margin:0.5rem 0; line-height:1.6;">
                    {tweet.get('content', '')[:200]}{'...' if len(tweet.get('content', '')) > 200 else ''}
                </div>
                <div style="display:flex; gap:1.5rem; color:#64748b; font-size:0.85rem;">
                    <span>❤️ {tweet.get('likes', 0):,}</span>
                    <span>🔁 {tweet.get('retweets', 0):,}</span>
                    <span>💬 {tweet.get('replies', 0):,}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📊 暂无 X/Twitter 数据 (等待真实 API 接入)")

# ━━━━ Reddit 热点 ━━━━
st.markdown('<div class="section-title">🔥 Reddit 热帖</div>', unsafe_allow_html=True)

reddit_hot = data.get("redditHot", [])
with st.expander(f"💬 Reddit 热门讨论 ({len(reddit_hot)} 条)", expanded=True):
    if reddit_hot:
        for post in reddit_hot[:10]:
            # Byreal/Solana 相关帖子高亮
            border_color = "#22d3ee" if post.get("isRelevant") else "#1e293b"
            relevant_mark = "⭐ " if post.get("isRelevant") else ""
            
            st.markdown(f"""
            <div style="background:#111827; border:1px solid {border_color}; border-radius:8px; padding:1rem; margin:0.5rem 0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                    <span style="color:#f59e0b; font-weight:600;">r/{post['subreddit']}</span>
                    <span style="color:#64748b; font-size:0.85rem;">{post.get('flair', '')}</span>
                </div>
                <div style="color:#e2e8f0; font-weight:500; margin:0.5rem 0;">
                    {relevant_mark}{post.get('title', '')}
                </div>
                <div style="display:flex; gap:1.5rem; color:#64748b; font-size:0.85rem;">
                    <span>⬆️ {post.get('score', 0):,} ({post.get('upvoteRatio', 0)*100:.0f}%)</span>
                    <span>💬 {post.get('numComments', 0):,} comments</span>
                    <span style="color:#64748b;">by u/{post.get('author', '')}</span>
                </div>
                <a href="{post.get('url', '')}" target="_blank" style="color:#22d3ee; font-size:0.85rem; text-decoration:none;">🔗 查看讨论 →</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📊 暂无 Reddit 数据")

# ━━━━ Byreal 账号分析 ━━━━
st.markdown('<div class="section-title">📊 @byreal_io 账号分析</div>', unsafe_allow_html=True)

byreal_acc = data.get("byrealAccount", {})
acc_cols = st.columns(4)

acc_metrics = [
    ("Followers", f"{byreal_acc.get('followers', 0):,}" if byreal_acc.get('followers') else "待接入", 
     f"+{byreal_acc.get('followersChange7d', 0):,} (7d)" if byreal_acc.get('followersChange7d') else None),
    ("推文数 (7d)", f"{byreal_acc.get('tweets7d', 0):,}" if byreal_acc.get('tweets7d') else "—", None),
    ("平均互动率", f"{byreal_acc.get('avgEngagement', 0):.1f}%" if byreal_acc.get('avgEngagement') else "—", None),
    ("状态", "🟢 活跃" if byreal_acc.get('tweets7d', 0) > 0 else "🟡 待更新", None),
]

for col, (label, value, change) in zip(acc_cols, acc_metrics):
    with col:
        change_html = ""
        if change:
            color = "#10b981"
            change_html = f'<div style="color:{color} !important; font-size:0.85rem;">{change}</div>'
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="font-size:1.4rem;">{value}</div>
            <div class="metric-label">{label}</div>
            {change_html}
        </div>
        """, unsafe_allow_html=True)

# 最近推文表现
recent_tweets = byreal_acc.get("recentTweets", [])
if recent_tweets:
    st.markdown('<div style="margin-top:1rem; color:#94a3b8; font-size:0.9rem; font-weight:600;">最近推文表现</div>', unsafe_allow_html=True)
    for tw in recent_tweets[:5]:
        st.markdown(f"""
        <div style="background:#111827; border:1px solid #1e293b; border-radius:6px; padding:0.8rem; margin:0.3rem 0;">
            <div style="color:#e2e8f0; font-size:0.9rem; margin-bottom:0.3rem;">{tw.get('content', '')[:100]}...</div>
            <div style="display:flex; gap:1rem; color:#64748b; font-size:0.8rem;">
                <span>❤️ {tw.get('likes', 0):,}</span>
                <span>🔁 {tw.get('retweets', 0):,}</span>
                <span>💬 {tw.get('replies', 0):,}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("📊 等待接入真实 X API 数据")

# ━━━━ xStocks ━━━━
xs = data.get("xStocks", [])
if xs:
    st.markdown('<div class="section-title">📈 xStocks</div>', unsafe_allow_html=True)
    xs_rows = []
    for s in xs[:12]:
        chg = s.get("pc1d", 0)
        chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg)*100:.1f}%" if chg else "—"
        xs_rows.append({
            "交易对": s["name"],
            "价格": f"${s['px']:.2f}" if s["px"] < 1000 else f"${s['px']:,.0f}",
            "24h 变化": chg_str,
            "TVL": fmt_usd(s["tvl"]),
            "24h Vol": fmt_usd(s["v24h"]),
            "APR": f"{s['apr']*100:.1f}%" if s.get("apr") else "—",
        })
    
    xs_html = '<table class="pool-table"><tr>'
    for h in xs_rows[0].keys():
        xs_html += f'<th>{h}</th>'
    xs_html += '</tr>'
    for row in xs_rows:
        xs_html += '<tr>'
        for i, v in enumerate(row.values()):
            style = ""
            if i == 2 and "▲" in str(v):
                style = ' style="color:#10b981 !important;"'
            elif i == 2 and "▼" in str(v):
                style = ' style="color:#ef4444 !important;"'
            xs_html += f'<td{style}>{v}</td>'
        xs_html += '</tr>'
    xs_html += '</table>'
    st.markdown(xs_html, unsafe_allow_html=True)

# ━━━━ Top 池子 ━━━━
st.markdown('<div class="section-title">🏊 Top 15 池子 (by TVL)</div>', unsafe_allow_html=True)

rankings = data.get("rankings", {})
top_tvl = rankings.get("topTvl", [])
if top_tvl:
    pool_rows = []
    for i, pool in enumerate(top_tvl, 1):
        pool_rows.append({
            "#": i,
            "交易对": pool["name"],
            "业务线": pool["biz"],
            "TVL": fmt_usd(pool["tvl"]),
            "24h Vol": fmt_usd(pool["v24h"]),
            "24h Fee": fmt_usd(pool["f24h"]),
            "APR": f"{pool['apr']*100:.1f}%" if pool.get("apr") else "—",
            "Fee/TVL": f"{pool['ftv']*100:.2f}%" if pool.get("ftv") else "—",
        })
    
    pool_html = '<table class="pool-table"><tr>'
    for h in pool_rows[0].keys():
        pool_html += f'<th>{h}</th>'
    pool_html += '</tr>'
    for row in pool_rows:
        pool_html += '<tr>'
        for v in row.values():
            pool_html += f'<td>{v}</td>'
        pool_html += '</tr>'
    pool_html += '</table>'
    st.markdown(pool_html, unsafe_allow_html=True)

# ━━━━ Top Vol ━━━━
st.markdown('<div class="section-title">🔥 Top 15 池子 (by 24h Volume)</div>', unsafe_allow_html=True)

top_vol = rankings.get("topVol", [])
if top_vol:
    vol_rows = []
    for i, pool in enumerate(top_vol, 1):
        vol_rows.append({
            "#": i,
            "交易对": pool["name"],
            "业务线": pool["biz"],
            "24h Vol": fmt_usd(pool["v24h"]),
            "TVL": fmt_usd(pool["tvl"]),
            "24h Fee": fmt_usd(pool["f24h"]),
        })
    
    vol_html = '<table class="pool-table"><tr>'
    for h in vol_rows[0].keys():
        vol_html += f'<th>{h}</th>'
    vol_html += '</tr>'
    for row in vol_rows:
        vol_html += '<tr>'
        for v in row.values():
            vol_html += f'<td>{v}</td>'
        vol_html += '</tr>'
    vol_html += '</table>'
    st.markdown(vol_html, unsafe_allow_html=True)

# ━━━━ 历史趋势 ━━━━
st.markdown('<div class="section-title">📈 历史趋势</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_history():
    """加载所有历史 summary.json"""
    history = []
    if not DATA_DIR.exists():
        return history
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and d.name != "latest" and not d.name.startswith("."):
            sf = d / "summary.json"
            if sf.exists():
                try:
                    with open(sf) as f:
                        s = json.load(f)
                    plat = s.get("platform", {})
                    blines = s.get("bizLines", {})
                    row = {
                        "日期": s.get("date", d.name),
                        "TVL": plat.get("tvl", 0),
                        "24h Vol": plat.get("vol24h", 0),
                        "24h Fee": plat.get("fee24h", 0),
                        "活跃池": plat.get("active", 0),
                    }
                    # 各业务线 TVL
                    for bk in ["xStocks", "Gold_RWA", "Major", "Stablecoin", "Other"]:
                        row[f"{bk} TVL"] = blines.get(bk, {}).get("tvl", 0)
                    history.append(row)
                except Exception:
                    pass
    return history

hist = load_history()
if len(hist) >= 2:
    import altair as alt
    
    df = pd.DataFrame(hist)
    df["日期"] = pd.to_datetime(df["日期"])
    
    trend_tab1, trend_tab2, trend_tab3 = st.tabs(["TVL & Volume", "业务线 TVL", "Fee & 活跃池"])
    
    with trend_tab1:
        base = alt.Chart(df).encode(x=alt.X("日期:T", title=""))
        tvl_line = base.mark_line(color="#22d3ee", strokeWidth=2).encode(
            y=alt.Y("TVL:Q", title="TVL ($)", axis=alt.Axis(format="~s"))
        )
        vol_line = base.mark_line(color="#a78bfa", strokeWidth=2, strokeDash=[4,2]).encode(
            y=alt.Y("24h Vol:Q", title="")
        )
        st.altair_chart(
            alt.layer(tvl_line, vol_line).properties(height=300).configure_view(strokeWidth=0).configure(background="#0a0e17").configure_axis(labelColor="#94a3b8", titleColor="#94a3b8", gridColor="#1e293b"),
            use_container_width=True
        )
        st.caption("🔵 TVL · 🟣 24h Volume")
    
    with trend_tab2:
        biz_cols = [c for c in df.columns if c.endswith(" TVL")]
        if biz_cols and "日期" in df.columns:
            df_melt = df[["日期"] + biz_cols].copy()
            df_biz = df_melt.melt(id_vars=["日期"], value_vars=biz_cols, var_name="业务线", value_name="TVL")
            chart = alt.Chart(df_biz).mark_area(opacity=0.7).encode(
                x=alt.X("日期:T", title=""),
                y=alt.Y("TVL:Q", title="TVL ($)", stack=True, axis=alt.Axis(format="~s")),
                color=alt.Color("业务线:N", scale=alt.Scale(scheme="tableau10")),
            ).properties(height=300).configure_view(strokeWidth=0).configure(background="#0a0e17").configure_axis(labelColor="#94a3b8", titleColor="#94a3b8", gridColor="#1e293b")
            st.altair_chart(chart, use_container_width=True)
    
    with trend_tab3:
        fee_chart = alt.Chart(df).mark_bar(color="#10b981", opacity=0.8).encode(
            x=alt.X("日期:T", title=""),
            y=alt.Y("24h Fee:Q", title="24h Fee ($)", axis=alt.Axis(format="~s")),
        ).properties(height=300).configure_view(strokeWidth=0).configure(background="#0a0e17").configure_axis(labelColor="#94a3b8", titleColor="#94a3b8", gridColor="#1e293b")
        st.altair_chart(fee_chart, use_container_width=True)

elif len(hist) == 1:
    st.info("📊 趋势图需要至少 2 天数据，明天就能看到了")
else:
    st.info("📊 暂无历史数据")

# Footer
st.markdown("""
<div style="text-align:center; color:#64748b !important; margin-top:3rem; padding:1rem; border-top:1px solid #1e293b; font-size:0.8rem;">
    Byreal Ops Dashboard · Data refreshed 3x daily at 09:20 / 13:00 / 18:00 UTC+8
</div>
""", unsafe_allow_html=True)
