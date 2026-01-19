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

# --- 3. CSS 設定 (優化6欄位顯示) ---
st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
/* 股票卡片：強制最小寬度，避免6個擠在一起變形 */
.compact-card { 
    border: 1px solid #ddd; border-radius: 6px; 
    padding: 8px 2px; text-align: center; 
    background: white; margin-bottom: 5px; 
    box-shadow: 1px 1px 2px rgba(0,0,0,0.1); 
    min-height: 85px;
}
.compact-name { 
    font-size: 16px !important; font-weight: 900; color: #333; 
    margin: 0; line-height: 1.2;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; /* 名字太長自動變... */
}
.compact-price { font-size: 20px !important; font-weight: bold; margin: 2px 0 0 0;}

/* 新聞樣式 */
.news-category-header { background-color: #e3f2fd; color: #0d47a1; padding: 8px 12px; border-left: 6px solid #0d47a1; font-size: 20px !important; font-weight: 900; margin-top: 20px; margin-bottom: 5px; border-radius: 4px; }
.news-item-compact { padding: 6px 0; border-bottom: 1px dashed #ccc; line-height: 1.3; }
.news-link-text { text-decoration: none; color: #222; font-size: 18px !important; font-weight: 600; display: block; }
.news-link-text:hover { color: #d32f2f; }
.news-meta-compact { font-size: 12px; color: #666; margin-top: 2px;}

/* 榜單 */
.rank-title { font-size: 18px; font-weight: 900; color: #fff; background: linear-gradient(90deg, #d32f2f, #ef5350); padding: 8px; border-radius: 5px 5px 0 0; margin-top: 15px; text-align: center; }
.rank-box { border: 1px solid #ef5350; border-top: none; border-radius: 0 0 5px 5px; padding: 5px; background: #fff; margin-bottom: 15px; }
.rank-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px dashed #eee; }
.rank-name { font-size: 16px; font-weight: bold; color: #333; }
.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; font-size: 18px;}
div[data-testid="column"] { padding: 0 2px !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. 側邊欄與使用者設定 ---
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
            url = new_rss
            if new_rss in MEDIA_PRESETS: url = MEDIA_PRESETS[new_rss]
            try: requests.get(GAS_URL, params={"action": "add", "code": url, "type": "news", "user": current_user}, timeout=2)
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
    if st.button("🔴 點我更新股價", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- 5. 超級漢化字典 (包含300+熱門股) ---
STOCK_MAP = {
    # === 熱門 ETF ===
    "0050": "元大台灣50", "0056": "元大高股息", "00878": "國泰永續高股息", "00919": "群益台灣精選", 
    "00929": "復華科技優息", "00940": "元大台灣價值", "006208": "富邦台50", "00713": "元大高息低波",
    "00939": "統一台灣高息", "00944": "野村趨勢動能", "00679B": "元大美債20年", "00687B": "國泰20年美債",
    "0051": "元大中型100", "00631L": "元大台灣50正2", "00632R": "元大台灣50反1", "00881": "國泰5G+",
    
    # === 半導體與電子權值 ===
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2303": "聯電", "2308": "台達電", 
    "3711": "日月光投控", "3034": "聯詠", "2379": "瑞昱", "3037": "欣興", "2382": "廣達", 
    "3231": "緯創", "6669": "緯穎", "2357": "華碩", "2356": "英業達", "2376": "技嘉",
    "2301": "光寶科", "2412": "中華電", "3045": "台灣大", "4904": "遠傳", "2345": "智邦",
    "2324": "仁寶", "2353": "宏碁", "2354": "鴻準", "2327": "國巨", "2344": "華邦電",
    "2408": "南亞科", "3036": "文曄", "3702": "大聯大", "2395": "研華", "4938": "和碩",
    "2383": "台光電", "2368": "金像電", "6239": "力成", "6415": "矽力-KY", "5269": "祥碩",
    
    # === 金融股全家桶 ===
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2886": "兆豐金", "2884": "玉山金", 
    "2892": "第一金", "5880": "合庫金", "2880": "華南金", "2885": "元大金", "2890": "永豐金", 
    "2883": "開發金", "2887": "台新金", "2834": "臺企銀", "2801": "彰銀", "2812": "台中銀",
    "2809": "京城銀", "2888": "新光金", "2889": "國票金", "5876": "上海商銀", "2897": "王道銀",
    
    # === 傳產龍頭 ===
    "2002": "中鋼", "1101": "台泥", "1102": "亞泥", "2603": "長榮", "2609": "陽明", 
    "2615": "萬海", "2618": "長榮航", "2610": "華航", "1605": "華新", "2201": "裕隆", 
    "1519": "華城", "1513": "中興電", "1503": "士電", "1504": "東元", "9910": "豐泰", 
    "2912": "統一超", "1216": "統一", "2027": "大成鋼", "2014": "中鴻", "9945": "潤泰新",
    "1301": "台塑", "1303": "南亞", "1326": "台化", "6505": "台塑化", "1402": "遠東新",
    "2105": "正新", "2106": "建大", "9904": "寶成", "9921": "巨大", "9914": "美利達",
    
    # === 營建與其他 ===
    "2501": "國建", "2520": "冠德", "2542": "興富發", "2548": "華固", "5522": "遠雄",
    "9940": "信義", "2915": "潤泰全", "1722": "台肥", "1717": "長興", "1710": "東聯",
    
    # === 上櫃/熱門中小型 ===
    "2476": "鉅祥", "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "6191": "精成科", "6761": "穩得", "6788": "華景電", "8926": "台汽電", "3661": "世芯-KY", 
    "3443": "創意", "3529": "力旺", "5274": "信驊", "3293": "鈊象", "8299": "群聯",
    "8069": "元太", "5347": "世界", "6488": "環球晶", "5483": "中美晶", "3105": "穩懋",
    "3260": "威剛", "6274": "台燿", "6223": "旺矽", "3583": "辛耘", "1560": "中砂"
}

def get_name(ticker):
    # 移除 .TW 或 .TWO 進行比對
    code = ticker.replace(".TW", "").replace(".TWO", "").split(".")[0]
    return STOCK_MAP.get(code, code)

# --- 資料處理函數 ---
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
    valid = []
    for t in ticker_list:
        if t and str(t).strip() != "":
            valid.append(str(t).strip())
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
                    
                    # 優先使用漢化字典，如果沒有，顯示代碼
                    display_name = get_name(t)
                    
                    # 如果字典沒抓到，嘗試用 yfinance 的英文名 (最後防線)
                    if display_name == t.replace(".TW", "").replace(".TWO", ""):
                         try: 
                             short = stocks.tickers[t].info.get('shortName', t)
                             # 簡單過濾掉太長的英文 (選前兩個單字)
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

@st.cache_data(ttl=300) 
def fetch_and_filter_news(user_rss_urls):
    KEYWORD_MAPPING = {
        "🤖 AI 與半導體": ["台積電", "聯電", "聯發科", "日月光", "AI", "半導體", "晶圓", "輝達", "NVIDIA", "CoWoS", "先進封裝", "伺服器", "緯創", "廣達", "技嘉", "智原", "世芯", "創意"],
        "🏗️ 鋼鐵與水泥": ["中鋼", "中鴻", "大成鋼", "鋼鐵", "台泥", "亞泥", "水泥", "玻陶", "豐興", "鋼價", "基建", "春雨", "燁輝"],
        "🚢 航運與運輸": ["長榮", "陽明", "萬海", "航運", "貨櫃", "散裝", "BDI", "航空", "華航", "長榮航", "星宇", "運價", "慧洋", "裕民"],
        "🚗 汽車與供應鏈": ["裕隆", "和泰車", "中華車", "汽車", "電動車", "特斯拉", "Tesla", "鴻華", "充電樁", "車用", "東陽", "堤維西", "AM", "帝寶", "和大"],
        "💰 金融與銀行": ["金控", "銀行", "壽險", "富邦", "國泰", "中信", "玉山", "兆豐", "台新", "升息", "降息", "股利", "配息", "第一金", "華南金"],
        "⚡ 重電與綠能": ["華城", "士電", "中興電", "亞力", "重電", "綠能", "風電", "太陽能", "儲能", "台電", "電網", "森崴", "世紀鋼"],
        "💊 生技與防疫": ["生技", "藥", "疫苗", "合一", "高端", "美時", "保瑞", "醫療", "長聖", "藥華藥"],
        "🏠 營建與房產": ["營建", "房地產", "房市", "遠雄", "興富發", "國產", "預售屋", "潤泰", "冠德"]
    }
    buckets = {key: [] for key in KEYWORD_MAPPING.keys()}
    buckets["🌍 其他頭條"] = []
    seen = set()
    
    default_rss = [
        "https://news.cnyes.com/rss/cat/headline", "https://news.cnyes.com/rss/cat/200",
        "https://news.cnyes.com/rss/cat/hotai", "https://finance.yahoo.com/news/rssindex",
        "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
        "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml", "https://technews.tw/feed/"
    ]
    if user_rss_urls: default_rss.extend(user_rss_urls)
    final_rss = list(set(default_rss))

    for url in final_rss:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:80]: 
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

# 1. 庫存
st.subheader(f"💰 {current_user} 的庫存")
inv_list = get_list_from_cloud("inventory", current_user)
df_inv = pd.DataFrame() 
if inv_list: df_inv = get_stock_data(inv_list)

if not df_inv.empty:
    cols = st.columns(6) # 堅持 6 欄位
    for i, row in df_inv.iterrows():
        with cols[i%6]:
            st.markdown(f"""
            <div class="compact-card" style="border-left: 4px solid {row['color']};">
                <div class="compact-name" title="{row['name']}">{row['name']}</div>
                <div class="compact-price" style="color:{row['color']}">{row['price']}</div>
                <div style="font-size:12px; font-weight:bold; color:{row['color']}">{row['sign']} {row['pct']}</div>
            </div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"d_{row['code']}"): 
                update_cloud_remove(row['full_code'], "inventory", current_user)
                st.cache_data.clear(); st.rerun()
else: st.info(f"嗨 {current_user}，庫存清單是空的，請從左側加入股票。")

# 2. 觀察
st.subheader(f"👀 {current_user} 的觀察名單")
watch_list = get_list_from_cloud("watchlist", current_user)
df_watch = pd.DataFrame() 
if watch_list: df_watch = get_stock_data(watch_list)

if not df_watch.empty:
    cols2 = st.columns(6) # 堅持 6 欄位
    for i, row in df_watch.iterrows():
        with cols2[i%6]:
            st.markdown(f"""<div class="compact-card"><div class="compact-name">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"dw_{row['code']}"): 
                update_cloud_remove(row['full_code'], "watchlist", current_user)
                st.cache_data.clear(); st.rerun()
else: st.info("暫無觀察名單。")

# 3. 熱門
st.markdown("---")
st.subheader("🏆 市場熱門戰情室")
HOT_LISTS = {
    "🔥 熱門討論": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], 
    "💎 人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], 
    "💡 焦點概念": ["1519.TW", "1513.TW", "2308.TW", "2454.TW", "6669.TW", "2376.TW"] 
}
hot_cols = st.columns(3)
idx = 0
for title, tickers in HOT_LISTS.items():
    with hot_cols[idx]:
        st.markdown(f'<div class="rank-title">{title}</div>', unsafe_allow_html=True)
        df_hot = get_stock_data(tickers)
        if not df_hot.empty:
            html = '<div class="rank-box">'
            for _, row in df_hot.iterrows():
                html += f"""<div class="rank-row"><span class="rank-name">{row['name']}</span><span class="rank-price" style="color:{row['color']}">{row['sign']} {row['price']}</span></div>"""
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
    idx += 1

# 4. 新聞
st.markdown("---")
st.subheader("🗞️ 產業新聞快遞")
user_rss = get_list_from_cloud("news", current_user)
with st.spinner("正在搜尋最新新聞..."):
    news_buckets = fetch_and_filter_news(user_rss)

display_order = ["🤖 AI 與半導體", "🏗️ 鋼鐵與水泥", "🚢 航運與運輸", "🚗 汽車與供應鏈", "💰 金融與銀行", "⚡ 重電與綠能", "💊 生技與防疫", "🏠 營建與房產", "🌍 其他頭條"]

for category in display_order:
    items = news_buckets.get(category, [])
    if items:
        st.markdown(f'<div class="news-category-header">{category} ({len(items)})</div>', unsafe_allow_html=True)
        for n in items: 
            st.markdown(f"""
            <div class="news-item-compact">
                <a href="{n['link']}" target="_blank" class="news-link-text">
                    {n['title']}
                </a>
                <div class="news-meta-compact">
                    {n['src']} • {n['date']}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
