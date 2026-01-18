import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海決策報", initial_sidebar_state="collapsed")

# --- 2. 您的 GAS API (請確認這是您的正確網址) ---
GAS_URL = "https://script.google.com/macros/library/d/1dOn69U1V5kqsde1kwg0SCdkU1ww694ahWUNhktSKZc08fi_wKiB1-IJI/1"

# --- 3. CSS 優化 (字體加大、手機好讀) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
    
    /* 股票卡片 */
    .compact-card {
        border: 1px solid #ddd; border-radius: 8px;
        padding: 10px 5px; text-align: center;
        background: white; margin-bottom: 5px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .compact-name { font-size: 18px !important; font-weight: 900; color: #333; margin: 0; line-height: 1.2;}
    .compact-price { font-size: 26px !important; font-weight: bold; margin: 0; line-height: 1.2;}
    .compact-change { font-size: 16px !important; font-weight: bold; }
    
    /* PChome 風格榜單 */
    .rank-title {
        font-size: 18px; font-weight: 900; color: #fff;
        background: linear-gradient(90deg, #d32f2f, #ef5350);
        padding: 8px; border-radius: 5px 5px 0 0;
        margin-top: 15px; text-align: center;
    }
    .rank-box {
        border: 1px solid #ef5350; border-top: none;
        border-radius: 0 0 5px 5px; padding: 5px;
        background: #fff; margin-bottom: 15px;
    }
    .rank-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 8px 5px; border-bottom: 1px dashed #eee;
    }
    .rank-name { font-size: 16px; font-weight: bold; color: #333; }
    .rank-price { font-size: 16px; font-weight: bold; }

    /* Yahoo 風格新聞分類標題 */
    .news-category-header {
        background-color: #f1f8ff;
        color: #1f4e78;
        padding: 8px 12px;
        border-left: 6px solid #1f4e78;
        font-size: 20px !important;
        font-weight: 900;
        margin-top: 25px;
        margin-bottom: 10px;
    }
    
    /* 新聞項目 */
    .news-item { padding: 12px 0; border-bottom: 1px solid #eee; }
    .news-link {
        text-decoration: none; color: #222;
        font-size: 20px; font-weight: 600;
        line-height: 1.4; display: block; margin-bottom: 6px;
    }
    .news-link:hover { color: #2E86C1; }
    .news-meta { font-size: 13px; color: #888; }
    .news-tag {
        display: inline-block; background: #eee; color: #555;
        font-size: 12px; padding: 2px 6px; border-radius: 4px; margin-right: 5px;
    }
    
    div[data-testid="column"] { padding: 0 3px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的股海決策報")
st.caption(f"全方位戰情版 | 更新：{datetime.now().strftime('%H:%M')}")

# --- 4. 資料庫設定 ---

# (A) 新聞 RSS 來源 (選用台灣最穩定的財經源，涵蓋 Yahoo 新聞內容)
RSS_SOURCES = [
    "https://news.cnyes.com/rss/cat/200", # 鉅亨台股 (量大)
    "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money", # 聯合財經
    "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml", # MoneyDJ
    "https://finance.yahoo.com/news/rssindex" # Yahoo 美股 (輔助)
]

# (B) 詳細分類關鍵字 (依照您的 Yahoo 分類表建立)
# 這裡定義三大類，程式會自動拿新聞標題去比對這些關鍵字
KEYWORD_MAPPING = {
    "📊 上市類股": {
        "半導體/電子": ["台積電", "聯發科", "聯電", "半導體", "晶圓", "IC", "電子"],
        "電腦/光電": ["電腦", "廣達", "緯創", "光電", "面板", "友達", "群創", "技嘉", "華碩", "宏碁"],
        "航運/運輸": ["長榮", "陽明", "萬海", "航運", "航空", "華航", "長榮航", "散裝"],
        "金融/保險": ["金控", "銀行", "富邦", "國泰", "中信", "玉山", "元大", "金融"],
        "水泥/鋼鐵/傳產": ["水泥", "台泥", "亞泥", "鋼鐵", "中鋼", "紡織", "塑膠", "台塑"],
        "生技/營建": ["生技", "藥", "疫苗", "營建", "房市", "遠雄", "興富發"]
    },
    "💡 概念股": {
        "AI/機器人": ["AI", "人工智慧", "機器人", "伺服器", "輝達", "NVIDIA", "散熱", "奇鋐"],
        "蘋果供應鏈": ["蘋果", "Apple", "iPhone", "iPad", "鴻海", "大立光", "Type-C"],
        "電動車/車電": ["電動車", "特斯拉", "Tesla", "電池", "充電樁", "裕隆", "鴻華", "ADAS"],
        "綠能/重電": ["綠能", "風電", "太陽能", "儲能", "華城", "士電", "中興電"],
        "元宇宙/網通": ["元宇宙", "VR", "宏達電", "網通", "智邦", "WiFi", "5G", "低軌衛星"]
    },
    "🏢 集團股": {
        "台積電集團": ["台積電", "精材", "創意", "世界先進"],
        "鴻海集團": ["鴻海", "鴻準", "群創", "樺漢", "工業富聯"],
        "台塑集團": ["台塑", "南亞", "台化", "台塑化"],
        "長榮集團": ["長榮", "榮運", "長榮航", "長榮鋼"],
        "國泰/富邦集團": ["國泰金", "富邦金", "富邦媒"],
        "聯華/遠東集團": ["聯華", "聯強", "遠東新", "遠傳"]
    }
}

# (C) 熱門榜單 (PChome 風格)
HOT_LISTS = {
    "🔥 熱門討論股": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], 
    "💎 人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], 
    "💡 熱門概念": ["1519.TW", "1513.TW", "2308.TW", "2454.TW", "6669.TW", "2376.TW"] 
}

STOCK_MAP = {
    "00878": "國泰永續高股息", "2301": "光寶科", "2308": "台達電", "2412": "中華電", 
    "2476": "鉅祥", "2884": "玉山金", "2892": "第一金", "3034": "聯詠", 
    "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "5880": "合庫金", "6191": "精成科", "6761": "穩得", "6788": "華景電", 
    "8926": "台汽電", "2330": "台積電", "2317": "鴻海", "2603": "長榮", 
    "2609": "陽明", "2615": "萬海", "2454": "聯發科", "3231": "緯創",
    "0056": "元大高股息", "0050": "元大台灣50", "00919": "群益台灣精選", "00929": "復華科技優息",
    "00940": "元大台灣價值", "1519": "華城", "1513": "中興電", "1503": "士電", "2382": "廣達", "6669": "緯穎",
    "2376": "技嘉"
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
    valid = [t for t in ticker_list if t.strip()]
    if not valid: return pd.DataFrame()
    data = []
    try:
        stocks = yf.Tickers(" ".join(valid))
        for t in valid:
            try:
                info = stocks.tickers[t].history(period="5d")
                if len(info) > 0:
                    price = info['Close'].iloc[-1]
                    prev = info['Close'].iloc[-2] if len(info) > 1 else price
                    pct = ((price - prev) / prev) * 100
                    color = "#e53935" if pct >= 0 else "#43a047"
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
    # 建立分類桶
    buckets = {
        "📊 上市類股": [], 
        "💡 概念股": [], 
        "🏢 集團股": [],
        "🌍 其他快訊": []
    }
    
    seen_titles = set()
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]: # 增加抓取量
                title = entry.title
                if title[:10] in seen_titles: continue
                seen_titles.add(title[:10])
                
                # 簡單翻譯英文標題
                if "yahoo" in url and sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < len(title)*0.3:
                     try: title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                     except: pass
                
                item = {
                    "title": title, "link": entry.link, 
                    "date": entry.get('published', '')[:16], 
                    "src": feed.feed.get('title', '快訊')
                }
                
                # 進行多重分類 (一則新聞可能屬於多個分類)
                matched = False
                
                # 1. 檢查上市類股
                for sub, kws in KEYWORD_MAPPING["📊 上市類股"].items():
                    if any(kw in title for kw in kws):
                        item_copy = item.copy()
                        item_copy["tag"] = sub
                        buckets["📊 上市類股"].append(item_copy)
                        matched = True
                        break # 同一大類只歸一次
                
                # 2. 檢查概念股
                for sub, kws in KEYWORD_MAPPING["💡 概念股"].items():
                    if any(kw in title for kw in kws):
                        item_copy = item.copy()
                        item_copy["tag"] = sub
                        buckets["💡 概念股"].append(item_copy)
                        matched = True
                        break
                
                # 3. 檢查集團股
                for sub, kws in KEYWORD_MAPPING["🏢 集團股"].items():
                    if any(kw in title for kw in kws):
                        item_copy = item.copy()
                        item_copy["tag"] = sub
                        buckets["🏢 集團股"].append(item_copy)
                        matched = True
                        break
                
                if not matched:
                    buckets["🌍 其他快訊"].append(item)
                    
        except: continue
    return buckets

# --- 6. 介面佈局 ---

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 股票管理")
    with st.expander("➕ 新增到【庫存股】"):
        inv_code = st.text_input("代碼", key="add_inv", placeholder="如 2330.TW")
        if st.button("加入庫存"):
            update_cloud("add", inv_code.upper(), "inventory")
            st.cache_data.clear(); st.rerun()
    with st.expander("➕ 新增到【觀察名單】"):
        watch_code = st.text_input("代碼", key="add_watch", placeholder="如 2603.TW")
        if st.button("加入觀察"):
            update_cloud("add", watch_code.upper(), "watchlist")
            st.cache_data.clear(); st.rerun()
    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# === 第一層：💰 媽媽的庫存 (最優先) ===
c1, c2 = st.columns([3, 1])
with c1: st.subheader("💰 媽媽的庫存")
with c2: 
    if st.button("更新"): st.cache_data.clear(); st.rerun()

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

# === 第二層：👀 有興趣的股票 ===
st.subheader("👀 有興趣的股票")
watch_list = get_list_from_cloud("watchlist")
if watch_list:
    df_w = get_stock_data(watch_list)
    cols2 = st.columns(3)
    for i, row in df_w.iterrows():
        with cols2[i%3]:
            st.markdown(f"""<div class="compact-card"><div style="font-size:16px;">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"dw_{row['code']}"): update_cloud("remove", row['full_code'], "watchlist"); st.rerun()
else:
    st.info("目前沒有觀察名單，請從左側新增。")

# === 第三層：🏆 市場熱門戰情室 (PChome 風格) ===
st.markdown("---")
st.subheader("🏆 市場熱門戰情室")

hot_cols = st.columns(3)
idx = 0
for title, tickers in HOT_LISTS.items():
    with hot_cols[idx]:
        st.markdown(f'<div class="rank-title">{title}</div>', unsafe_allow_html=True)
        df_hot = get_stock_data(tickers)
        html = '<div class="rank-box">'
        for _, row in df_hot.iterrows():
            html += f"""
            <div class="rank-row">
                <span class="rank-name">{row['name']}</span>
                <span class="rank-price" style="color:{row['color']}">{row['sign']} {row['price']}</span>
            </div>"""
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    idx += 1

# === 第四層：📰 產業新聞瀑布流 (Yahoo 分類) ===
st.markdown("---")
st.subheader("🗞️ 產業新聞快遞 (Yahoo 分類)")

# 快速連結 Launcher
st.markdown("""
<div style="overflow-x:auto; white-space:nowrap; padding-bottom:10px;">
<a href="https://tw.stock.yahoo.com/class" target="_blank" style="padding:5px 10px; background:#eee; border-radius:15px; text-decoration:none; margin-right:5px; font-size:14px;">Yahoo類股 ↗</a>
<a href="https://tw.stock.yahoo.com/news/" target="_blank" style="padding:5px 10px; background:#eee; border-radius:15px; text-decoration:none; margin-right:5px; font-size:14px;">Yahoo新聞 ↗</a>
</div>
""", unsafe_allow_html=True)

with st.spinner("正在為媽媽整理新聞..."):
    news_buckets = fetch_news_waterfall()

# 依序顯示三大類
cats_order = ["📊 上市類股", "💡 概念股", "🏢 集團股", "🌍 其他快訊"]

for cat in cats_order:
    items = news_buckets.get(cat, [])
    if items:
        st.markdown(f'<div class="news-category-header">{cat}</div>', unsafe_allow_html=True)
        # 只顯示前 8 則避免過長
        for n in items[:8]:
            tag_html = f'<span class="news-tag">{n["tag"]}</span>' if "tag" in n else ""
            st.markdown(f"""
            <div class="news-item">
                <a href="{n['link']}" target="_blank" class="news-link">
                    {n['title']}
                </a>
                <div class="news-meta">
                    {tag_html} {n['src']} • {n['date']}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
