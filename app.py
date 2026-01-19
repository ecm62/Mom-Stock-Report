import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
import urllib.parse # 用於網址編碼

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
/* 全域設定 */
html, body, [class*="css"] { 
    font-family: "Microsoft JhengHei", "Segoe UI", Roboto, Helvetica, sans-serif; 
}

/* 訪客計數器 */
.visitor-counter {
    position: fixed; bottom: 10px; right: 15px; font-size: 11px;
    color: #bdbdbd; background-color: rgba(255,255,255,0.95);
    padding: 3px 10px; border-radius: 12px; z-index: 9999;
    border: 1px solid #eee; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* Tab 分頁籤優化 */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
    height: 42px; border-radius: 6px; background-color: #f8f9fa; color: #5f6368;
    font-weight: 700; font-size: 15px; padding: 0 18px; border: 1px solid #eee;
}
.stTabs [aria-selected="true"] {
    background-color: #1a73e8 !important; color: white !important; border-color: #1a73e8;
}

/* 響應式欄位控制 (電腦8欄 / 手機4欄) */
div[data-testid="column"] {
    min-width: 85px !important; 
    flex: 1 1 auto !important;
    padding: 0 2px !important; 
}

/* 股票卡片 */
.compact-card { 
    border: 1px solid #f1f3f4; border-radius: 8px; padding: 6px 2px; 
    text-align: center; background: white; margin-bottom: 0px; 
    box-shadow: 0 1px 2px rgba(0,0,0,0.03); min-height: 72px; transition: all 0.2s;
}
.compact-card:hover { transform: translateY(-2px); border-color: #cfd8dc; box-shadow: 0 4px 8px rgba(0,0,0,0.08);}

/* 專區卡片樣式 */
a.hot-link { text-decoration: none; color: inherit; display: block; margin-bottom: 4px;}
.hot-card, .opinion-card, .tech-card {
    border-radius: 8px; padding: 8px 2px; text-align: center; 
    box-shadow: 0 1px 2px rgba(0,0,0,0.03); min-height: 75px; transition: all 0.2s;
}
.hot-card { border: 1px solid #ffccbc; background: #fffbfb; }
.opinion-card { border: 1px solid #d1c4e9; background: #fdfbff; }
.tech-card { border: 1px solid #bbdefb; background: #f0f7ff; }

.hot-card:hover { border-color: #ff5722; box-shadow: 0 4px 8px rgba(255, 87, 34, 0.15); transform: translateY(-2px);}
.opinion-card:hover { border-color: #673ab7; box-shadow: 0 4px 8px rgba(103, 58, 183, 0.15); transform: translateY(-2px);}
.tech-card:hover { border-color: #2196f3; box-shadow: 0 4px 8px rgba(33, 150, 243, 0.15); transform: translateY(-2px);}

.compact-name, .opinion-name, .tech-name { font-size: 13px !important; font-weight: 700; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.compact-name { color: #37474f; } .opinion-name { color: #4527a0; } .tech-name { color: #0d47a1; }
.compact-price { font-size: 18px !important; font-weight: 800; margin: 2px 0 0 0; letter-spacing: -0.5px; font-family: "Segoe UI", sans-serif;}
.opinion-tag, .tech-tag { font-size: 10px !important; margin-top: 2px; font-weight: bold;}
.opinion-tag { color: #7e57c2; } .tech-tag { color: #1976d2; }

/* 財務指標卡片 */
.metric-card {
    background-color: #f1f8e9; border-left: 4px solid #66bb6a;
    padding: 8px; border-radius: 4px; margin-bottom: 8px; text-align: center;
}
.metric-label { font-size: 12px; color: #558b2f; font-weight: bold; }
.metric-value { font-size: 18px; color: #33691e; font-weight: 900; }

/* 個股專屬新聞 */
.stock-news-card {
    padding: 8px 0; border-bottom: 1px dashed #e0e0e0;
}
.stock-news-title {
    font-size: 15px; font-weight: 700; color: #1565c0; text-decoration: none; display: block; line-height: 1.4;
}
.stock-news-title:hover { text-decoration: underline; color: #0d47a1; }
.stock-news-date { font-size: 11px; color: #757575; margin-top: 2px; }

/* 隱形刪除鈕 */
div[data-testid="column"] .stButton > button {
    width: 100%; border: none !important; background: transparent !important;
    color: #f5f5f5 !important; font-size: 10px !important; padding: 0 !important;
    height: 14px !important; margin-top: -2px !important; 
}
div[data-testid="column"] .stButton > button:hover { color: #ef5350 !important; font-weight: bold; background: rgba(255, 235, 238, 0.5) !important; }

/* 標題與按鈕 */
.section-header { font-size: 16px; font-weight: 900; color: #37474f; padding: 8px 0; border-bottom: 2px solid #eceff1; margin: 15px 0 10px 0; letter-spacing: 0.5px;}
.hot-badge { background: #ff3d00; color: white; padding: 1px 5px; border-radius: 4px; font-size: 11px; margin-left: 5px; vertical-align: middle;}
.opinion-badge { background: #673ab7; color: white; padding: 1px 5px; border-radius: 4px; font-size: 11px; margin-left: 5px; vertical-align: middle;}
.tech-badge { background: #1565c0; color: white; padding: 1px 5px; border-radius: 4px; font-size: 11px; margin-left: 5px; vertical-align: middle;}

.news-category-header { background: #e3f2fd; color: #1565c0; padding: 8px 12px; border-left: 4px solid #1565c0; font-size: 16px !important; font-weight: 900; margin-top: 20px; margin-bottom: 8px; border-radius: 4px; }
.news-item-compact { padding: 8px 0; border-bottom: 1px dashed #e0e0e0; line-height: 1.4; }
.news-link-text { text-decoration: none; color: #333; font-size: 16px !important; font-weight: 600; display: block; }
.news-link-text:hover { color: #1565c0; }

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

# --- 6. 台股全漢化數據庫 (Top 800+) ---
STOCK_MAP = {
    # 熱門 ETF
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息", "00919": "群益台灣精選", 
    "00929": "復華科技優息", "00940": "元大台灣價值", "006208": "富邦台50", "00713": "元大高息低波",
    "00939": "統一台灣高息", "00944": "野村趨勢動能", "00679B": "元大美債20年", "00687B": "國泰20年美債",
    "0051": "元大中型100", "00631L": "元大台灣50正2", "00632R": "元大台灣50反1", "00881": "國泰5G+",
    # 電子/半導體
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2303": "聯電", "2308": "台達電", 
    "3711": "日月光投控", "3034": "聯詠", "2379": "瑞昱", "3037": "欣興", "2382": "廣達", 
    "3231": "緯創", "6669": "緯穎", "2357": "華碩", "2356": "英業達", "2376": "技嘉",
    "2301": "光寶科", "2412": "中華電", "3045": "台灣大", "4904": "遠傳", "2345": "智邦",
    "2324": "仁寶", "2353": "宏碁", "2354": "鴻準", "2327": "國巨", "2344": "華邦電",
    "2408": "南亞科", "3036": "文曄", "3702": "大聯大", "2395": "研華", "4938": "和碩",
    "2383": "台光電", "2368": "金像電", "6239": "力成", "6415": "矽力-KY", "5269": "祥碩",
    "2449": "京元電子", "6278": "台表科", "2313": "華通", "3017": "奇鋐", "3324": "雙鴻",
    # 金融
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2886": "兆豐金", "2884": "玉山金", 
    "2892": "第一金", "5880": "合庫金", "2880": "華南金", "2885": "元大金", "2890": "永豐金", 
    "2883": "開發金", "2887": "台新金", "2834": "臺企銀", "2801": "彰銀", "2812": "台中銀",
    "2809": "京城銀", "2888": "新光金", "2889": "國票金", "5876": "上海商銀", "2897": "王道銀",
    # 傳產
    "2002": "中鋼", "1101": "台泥", "1102": "亞泥", "2603": "長榮", "2609": "陽明", 
    "2615": "萬海", "2618": "長榮航", "2610": "華航", "1605": "華新", "2201": "裕隆", 
    "1519": "華城", "1513": "中興電", "1503": "士電", "1504": "東元", "9910": "豐泰", 
    "2912": "統一超", "1216": "統一", "2027": "大成鋼", "2014": "中鴻", "9945": "潤泰新",
    "1301": "台塑", "1303": "南亞", "1326": "台化", "6505": "台塑化", "1402": "遠東新",
    "2105": "正新", "2106": "建大", "9904": "寶成", "9921": "巨大", "9914": "美利達",
    # 上櫃/IP/生技
    "2476": "鉅祥", "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "6191": "精成科", "6761": "穩得", "6788": "華景電", "8926": "台汽電", "3661": "世芯-KY", 
    "3443": "創意", "3529": "力旺", "5274": "信驊", "3293": "鈊象", "8299": "群聯",
    "8069": "元太", "5347": "世界", "6488": "環球晶", "5483": "中美晶", "3105": "穩懋",
    "3260": "威剛", "6274": "台燿", "6223": "旺矽", "3583": "辛耘", "1560": "中砂",
    "1795": "美時", "6472": "保瑞", "6446": "藥華藥", "4128": "中天", "4743": "合一"
}

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

def fetch_specific_stock_news(stock_name):
    """
    使用 Google News RSS 搜尋特定股票名稱
    """
    # 對關鍵字進行 URL 編碼
    encoded_name = urllib.parse.quote(stock_name)
    # 搜尋 "股票名稱" + "股票" 增加準確度
    rss_url = f"https://news.google.com/rss/search?q={encoded_name}+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        # 只取前 5 則最新相關新聞
        for entry in feed.entries[:5]:
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "date": entry.published[:16] if 'published' in entry else ""
            })
        return news_items
    except: return []

@st.cache_data(ttl=300) 
def fetch_and_filter_news(user_rss_urls):
    KEYWORD_MAPPING = {
        "🤖 AI 與半導體": ["台積電", "聯電", "聯發科", "AI", "半導體", "輝達"],
        "🏗️ 鋼鐵與水泥": ["中鋼", "中鴻", "台泥", "亞泥"],
        "🚢 航運與運輸": ["長榮", "陽明", "萬海", "華航", "長榮航"],
        "💰 金融與銀行": ["金控", "銀行", "壽險", "富邦", "國泰"],
        "⚡ 重電與綠能": ["華城", "士電", "中興電", "重電", "綠能"],
        "🏠 營建與房產": ["營建", "房地產", "遠雄", "興富發"]
    }
    buckets = {key: [] for key in KEYWORD_MAPPING.keys()}
    buckets["🌍 其他頭條"] = []
    seen = set()
    
    default_rss = [
        "https://news.cnyes.com/rss/cat/headline", 
        "https://finance.yahoo.com/news/rssindex",
        "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money"
    ]
    if user_rss_urls and isinstance(user_rss_urls, list): default_rss.extend(user_rss_urls)
    
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

# --- 7. 戰情室分頁配置 ---
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
    
    # 30 檔熱門股 (依熱度與成交量大致排序)
    HOT_SEARCH_TICKERS = [
        # ETF 與 指標
        "00940.TW", "00919.TW", "00929.TW", "00878.TW", "0056.TW", "0050.TW", "00939.TW", "00679B.TW",
        # AI 與 權值
        "2330.TW", "2317.TW", "2454.TW", "3231.TW", "2382.TW", "2376.TW", "6669.TW", "3035.TW",
        # 海運
        "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW",
        # 重電
        "1519.TW", "1513.TW", "1503.TW", "1605.TW",
        # 金融
        "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2892.TW"
    ]
    
    df_hot_search = get_stock_data(HOT_SEARCH_TICKERS)
    if not df_hot_search.empty:
        hot_cols = st.columns(8) # 一行8個
        for i, row in df_hot_search.iterrows():
            with hot_cols[i%8]:
                url = f"https://www.google.com/search?q={row['name']} 股票 討論 ptt"
                st.markdown(f"""<a href="{url}" target="_blank" class="hot-link"><div class="hot-card"><div class="compact-name" style="color:#d84315;">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div><div style="font-size:11px; color:{row['color']};">{row['sign']} {row['pct']}</div></div></a>""", unsafe_allow_html=True)

    st.markdown("""<div class="section-header">📢 名嘴喇叭區 <span class="opinion-badge">名師觀點</span></div>""", unsafe_allow_html=True)
    COMMENTATORS = [
        {"name": "謝金河", "tag": "總經", "q": "謝金河 數字台灣 最新"}, {"name": "權證小哥", "tag": "籌碼", "q": "權證小哥 籌碼 最新"},
        {"name": "陳重銘", "tag": "存股", "q": "不敗教主 陳重銘 最新"}, {"name": "股魚", "tag": "財報", "q": "股魚 價值投資 最新"},
        {"name": "朱家泓", "tag": "技術", "q": "朱家泓 技術分析 最新"}, {"name": "阮慕驊", "tag": "財經", "q": "阮慕驊 財經一路發 最新"},
        {"name": "老王", "desc": "浦惠/均線", "q": "老王愛說笑 技術分析 最新"}, {"name": "林家洋", "desc": "K線教學", "q": "林家洋 K線 教室 最新"}
    ]
    op_cols = st.columns(8)
    for i, p in enumerate(COMMENTATORS):
        with op_cols[i%8]:
            st.markdown(f"""<a href="https://www.google.com/search?q={p['q']}&tbm=vid" target="_blank" class="hot-link"><div class="opinion-card"><div class="opinion-name">{p['name']}</div><div class="opinion-tag">{p['tag'] if 'tag' in p else '名師'}</div><div style="font-size:10px; color:#9575cd;">▶ 觀看</div></div></a>""", unsafe_allow_html=True)

    st.markdown("""<div class="section-header">📈 技術分析戰情室 <span class="tech-badge">K線/指標</span></div>""", unsafe_allow_html=True)
    TECH_SITES = [
        {"name": "玩股網", "desc": "台股指標", "url": "https://www.wantgoo.com/stock"}, {"name": "CMoney", "desc": "籌碼K線", "url": "https://www.cmoney.tw/finance/"},
        {"name": "Goodinfo", "desc": "十年財報", "url": "https://goodinfo.tw/tw/index.asp"}, {"name": "鉅亨網", "desc": "即時看盤", "url": "https://www.cnyes.com/twstock/"},
        {"name": "蔡森", "desc": "型態學", "q": "蔡森 技術分析 最新"}, {"name": "股市爆料", "desc": "即時討論", "url": "https://www.cmoney.tw/follow/channel/"}
    ]
    tc_cols = st.columns(6)
    for i, s in enumerate(TECH_SITES):
        with tc_cols[i%6]:
            link = s["url"] if "url" in s else f"https://www.google.com/search?q={s['q']}&tbm=vid"
            st.markdown(f"""<a href="{link}" target="_blank" class="hot-link"><div class="tech-card"><div class="tech-name">{s['name']}</div><div class="tech-tag">{s['desc']}</div><div style="font-size:10px; color:#64b5f6;">➜ 前往</div></div></a>""", unsafe_allow_html=True)

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
                
                # 2. 專屬新聞 (新功能)
                st.markdown(f"""<div class="section-header">📰 {stock_name_zh} 最新相關新聞</div>""", unsafe_allow_html=True)
                stock_news = fetch_specific_stock_news(stock_name_zh) # 搜尋該股票新聞
                
                if stock_news:
                    for news in stock_news:
                        st.markdown(f"""
                        <div class="stock-news-card">
                            <a href="{news['link']}" target="_blank" class="stock-news-title">{news['title']}</a>
                            <div class="stock-news-date">{news['date']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info(f"暫無 {stock_name_zh} 的相關新聞。")
                    
            else: st.error("查無數據")
    else: st.warning("請先加入股票。")

# === Tab 3: 熱門排行 ===
with tab3:
    st.markdown('<div class="section-header">🏆 市場熱門榜</div>', unsafe_allow_html=True)
    HOT_LISTS = {
        "🔥 交易熱門": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], 
        "💎 人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], 
        "💡 AI 概念": ["1519.TW", "1513.TW", "2308.TW", "2454.TW", "6669.TW", "2376.TW"] 
    }
    hl_cols = st.columns(3)
    idx = 0
    for title, tickers in HOT_LISTS.items():
        with hl_cols[idx]:
            st.markdown(f'<div style="text-align:center; font-weight:bold; margin-bottom:10px; background:#eceff1; padding:5px; border-radius:5px;">{title}</div>', unsafe_allow_html=True)
            df_hot = get_stock_data(tickers)
            if not df_hot.empty:
                for _, row in df_hot.iterrows():
                    st.markdown(f"""<div style="display:flex; justify-content:space-between; border-bottom:1px dashed #cfd8dc; padding:6px;"><span style="font-weight:bold; font-size:14px; color:#455a64;">{row['name']}</span><span style="color:{row['color']}; font-weight:bold;">{row['price']}</span></div>""", unsafe_allow_html=True)
        idx += 1

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
