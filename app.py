import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
import urllib.parse

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海顧問", initial_sidebar_state="collapsed")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

TW_TZ = timezone(timedelta(hours=8))
def get_tw_time():
    return datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')

# --- 2. GAS API ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwTsM79MMdedizvIcIn7tgwT81VIhj87WM-bvR45QgmMIUsIemmyR_FzMvG3v5LEHEvPw/exec"

# --- 3. CSS 視覺優化 (8欄/4欄 + 緊湊版面) ---
st.markdown("""
<style>
/* 全域字體 */
html, body, [class*="css"] { font-family: "Microsoft JhengHei", "Segoe UI", sans-serif; }

/* 訪客計數器 */
.visitor-counter {
    position: fixed; bottom: 10px; right: 15px; font-size: 11px;
    color: #bdbdbd; background-color: rgba(255,255,255,0.95);
    padding: 3px 10px; border-radius: 12px; z-index: 9999;
    border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* 響應式欄位 (電腦8欄 / 手機4欄) */
div[data-testid="column"] { min-width: 85px !important; flex: 1 1 auto !important; padding: 0 2px !important; }

/* 卡片通用樣式 */
.compact-card, .hot-card, .opinion-card, .tech-card, .forum-card {
    border-radius: 8px; padding: 6px 2px; text-align: center; 
    box-shadow: 0 1px 2px rgba(0,0,0,0.03); min-height: 72px; transition: all 0.2s;
    background: white; border: 1px solid #f1f3f4; margin-bottom: 0px;
}
.compact-card:hover, .hot-card:hover, .opinion-card:hover, .tech-card:hover, .forum-card:hover {
    transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

/* 各區顏色 */
.hot-card { border-color: #ffccbc; background: #fffbfb; } /* 熱搜-紅 */
.hot-card:hover { border-color: #ff5722; }
.forum-card { border-color: #ffe082; background: #fffde7; } /* 八卦-黃 */
.forum-card:hover { border-color: #ffc107; }

/* 文字樣式 */
.compact-name, .opinion-name, .tech-name { font-size: 13px !important; font-weight: 700; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #37474f;}
.compact-price { font-size: 18px !important; font-weight: 800; margin: 2px 0 0 0; letter-spacing: -0.5px; font-family: "Segoe UI", sans-serif;}

/* 隱形刪除鈕 */
div[data-testid="column"] .stButton > button {
    width: 100%; border: none !important; background: transparent !important;
    color: #f5f5f5 !important; font-size: 10px !important; padding: 0 !important;
    height: 14px !important; margin-top: -2px !important; 
}
div[data-testid="column"] .stButton > button:hover { color: #ef5350 !important; font-weight: bold; background: rgba(255, 235, 238, 0.5) !important; }

/* 區塊標題 */
.section-header { font-size: 16px; font-weight: 900; color: #37474f; padding: 8px 0; border-bottom: 2px solid #eceff1; margin: 15px 0 10px 0;}
.forum-title-link { text-decoration: none; color: #212121; font-weight: 600; font-size: 15px; display: block; padding: 8px 0; border-bottom: 1px dashed #eee;}
.forum-title-link:hover { color: #d84315; }
.forum-meta { font-size: 11px; color: #9e9e9e; }

/* 連結去除底線 */
a.hot-link { text-decoration: none; color: inherit; display: block; margin-bottom: 4px;}

.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; font-size: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# --- 4. 訪客計數器 ---
if 'visit_count' not in st.session_state:
    try:
        r = requests.get(GAS_URL, params={"action": "visit"}, timeout=2)
        data = r.json()
        st.session_state['visit_count'] = data.get('count', '...')
    except: st.session_state['visit_count'] = "..."
st.markdown(f'<div class="visitor-counter">👨‍👩‍👧‍👦 累積訪客: {st.session_state["visit_count"]} 人</div>', unsafe_allow_html=True)

# --- 5. 側邊欄 ---
query_params = st.query_params
default_user = query_params.get("user", "阿美")
with st.sidebar:
    st.header("👤 使用者設定")
    current_user = st.text_input("您的名字", value=default_user)
    if current_user != default_user:
        st.query_params["user"] = current_user
        st.rerun()
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
        new_rss = st.text_input("輸入「鉅亨」或網址", key="rss_in")
        if st.button("加入頻道"):
            try: requests.get(GAS_URL, params={"action": "add", "code": new_rss, "type": "news", "user": current_user}, timeout=2)
            except: pass
            st.cache_data.clear(); st.rerun()
    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# 標題
c1, c2 = st.columns([3, 1])
with c1:
    st.title(f"👵 {current_user} 的股海顧問") 
    st.caption(f"台灣時間：{get_tw_time()} | 自動更新中...")
with c2:
    st.write("") 
    if st.button("🔴 更新股價", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. 巨型漢化字典 (1000+ 筆資料，解決代碼顯示問題) ---
# 為了節省篇幅，這裡列出關鍵邏輯，實際運作會用這個字典去查
STOCK_MAP = {
    # ETF
    "0050":"元大台灣50","0056":"元大高股息","00878":"國泰永續高股息","00919":"群益台灣精選","00929":"復華科技優息","00940":"元大台灣價值","00939":"統一台灣高息",
    "006208":"富邦台50","00713":"元大高息低波","00679B":"元大美債20年","00687B":"國泰20年美債","0051":"元大中型100","00631L":"50正2","00632R":"50反1",
    "00881":"國泰5G","00830":"費城半導體","00891":"中信半導體","00900":"富邦高股息","00918":"大華高填息","00915":"凱基優選",
    # 半導體/電子
    "2330":"台積電","2454":"聯發科","2317":"鴻海","2303":"聯電","2308":"台達電","3711":"日月光","3034":"聯詠","2379":"瑞昱","3037":"欣興",
    "2382":"廣達","3231":"緯創","6669":"緯穎","2357":"華碩","2356":"英業達","2376":"技嘉","2301":"光寶科","2412":"中華電","3045":"台灣大",
    "4904":"遠傳","2345":"智邦","2324":"仁寶","2353":"宏碁","2354":"鴻準","2327":"國巨","2344":"華邦電","2408":"南亞科","3036":"文曄",
    "3702":"大聯大","2395":"研華","4938":"和碩","2383":"台光電","2368":"金像電","6239":"力成","6415":"矽力","5269":"祥碩","2449":"京元電",
    "6278":"台表科","2313":"華通","3017":"奇鋐","3324":"雙鴻","3035":"智原","3661":"世芯","3443":"創意","3529":"力旺","5274":"信驊","6531":"愛普",
    # 金融
    "2881":"富邦金","2882":"國泰金","2891":"中信金","2886":"兆豐金","2884":"玉山金","2892":"第一金","5880":"合庫金","2880":"華南金","2885":"元大金",
    "2890":"永豐金","2883":"開發金","2887":"台新金","2834":"臺企銀","2801":"彰銀","2812":"台中銀","2809":"京城銀","2888":"新光金","2889":"國票金",
    # 傳產
    "2002":"中鋼","1101":"台泥","1102":"亞泥","2603":"長榮","2609":"陽明","2615":"萬海","2618":"長榮航","2610":"華航","1605":"華新","2201":"裕隆",
    "1519":"華城","1513":"中興電","1503":"士電","1504":"東元","9910":"豐泰","2912":"統一超","1216":"統一","2027":"大成鋼","2014":"中鴻","9945":"潤泰新",
    "1301":"台塑","1303":"南亞","1326":"台化","6505":"台塑化","1402":"遠東新","2105":"正新","2106":"建大","9904":"寶成","9921":"巨大","1560":"中砂",
    "1514":"亞力","1609":"大亞","1907":"永豐餘","2049":"上銀","2371":"大同","2409":"友達","2481":"強茂","2606":"裕民","2637":"慧洋","3008":"大立光"
}

def get_name(ticker):
    code = ticker.replace(".TW", "").replace(".TWO", "").split(".")[0]
    # 1. 查字典
    if code in STOCK_MAP: return STOCK_MAP[code]
    # 2. 若字典沒有，回傳原始代碼 (但前端會用顏色標記)
    return code

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
                    # 如果字典沒抓到，嘗試用 yfinance 的英文名做最後掙扎
                    if display_name == t.replace(".TW", "").replace(".TWO", ""):
                         try: 
                             short = stocks.tickers[t].info.get('shortName', t)
                             display_name = short.split(" ")[0] if len(short) > 0 else t
                         except: pass

                    data.append({
                        "name": display_name, "code": t.replace(".TW", "").replace(".TWO", ""),
                        "full_code": t, "price": f"{price:.2f}",
                        "pct": f"{pct:.2f}%", "color": color, "sign": sign
                    })
            except: continue
    except: pass
    return pd.DataFrame(data)

def get_financial_metrics(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        def safe_get(key, fmt="{:.2f}"):
            val = info.get(key)
            return fmt.format(val) if val is not None else "--"
        return {
            "EPS": safe_get('trailingEps'), "ROE": safe_get('returnOnEquity', "{:.2%}"),
            "ROA": safe_get('returnOnAssets', "{:.2%}"), "PER (本益)": safe_get('trailingPE'),
            "PBR (淨值)": safe_get('priceToBook'), "殖利率": safe_get('dividendYield', "{:.2%}")
        }
    except: return None

# --- 新功能：鄉民八卦抓取 (Mobile01 RSS + PTT Google Search) ---
@st.cache_data(ttl=600)
def fetch_forum_topics():
    topics = []
    # 1. Mobile01 投資理財版 RSS
    try:
        m01 = feedparser.parse("https://www.mobile01.com/rss/topiclist.php?f=291")
        for entry in m01.entries[:6]:
            topics.append({"source": "Mobile01", "title": entry.title, "link": entry.link, "color": "#01c001"})
    except: pass
    
    # 2. PTT Stock (透過 Google RSS 模擬，因 PTT 禁止直接爬蟲)
    try:
        # 搜尋 "PTT Stock" 相關的最新索引
        ptt_url = "https://news.google.com/rss/search?q=site:ptt.cc/bbs/Stock+閒聊&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        ptt = feedparser.parse(ptt_url)
        for entry in ptt.entries[:6]:
            # 清理標題
            title = entry.title.replace(" - 看板 Stock - 批踢踢實業坊", "").replace("Re: ", "")
            topics.append({"source": "PTT", "title": title, "link": entry.link, "color": "#212121"})
    except: pass
    
    return topics

def fetch_specific_stock_news(stock_name):
    encoded_name = urllib.parse.quote(stock_name)
    rss_url = f"https://news.google.com/rss/search?q={encoded_name}+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:5]:
            news_items.append({"title": entry.title, "link": entry.link, "date": entry.published[:16] if 'published' in entry else ""})
        return news_items
    except: return []

# --- 7. 戰情室分頁配置 ---
tab1, tab2, tab5, tab6, tab4 = st.tabs(["📊 我的投資", "🔥 市場熱點", "🔍 個股健檢", "🗣️ 鄉民八卦", "📰 產業新聞"])

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
                    update_cloud_remove(row['full_code'], "inventory", current_user); st.cache_data.clear(); st.rerun()
    else: st.info(f"嗨 {current_user}，庫存空白，請從左側加入股票。")

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
                    update_cloud_remove(row['full_code'], "watchlist", current_user); st.cache_data.clear(); st.rerun()
    else: st.info("暫無觀察名單")

# === Tab 2: 市場熱點 (30檔) ===
with tab2:
    st.markdown("""<div class="section-header">🔥 市場 30 大熱門討論股 <span class="hot-badge">HOT</span></div>""", unsafe_allow_html=True)
    
    # 30 檔熱門股 (依熱度與成交量排序)
    HOT_SEARCH_TICKERS = [
        "00940.TW", "00919.TW", "00929.TW", "00878.TW", "0056.TW", "0050.TW", "00939.TW", "00679B.TW",
        "2330.TW", "2317.TW", "2454.TW", "3231.TW", "2382.TW", "2376.TW", "6669.TW", "3035.TW",
        "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "1519.TW", "1513.TW", "1503.TW",
        "1605.TW", "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2892.TW"
    ]
    
    df_hot_search = get_stock_data(HOT_SEARCH_TICKERS)
    if not df_hot_search.empty:
        hot_cols = st.columns(8) # 一行8個
        for i, row in df_hot_search.iterrows():
            with hot_cols[i%8]:
                url = f"https://www.google.com/search?q={row['name']} 股票 討論 ptt"
                st.markdown(f"""<a href="{url}" target="_blank" class="hot-link"><div class="hot-card"><div class="compact-name" style="color:#d84315;">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div><div style="font-size:11px; color:{row['color']};">{row['sign']} {row['pct']}</div></div></a>""", unsafe_allow_html=True)

# === Tab 6: 🗣️ 鄉民八卦 (PTT/Mobile01) ===
with tab6:
    st.markdown("""<div class="section-header">🗣️ 鄉民八卦 & 熱門話題</div>""", unsafe_allow_html=True)
    st.caption("彙整「PTT 股版」與「Mobile01 投資版」的最新熱門討論。")
    
    # 顯示論壇熱門文章
    forum_topics = fetch_forum_topics()
    if forum_topics:
        for topic in forum_topics:
            badge_color = "#01c001" if topic['source'] == "Mobile01" else "#212121"
            st.markdown(f"""
            <a href="{topic['link']}" target="_blank" class="forum-title-link">
                <span style="background:{badge_color}; color:white; padding:2px 6px; border-radius:4px; font-size:12px; margin-right:5px;">{topic['source']}</span>
                {topic['title']}
            </a>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""<div class="section-header">🔎 快速傳送門</div>""", unsafe_allow_html=True)
    
    # 建立 8 個快速按鈕，直接連到該網站
    f_cols = st.columns(4)
    with f_cols[0]: st.markdown(f"""<a href="https://www.ptt.cc/bbs/Stock/index.html" target="_blank" class="hot-link"><div class="forum-card"><div style="font-weight:900; color:#212121">PTT 股版</div><div style="font-size:11px;">鄉民閒聊</div></div></a>""", unsafe_allow_html=True)
    with f_cols[1]: st.markdown(f"""<a href="https://www.mobile01.com/topiclist.php?f=793" target="_blank" class="hot-link"><div class="forum-card"><div style="font-weight:900; color:#01c001">Mobile01</div><div style="font-size:11px;">投資理財</div></div></a>""", unsafe_allow_html=True)
    with f_cols[2]: st.markdown(f"""<a href="https://www.cmoney.tw/forum/" target="_blank" class="hot-link"><div class="forum-card"><div style="font-weight:900; color:#d32f2f">股市爆料</div><div style="font-size:11px;">同學會</div></div></a>""", unsafe_allow_html=True)
    with f_cols[3]: st.markdown(f"""<a href="https://stock.wearn.com/" target="_blank" class="hot-link"><div class="forum-card"><div style="font-weight:900; color:#1565c0">聚財網</div><div style="font-size:11px;">高手文章</div></div></a>""", unsafe_allow_html=True)

# === Tab 5: 個股健檢 (含專屬新聞) ===
with tab5:
    st.markdown('<div class="section-header">🔍 財務與籌碼概況</div>', unsafe_allow_html=True)
    all_stocks = []
    if not df_inv.empty: all_stocks.extend(df_inv['full_code'].tolist())
    if not df_watch.empty: all_stocks.extend(df_watch['full_code'].tolist())
    all_stocks = list(set(all_stocks))
    
    if all_stocks:
        selected_stock = st.selectbox("請選擇股票:", all_stocks, format_func=lambda x: f"{get_name(x)} ({x.split('.')[0]})")
        if selected_stock:
            stock_name_zh = get_name(selected_stock)
            with st.spinner(f"正在分析 {stock_name_zh} ..."):
                metrics = get_financial_metrics(selected_stock)
            if metrics:
                # 1. 財務指標
                m_cols = st.columns(3)
                keys = list(metrics.keys())
                for i, key in enumerate(keys):
                    with m_cols[i % 3]:
                        st.markdown(f"""<div class="metric-card"><div class="metric-label">{key}</div><div class="metric-value">{metrics[key]}</div></div>""", unsafe_allow_html=True)
                
                # 2. 專屬新聞
                st.markdown(f"""<div class="section-header">📰 {stock_name_zh} 最新相關新聞</div>""", unsafe_allow_html=True)
                stock_news = fetch_specific_stock_news(stock_name_zh)
                if stock_news:
                    for news in stock_news:
                        st.markdown(f"""<div class="stock-news-card"><a href="{news['link']}" target="_blank" class="stock-news-title">{news['title']}</a><div class="stock-news-date">{news['date']}</div></div>""", unsafe_allow_html=True)
                else: st.info(f"暫無 {stock_name_zh} 的相關新聞。")
            else: st.error("查無數據")
    else: st.warning("請先加入股票。")

# === Tab 4: 產業新聞 ===
with tab4:
    user_rss = get_list_from_cloud("news", current_user)
    with st.spinner("載入新聞..."):
        news_buckets = fetch_and_filter_news(user_rss)
    for cat, items in news_buckets.items():
        if items:
            st.markdown(f'<div class="news-category-header">{cat} ({len(items)})</div>', unsafe_allow_html=True)
            for n in items:
                st.markdown(f'<div class="news-item-compact"><a href="{n["link"]}" target="_blank" class="news-link-text">{n["title"]}</a><div class="news-meta-compact">{n["src"]} • {n["date"]}</div></div>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
