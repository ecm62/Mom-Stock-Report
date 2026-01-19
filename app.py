import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海顧問", initial_sidebar_state="collapsed")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

TW_TZ = timezone(timedelta(hours=8))
def get_tw_time():
    return datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')

# --- 2. GAS API ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwTsM79MMdedizvIcIn7tgwT81VIhj87WM-bvR45QgmMIUsIemmyR_FzMvG3v5LEHEvPw/exec"

# --- 3. CSS 專業級優化 ---
st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Microsoft JhengHei", "Segoe UI", sans-serif; }

/* 訪客計數器 (右下角淡灰色) */
.visitor-counter {
    position: fixed;
    bottom: 10px;
    right: 15px;
    font-size: 12px;
    color: #bdbdbd; /* 淡灰色 */
    background-color: rgba(255, 255, 255, 0.8);
    padding: 2px 8px;
    border-radius: 10px;
    z-index: 9999;
    font-family: monospace;
}

/* 分頁籤優化 */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
.stTabs [data-baseweb="tab"] {
    height: 45px; border-radius: 8px; background-color: #f8f9fa; color: #555;
    font-weight: 700; font-size: 15px; padding: 0 20px; border: 1px solid #eee;
}
.stTabs [aria-selected="true"] {
    background-color: #1565c0 !important; color: white !important; border: none;
}

/* 財務指標卡片 */
.metric-card {
    background-color: #f1f8e9;
    border-left: 5px solid #66bb6a;
    padding: 10px;
    border-radius: 4px;
    margin-bottom: 10px;
    text-align: center;
}
.metric-label { font-size: 14px; color: #558b2f; font-weight: bold; }
.metric-value { font-size: 20px; color: #33691e; font-weight: 900; }

/* 股票卡片 */
.compact-card { 
    border: 1px solid #eeeeee; border-radius: 6px; padding: 4px 1px; text-align: center; 
    background: white; margin-bottom: 0px; box-shadow: 0 1px 1px rgba(0,0,0,0.03);
    min-height: 70px; transition: all 0.2s;
}
.compact-card:hover { transform: translateY(-1px); box-shadow: 0 3px 6px rgba(0,0,0,0.08); border-color: #b0bec5; }
.compact-name { font-size: 13px !important; font-weight: 700; color: #455a64; margin: 0; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.compact-price { font-size: 17px !important; font-weight: 800; margin: 1px 0 0 0; letter-spacing: -0.5px; font-family: "Segoe UI", sans-serif;}

/* 隱形刪除鈕 */
div[data-testid="column"] .stButton > button {
    width: 100%; border: none !important; background: transparent !important;
    color: #eeeeee !important; font-size: 10px !important; padding: 0 !important;
    height: 12px !important; margin-top: -4px !important; 
}
div[data-testid="column"] .stButton > button:hover { color: #ef5350 !important; font-weight: bold; background: rgba(255, 200, 200, 0.2) !important; }

/* 連結樣式 */
a.hot-link { text-decoration: none; color: inherit; display: block; margin-bottom: 4px;}
.hot-card { border: 1px solid #ffccbc; border-radius: 6px; padding: 6px 2px; text-align: center; background: #fffbfb; min-height: 75px; }
.opinion-card { border: 1px solid #d1c4e9; border-radius: 6px; padding: 8px 2px; text-align: center; background: #fdfbff; min-height: 75px; }
.tech-card { border: 1px solid #bbdefb; border-radius: 6px; padding: 8px 2px; text-align: center; background: #f0f7ff; min-height: 75px; }

/* 區塊標題 */
.section-header { font-size: 16px; font-weight: 900; color: #37474f; padding: 5px 0; border-bottom: 2px solid #eceff1; margin: 15px 0 10px 0; }
.news-category-header { background: #f1f8e9; color: #2e7d32; padding: 6px 10px; border-left: 4px solid #2e7d32; font-size: 16px !important; font-weight: 900; margin-top: 15px; margin-bottom: 5px; border-radius: 4px; }
.news-item-compact { padding: 8px 0; border-bottom: 1px dashed #e0e0e0; line-height: 1.3; }
.news-link-text { text-decoration: none; color: #263238; font-size: 16px !important; font-weight: 600; display: block; }

.stButton > button { width: 100%; border-radius: 6px; font-weight: bold; font-size: 15px;}
div[data-testid="column"] { min-width: 85px !important; flex: 1 1 auto !important; padding: 0 1px !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. 訪客計數器邏輯 ---
if 'visit_count' not in st.session_state:
    try:
        # 呼叫 GAS 增加計數
        r = requests.get(GAS_URL, params={"action": "visit"}, timeout=3)
        data = r.json()
        st.session_state['visit_count'] = data.get('count', 'N/A')
    except:
        st.session_state['visit_count'] = "..."

# 顯示計數器 (HTML)
st.markdown(f"""
<div class="visitor-counter">
    累積訪客: {st.session_state['visit_count']} 人
</div>
""", unsafe_allow_html=True)

# --- 5. 側邊欄與使用者設定 ---
query_params = st.query_params
default_user = query_params.get("user", "阿美")

with st.sidebar:
    st.header("👤 使用者設定")
    current_user = st.text_input("您的名字", value=default_user)
    if current_user != default_user:
        st.query_params["user"] = current_user
        st.rerun()
    st.markdown(f"目前顯示：**{current_user}** 的資料")
    st.divider()

    st.header("⚙️ 股票管理")
    with st.expander("➕ 新增到【庫存股】"):
        inv_code = st.text_input("代碼", key="add_inv", placeholder="如 2330.TW")
        if st.button("加入庫存"):
            try: requests.get(GAS_URL, params={"action": "add", "code": inv_code.upper(), "type": "inventory", "user": current_user}, timeout=2)
            except: pass
            st.cache_data.clear(); st.rerun()
    with st.expander("➕ 新增到【觀察名單】"):
        watch_code = st.text_input("代碼", key="add_watch", placeholder="如 2603.TW")
        if st.button("加入觀察"):
            try: requests.get(GAS_URL, params={"action": "add", "code": watch_code.upper(), "type": "watchlist", "user": current_user}, timeout=2)
            except: pass
            st.cache_data.clear(); st.rerun()
    with st.expander("📰 新增【新聞頻道】"):
        MEDIA_PRESETS = {"雅虎": "https://finance.yahoo.com/news/rssindex", "鉅亨": "https://news.cnyes.com/rss/cat/headline"}
        new_rss = st.text_input("輸入「鉅亨」或網址", key="rss_in")
        if st.button("加入頻道"):
            try: requests.get(GAS_URL, params={"action": "add", "code": new_rss, "type": "news", "user": current_user}, timeout=2)
            except: pass
            st.cache_data.clear(); st.rerun()
    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# 標題
c_title, c_btn = st.columns([3, 1])
with c_title:
    st.title(f"👵 {current_user} 的股海顧問") 
    st.caption(f"台灣時間：{get_tw_time()} | 自動更新中...")
with c_btn:
    st.write("") 
    if st.button("🔴 更新股價", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. 資料處理函數 ---
STOCK_MAP = {"0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息", "00919": "群益台灣精選", "00929": "復華科技優息", "00940": "元大台灣價值", "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2303": "聯電", "2308": "台達電", "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2002": "中鋼", "2603": "長榮", "2609": "陽明", "2615": "萬海", "1519": "華城", "1513": "中興電", "3231": "緯創", "2382": "廣達", "6669": "緯穎", "2376": "技嘉", "3035": "智原"}

def get_name(ticker):
    code = ticker.replace(".TW", "").replace(".TWO", "").split(".")[0]
    return STOCK_MAP.get(code, code)

def get_list_from_cloud(list_type, user):
    try:
        response = requests.get(GAS_URL, params={"action": "read", "type": list_type, "user": user}, timeout=5)
        data = response.json()
        if isinstance(data, list): return data
        return []
    except: return []

def update_cloud_remove(code, list_type, user):
    try: requests.get(GAS_URL, params={"action": "remove", "code": code, "type": list_type, "user": user}, timeout=2)
    except: pass

def get_stock_data(ticker_list):
    if not ticker_list: return pd.DataFrame()
    valid = [str(t).strip() for t in ticker_list if t and str(t).strip() != ""]
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
                    display_name = get_name(t)
                    if display_name == t.replace(".TW", "").replace(".TWO", ""):
                         try: 
                             short = stocks.tickers[t].info.get('shortName', t)
                             display_name = " ".join(short.split(" ")[:2]) if len(short) > 10 else short
                         except: pass
                    data.append({"name": display_name, "code": t.replace(".TW", "").replace(".TWO", ""), "full_code": t, "price": f"{price:.2f}", "pct": f"{pct:.2f}%", "color": color, "sign": sign})
            except: continue
    except: pass
    return pd.DataFrame(data)

def get_financial_metrics(ticker):
    """抓取各股財務指標"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # 處理資料，若無資料顯示 --
        def safe_get(key, fmt="{:.2f}"):
            val = info.get(key)
            return fmt.format(val) if val is not None else "--"
        
        return {
            "EPS": safe_get('trailingEps'),
            "ROE": safe_get('returnOnEquity', "{:.2%}"),
            "ROA": safe_get('returnOnAssets', "{:.2%}"),
            "PER (本益比)": safe_get('trailingPE'),
            "PBR (淨值比)": safe_get('priceToBook'),
            "殖利率": safe_get('dividendYield', "{:.2%}")
        }
    except:
        return None

@st.cache_data(ttl=300) 
def fetch_and_filter_news(user_rss_urls):
    KEYWORD_MAPPING = { "🤖 AI 與半導體": ["台積電", "聯電", "AI"], "🏗️ 鋼鐵與水泥": ["中鋼", "水泥"], "🚢 航運與運輸": ["長榮", "陽明"], "💰 金融與銀行": ["金控", "銀行"], "💊 生技與防疫": ["生技", "藥"], "🏠 營建與房產": ["房地產", "營建"]}
    buckets = {key: [] for key in KEYWORD_MAPPING.keys()}
    buckets["🌍 其他頭條"] = []
    seen = set()
    default_rss = ["https://news.cnyes.com/rss/cat/headline", "https://finance.yahoo.com/news/rssindex"]
    if user_rss_urls: default_rss.extend(user_rss_urls)
    final_rss = list(set(default_rss))
    for url in final_rss:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:60]: 
                title = entry.title
                if title[:10] in seen: continue
                seen.add(title[:10])
                if "yahoo" in url and sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < len(title)*0.3:
                     try: title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                     except: pass
                item = {"title": title, "link": entry.link, "date": entry.get('published', '')[:16], "src": feed.feed.get('title', '快訊')}
                matched = False
                for category, keywords in KEYWORD_MAPPING.items():
                    if any(kw in title for kw in keywords):
                        buckets[category].append(item); matched = True; break 
                if not matched: buckets["🌍 其他頭條"].append(item)
        except: continue
    return buckets

# --- 戰情室分頁 ---
tab1, tab2, tab5, tab3, tab4 = st.tabs(["📊 我的投資", "🔥 市場熱點", "🔍 個股健檢", "🏆 熱門排行", "📰 產業新聞"])

# === Tab 1: 我的投資 ===
with tab1:
    st.markdown('<div class="section-header">💰 庫存損益</div>', unsafe_allow_html=True)
    inv_list = get_list_from_cloud("inventory", current_user)
    df_inv = pd.DataFrame() 
    if inv_list: df_inv = get_stock_data(inv_list)
    if not df_inv.empty:
        cols = st.columns(8) 
        for i, row in df_inv.iterrows():
            with cols[i%8]:
                st.markdown(f"""<div class="compact-card" style="border-left: 4px solid {row['color']};"><div class="compact-name" title="{row['name']}">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div><div style="font-size:12px; font-weight:bold; color:{row['color']}">{row['sign']} {row['pct']}</div></div>""", unsafe_allow_html=True)
                if st.button("✕", key=f"d_{row['code']}"): 
                    update_cloud_remove(row['full_code'], "inventory", current_user)
                    st.cache_data.clear(); st.rerun()
    else: st.info("庫存空白。")

    st.markdown('<div class="section-header">👀 觀察名單</div>', unsafe_allow_html=True)
    watch_list = get_list_from_cloud("watchlist", current_user)
    df_watch = pd.DataFrame() 
    if watch_list: df_watch = get_stock_data(watch_list)
    if not df_watch.empty:
        cols2 = st.columns(8)
        for i, row in df_watch.iterrows():
            with cols2[i%8]:
                st.markdown(f"""<div class="compact-card"><div class="compact-name">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
                if st.button("✕", key=f"dw_{row['code']}"): 
                    update_cloud_remove(row['full_code'], "watchlist", current_user)
                    st.cache_data.clear(); st.rerun()
    else: st.info("無觀察名單。")

# === Tab 2: 市場熱點 ===
with tab2:
    st.markdown("""<div class="section-header">🔥 Google 熱搜潛力股</div>""", unsafe_allow_html=True)
    HOT_SEARCH_TICKERS = ["2330.TW", "2317.TW", "3231.TW", "2603.TW", "1519.TW", "00940.TW"]
    df_hot_search = get_stock_data(HOT_SEARCH_TICKERS)
    if not df_hot_search.empty:
        hot_cols = st.columns(6)
        for i, row in df_hot_search.iterrows():
            with hot_cols[i%6]:
                url = f"https://www.google.com/search?q={row['name']} 股票 討論 ptt"
                st.markdown(f"""<a href="{url}" target="_blank" class="hot-link"><div class="hot-card"><div class="compact-name" style="color:#d84315;">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div></a>""", unsafe_allow_html=True)

# === Tab 5: 個股健檢 (新功能) ===
with tab5:
    st.markdown('<div class="section-header">🔍 財務與籌碼概況</div>', unsafe_allow_html=True)
    st.caption("請選擇庫存或觀察名單中的股票，查看詳細財務數據。")
    
    # 合併清單供選擇
    all_stocks = []
    if not df_inv.empty: all_stocks.extend(df_inv['full_code'].tolist())
    if not df_watch.empty: all_stocks.extend(df_watch['full_code'].tolist())
    all_stocks = list(set(all_stocks))
    
    if all_stocks:
        selected_stock = st.selectbox("選擇股票:", all_stocks, format_func=lambda x: f"{get_name(x)} ({x.split('.')[0]})")
        if selected_stock:
            with st.spinner("正在分析財務數據..."):
                metrics = get_financial_metrics(selected_stock)
            
            if metrics:
                m_cols = st.columns(3)
                # 分組顯示
                keys = list(metrics.keys())
                for i, key in enumerate(keys):
                    with m_cols[i % 3]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">{key}</div>
                            <div class="metric-value">{metrics[key]}</div>
                        </div>
                        """, unsafe_allow_html=True)
                st.info("註：三大法人買賣超數據因資料源限制，暫無法提供即時更新，建議參考籌碼K線或證交所網站。")
            else:
                st.error("無法取得該股票的財務數據。")
    else:
        st.warning("請先加入股票到庫存或觀察名單。")

# === Tab 3 & 4 (保持原樣) ===
with tab3:
    st.write("熱門排行 (略)") # 為了精簡代碼，此處略過重複內容，您原有的可保留
with tab4:
    user_rss = get_list_from_cloud("news", current_user)
    with st.spinner("載入新聞..."):
        news_buckets = fetch_and_filter_news(user_rss)
    for cat, items in news_buckets.items():
        if items:
            st.markdown(f'<div class="news-category-header">{cat}</div>', unsafe_allow_html=True)
            for n in items:
                st.markdown(f'<div class="news-item-compact"><a href="{n["link"]}" target="_blank" class="news-link-text">{n["title"]}</a></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
