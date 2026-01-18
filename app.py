import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海決策報", initial_sidebar_state="collapsed")

# --- 2. 您的 GAS API ---
GAS_URL = "https://script.google.com/macros/library/d/1dOn69U1V5kqsde1kwg0SCdkU1ww694ahWUNhktSKZc08fi_wKiB1-IJI/1"

# --- 3. CSS 優化 (PChome 風格榜單) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
    
    /* PChome 風格榜單標題 */
    .rank-title {
        font-size: 20px; font-weight: 900; color: #fff;
        background: linear-gradient(90deg, #d32f2f, #e57373);
        padding: 8px 15px; border-radius: 5px 5px 0 0;
        margin-top: 10px; text-align: center;
    }
    .rank-box {
        border: 2px solid #e57373; border-top: none;
        border-radius: 0 0 5px 5px; padding: 10px;
        background: #fff; margin-bottom: 20px;
    }
    
    /* 緊湊型股票行 (榜單專用) */
    .rank-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 0; border-bottom: 1px dashed #eee;
    }
    .rank-name { font-size: 18px; font-weight: bold; color: #333; }
    .rank-price { font-size: 20px; font-weight: bold; }
    
    /* 一般股票小卡片 */
    .compact-card {
        border: 1px solid #eee; border-radius: 10px;
        padding: 12px 5px; text-align: center;
        background: white; margin-bottom: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .compact-name { font-size: 20px !important; font-weight: 900; color: #333; margin: 0; line-height: 1.2;}
    .compact-price { font-size: 26px !important; font-weight: bold; margin: 0; line-height: 1.2;}
    
    /* 新聞區塊 */
    .news-section-title {
        background-color: #f8f9fa; color: #2c3e50;
        padding: 12px 15px; border-left: 8px solid #E74C3C;
        font-size: 24px !important; font-weight: 900;
        margin-top: 30px; margin-bottom: 15px;
    }
    .news-link {
        text-decoration: none; color: #2E86C1;
        font-size: 22px; font-weight: 700;
        display: block; margin-bottom: 8px;
    }
    
    div[data-testid="column"] { padding: 0 5px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的股海決策報")
st.caption(f"旗艦熱門榜單版 | 更新：{datetime.now().strftime('%H:%M')}")

# --- 4. 資料來源設定 ---
# (A) 定義熱門榜單 (模仿 PChome 的選股邏輯)
HOT_LISTS = {
    "🔥 熱門討論股": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], # 台積,鴻海,緯創,廣達,長榮,陽明
    "💎 台股人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], # 高股息與市值型
    "💡 熱門概念股": ["1519.TW", "1513.TW", "1503.TW", "2308.TW", "2454.TW", "6669.TW"] # 重電(華城,士電) & AI(台達電,聯發科,緯穎)
}

RSS_SOURCES = [
    "https://finance.yahoo.com/news/rssindex",
    "https://news.cnyes.com/rss/cat/200",
    "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
    "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml"
]

CATEGORY_KEYWORDS = {
    "🔥 熱門電子": ["台積電", "聯電", "鴻海", "廣達", "緯創", "AI", "半導體", "輝達", "伺服器", "散熱"],
    "🚢 航運/傳產": ["長榮", "陽明", "萬海", "航運", "航空", "台泥", "中鋼", "台塑", "紡織"],
    "💰 金融/總經": ["金控", "銀行", "富邦", "國泰", "中信", "升息", "美元", "外資"],
    "💡 概念/集團": ["蘋果", "iPhone", "電動車", "特斯拉", "重電", "綠能", "國巨", "元宇宙", "華城"],
    "🏠 生活/營建": ["營建", "房市", "觀光", "王品", "統一", "生技"]
}

STOCK_MAP = {
    "00878": "國泰永續高股息", "2301": "光寶科", "2308": "台達電", "2412": "中華電", 
    "2476": "鉅祥", "2884": "玉山金", "2892": "第一金", "3034": "聯詠", 
    "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "5880": "合庫金", "6191": "精成科", "6761": "穩得", "6788": "華景電", 
    "8926": "台汽電", "2330": "台積電", "2317": "鴻海", "2603": "長榮", 
    "2609": "陽明", "2615": "萬海", "2454": "聯發科", "3231": "緯創",
    "0056": "元大高股息", "0050": "元大台灣50", "00919": "群益台灣精選", "00929": "復華科技優息",
    "00940": "元大台灣價值", "1519": "華城", "1513": "中興電", "1503": "士電", "2382": "廣達", "6669": "緯穎"
}

# --- 5. 核心函數 ---

def get_list_from_cloud(list_type):
    try:
        response = requests.get(GAS_URL, params={"action": "read", "type": list_type}, timeout=5)
        return response.json() or []
    except: return []

def update_cloud(action, code, list_type, price="0"):
    try: requests.get(GAS_URL, params={"action": action, "code": code, "type": list_type, "price": price}, timeout=2)
    except: pass

def get_name(ticker):
    code = ticker.split(".")[0]
    return STOCK_MAP.get(code, code)

def get_stock_data(ticker_list):
    if not ticker_list: return pd.DataFrame()
    valid_tickers = [t for t in ticker_list if t.strip()]
    if not valid_tickers: return pd.DataFrame()
    data = []
    try:
        stocks = yf.Tickers(" ".join(valid_tickers))
        for t in valid_tickers:
            try:
                info = stocks.tickers[t].history(period="5d")
                if len(info) > 0:
                    price = info['Close'].iloc[-1]
                    prev = info['Close'].iloc[-2] if len(info) > 1 else price
                    pct = ((price - prev) / prev) * 100
                    color = "#e53935" if pct >= 0 else "#43a047" # 紅漲綠跌
                    sign = "▲" if pct >= 0 else "▼"
                    
                    data.append({
                        "name": get_name(t), "code": t.replace(".TW", "").replace(".TWO", ""),
                        "full_code": t, "price": f"{price:.2f}",
                        "pct": f"{pct:.2f}%", "color": color, "sign": sign
                    })
            except: continue
    except: pass
    return pd.DataFrame(data)

@st.cache_data(ttl=1800)
def fetch_news_waterfall():
    buckets = {key: [] for key in CATEGORY_KEYWORDS.keys()}
    buckets["🌍 其他焦點"] = []
    seen = set()
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = entry.title
                if title[:10] in seen: continue
                seen.add(title[:10])
                if "yahoo" in url and sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < len(title)*0.3:
                    try: title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                    except: pass
                item = {"title": title, "link": entry.link, "date": entry.get('published', '')[:16], "src": feed.feed.get('title', '快訊')}
                matched = False
                for cat, kws in CATEGORY_KEYWORDS.items():
                    if any(kw in title for kw in kws):
                        buckets[cat].append(item)
                        matched = True; break
                if not matched: buckets["🌍 其他焦點"].append(item)
        except: continue
    return buckets

# --- 6. 介面佈局 ---

with st.sidebar:
    st.header("⚙️ 股票管理")
    with st.expander("➕ 新增到【庫存股】"):
        inv_code = st.text_input("代碼 (庫存)", key="inv", placeholder="如 2330.TW")
        if st.button("加入庫存"):
            update_cloud("add", inv_code.upper(), "inventory")
            st.cache_data.clear(); st.rerun()
    with st.expander("➕ 新增到【觀察名單】"):
        watch_code = st.text_input("代碼 (觀察)", key="watch", placeholder="如 2603.TW")
        if st.button("加入觀察"):
            update_cloud("add", watch_code.upper(), "watchlist")
            st.cache_data.clear(); st.rerun()
    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# === A. 庫存與觀察 (媽媽的私房區) ===
c1, c2 = st.columns([3, 1])
with c1: st.subheader("💰 媽媽的股票")
with c2: 
    if st.button("更新數據"): st.cache_data.clear(); st.rerun()

# 庫存
inv_list = get_list_from_cloud("inventory")
if inv_list:
    df = get_stock_data(inv_list)
    cols = st.columns(3)
    for i, row in df.iterrows():
        with cols[i%3]:
            st.markdown(f"""
            <div class="compact-card" style="border-left: 5px solid {row['color']};">
                <div style="font-size:16px;">{row['name']}</div>
                <div class="compact-price" style="color:{row['color']}">{row['price']}</div>
                <div style="font-weight:bold; color:{row['color']}">{row['sign']} {row['pct']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"d_{row['code']}"): update_cloud("remove", row['full_code'], "inventory"); st.rerun()

# 觀察
st.caption("👀 有興趣的觀察股")
watch_list = get_list_from_cloud("watchlist")
if watch_list:
    df_w = get_stock_data(watch_list)
    cols2 = st.columns(3)
    for i, row in df_w.iterrows():
        with cols2[i%3]:
            st.markdown(f"""<div class="compact-card"><div style="font-size:16px;">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"dw_{row['code']}"): update_cloud("remove", row['full_code'], "watchlist"); st.rerun()

# === B. 🏆 市場熱門戰情室 (PChome 風格) ===
st.markdown("---")
st.subheader("🏆 市場熱門排行 (PChome 同步)")

col_hot1, col_hot2, col_hot3 = st.columns(3)

def render_hot_list(title, tickers):
    st.markdown(f'<div class="rank-title">{title}</div>', unsafe_allow_html=True)
    df = get_stock_data(tickers)
    html_content = '<div class="rank-box">'
    for _, row in df.iterrows():
        html_content += f"""
        <div class="rank-row">
            <span class="rank-name">{row['name']} <span style="font-size:12px;color:#999">{row['code']}</span></span>
            <span class="rank-price" style="color:{row['color']}">{row['sign']} {row['price']}</span>
        </div>
        """
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

with col_hot1: render_hot_list("🔥 熱門討論股", HOT_LISTS["🔥 熱門討論股"])
with col_hot2: render_hot_list("💎 台股人氣 ETF", HOT_LISTS["💎 台股人氣 ETF"])
with col_hot3: render_hot_list("💡 熱門概念股", HOT_LISTS["💡 熱門概念股"])

# === C. 新聞瀑布流 ===
st.markdown("---")
with st.spinner("整理頭條中..."):
    news_data = fetch_news_waterfall()

cats = ["🔥 熱門電子", "🚢 航運/傳產", "💰 金融/總經", "💡 概念/集團", "🏠 生活/營建", "🌍 其他焦點"]
for cat in cats:
    items = news_data.get(cat, [])
    if items:
        st.markdown(f'<div class="news-section-title">{cat}</div>', unsafe_allow_html=True)
        for n in items[:5]:
            st.markdown(f"""<div style="padding:10px 0; border-bottom:1px solid #eee;"><a href="{n['link']}" target="_blank" class="news-link">{n['title']}</a><div style="color:#888;font-size:14px;">{n['src']} • {n['date']}</div></div>""", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
