import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. 頁面與時區設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海顧問", initial_sidebar_state="collapsed")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh")

TW_TZ = timezone(timedelta(hours=8))
def get_tw_time():
    return datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')

# --- 2. GAS API ---
# 請確認這是否為您最新部署 (有選「建立新版本」) 的網址
GAS_URL = "https://script.google.com/macros/s/AKfycbwTsM79MMdedizvIcIn7tgwT81VIhj87WM-bvR45QgmMIUsIemmyR_FzMvG3v5LEHEvPw/exec"

# --- 3. 媒體與 CSS 設定 ---
MEDIA_PRESETS = {
    "雅虎": "https://finance.yahoo.com/news/rssindex", "鉅亨": "https://news.cnyes.com/rss/cat/headline",
    "聯合": "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money", "經濟": "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
    "moneydj": "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml", "商周": "https://www.businessweekly.com.tw/rss/latest",
    "科技": "https://technews.tw/feed/"
}

# 修復 CSS 格式，避免顯示亂碼
st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
.compact-card { border: 1px solid #ddd; border-radius: 6px; padding: 5px 2px; text-align: center; background: white; margin-bottom: 5px; box-shadow: 1px 1px 2px rgba(0,0,0,0.1); min-height: 80px; }
.compact-name { font-size: 15px !important; font-weight: 900; color: #333; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.compact-price { font-size: 18px !important; font-weight: bold; margin: 0;}
.news-category-header { background-color: #e3f2fd; color: #0d47a1; padding: 8px 12px; border-left: 6px solid #0d47a1; font-size: 20px !important; font-weight: 900; margin-top: 20px; margin-bottom: 5px; border-radius: 4px; }
.news-item-compact { padding: 6px 0; border-bottom: 1px dashed #ccc; line-height: 1.3; }
.news-link-text { text-decoration: none; color: #222; font-size: 18px !important; font-weight: 600; display: block; }
.news-link-text:hover { color: #d32f2f; }
.news-meta-compact { font-size: 12px; color: #666; margin-top: 2px;}
.rank-title { font-size: 18px; font-weight: 900; color: #fff; background: linear-gradient(90deg, #d32f2f, #ef5350); padding: 8px; border-radius: 5px 5px 0 0; margin-top: 15px; text-align: center; }
.rank-box { border: 1px solid #ef5350; border-top: none; border-radius: 0 0 5px 5px; padding: 5px; background: #fff; margin-bottom: 15px; }
.rank-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px dashed #eee; }
.rank-name { font-size: 16px; font-weight: bold; color: #333; }
.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; font-size: 18px;}
div[data-testid="column"] { padding: 0 2px !important; }
</style>
""", unsafe_allow_html=True)

# --- 4. 登入邏輯 (含自動登入) ---
query_params = st.query_params
url_user = query_params.get("user", "")
url_pass = query_params.get("password", "")

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_name' not in st.session_state: st.session_state['user_name'] = ""

def verify_user(username, password):
    try:
        response = requests.get(GAS_URL, params={"action": "login", "user": username, "password": password}, timeout=5)
        res = response.json()
        return res.get("status") == "success"
    except: return False

def register_user(username, password):
    try:
        response = requests.get(GAS_URL, params={"action": "signup", "user": username, "password": password}, timeout=5)
        return response.json()
    except: return {"status": "error", "msg": "連線失敗"}

# 自動登入嘗試
if not st.session_state['logged_in'] and url_user and url_pass:
    if verify_user(url_user, url_pass):
        st.session_state['logged_in'] = True
        st.session_state['user_name'] = url_user

# 登入閘道 UI
if not st.session_state['logged_in']:
    st.title("🔐 歡迎來到股海顧問")
    st.caption("請登入以存取您的專屬資料")
    
    tab1, tab2 = st.tabs(["🔑 登入", "📝 註冊"])
    
    with tab1:
        with st.form("login_form"):
            user_in = st.text_input("帳號", value=url_user)
            pass_in = st.text_input("密碼", type="password")
            submitted = st.form_submit_button("登入", type="primary")
            if submitted:
                if verify_user(user_in, pass_in):
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = user_in
                    st.query_params["user"] = user_in
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤 (請確認 GAS 是否已發布為『新版本』)")
    
    with tab2:
        with st.form("signup_form"):
            new_user = st.text_input("設定帳號")
            new_pass = st.text_input("設定密碼", type="password")
            submit_reg = st.form_submit_button("註冊")
            if submit_reg and new_user and new_pass:
                res = register_user(new_user, new_pass)
                if res.get("status") == "success":
                    st.success("註冊成功！請切換到登入頁籤登入。")
                else:
                    st.error(f"註冊失敗：{res.get('msg')}")
    st.stop()

# =========================================================
# 主程式
# =========================================================

current_user = st.session_state['user_name']

# 側邊欄
with st.sidebar:
    st.header(f"👤 {current_user}")
    
    my_link = f"?user={current_user}"
    with st.expander("🔗 取得分享連結"):
        st.caption("分享此連結給朋友 (對方需輸入密碼)")
        st.code(f"https://share.streamlit.io/...(您的網址)...{my_link}", language="text")

    if st.button("登出"):
        st.session_state['logged_in'] = False
        st.query_params.clear()
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
            url = new_rss
            if new_rss in MEDIA_PRESETS: url = MEDIA_PRESETS[new_rss]
            try: requests.get(GAS_URL, params={"action": "add", "code": url, "type": "news", "user": current_user}, timeout=2)
            except: pass
            st.cache_data.clear(); st.rerun()
    
    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# 標題與更新區
c_title, c_btn = st.columns([3, 1])
with c_title:
    st.title(f"👵 {current_user} 的股海顧問") 
    st.caption(f"台灣時間：{get_tw_time()} | 自動更新中...")
with c_btn:
    st.write("") 
    if st.button("🔴 點我更新股價", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- 資料處理函數 ---
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

HOT_LISTS = {
    "🔥 熱門討論": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], 
    "💎 人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], 
    "💡 焦點概念": ["1519.TW", "1513.TW", "2308.TW", "2454.TW", "6669.TW", "2376.TW"] 
}

STOCK_MAP = {"00878": "國泰高股息", "2330": "台積電", "2317": "鴻海", "2603": "長榮", "2609": "陽明", "2454": "聯發科", "3231": "緯創", "0056": "元大高股息", "0050": "台灣50", "00919": "群益精選", "00940": "台灣價值", "1519": "華城", "1513": "中興電", "1503": "士電", "2382": "廣達", "6669": "緯穎", "2376": "技嘉", "2002": "中鋼", "1101": "台泥", "2201": "裕隆", "2412":"中華電", "2308":"台達電", "2881":"富邦金", "2882":"國泰金"}

def get_list_from_cloud(list_type, user):
    try:
        response = requests.get(GAS_URL, params={"action": "read", "type": list_type, "user": user}, timeout=5)
        return response.json() or []
    except: return []

def update_cloud_remove(code, list_type, user):
    try: requests.get(GAS_URL, params={"action": "remove", "code": code, "type": list_type, "user": user}, timeout=2)
    except: pass

def get_name(ticker):
    code = ticker.split(".")[0]
    return STOCK_MAP.get(code, code)

# 修復語法錯誤：確保變數名稱與邏輯正確
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

@st.cache_data(ttl=300) 
def fetch_and_filter_news(user_rss_urls):
    buckets = {key: [] for key in KEYWORD_MAPPING.keys()}
    buckets["🌍 其他頭條"] = []
    seen = set()
    
    default_rss = [
        "https://news.cnyes.com/rss/cat/headline", 
        "https://news.cnyes.com/rss/cat/200",
        "https://news.cnyes.com/rss/cat/hotai",
        "https://finance.yahoo.com/news/rssindex",
        "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
        "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml",
        "https://technews.tw/feed/"
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
if inv_list:
    df = get_stock_data(inv_list)
    cols = st.columns(6)
    for i, row in df.iterrows():
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
else: st.info("清單空白，請從側邊欄新增。")

# 2. 觀察
st.subheader(f"👀 {current_user} 的觀察名單")
watch_list = get_list_from_cloud("watchlist", current_user)
if watch_list:
    df_w = get_stock_data(watch_list)
    cols2 = st.columns(6)
    for i, row in df_w.iterrows():
        with cols2[i%6]:
            st.markdown(f"""<div class="compact-card"><div class="compact-name">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"dw_{row['code']}"): 
                update_cloud_remove(row['full_code'], "watchlist", current_user)
                st.cache_data.clear(); st.rerun()

# 3. 熱門
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
