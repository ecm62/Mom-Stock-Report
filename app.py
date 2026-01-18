import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. 頁面與自動更新 ---
st.set_page_config(layout="wide", page_title="阿美的股海顧問", initial_sidebar_state="collapsed")
st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh") # 5分鐘自動刷新

# --- 2. GAS API ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwTsM79MMdedizvIcIn7tgwT81VIhj87WM-bvR45QgmMIUsIemmyR_FzMvG3v5LEHEvPw/exec"

# --- 3. 媒體關鍵字字典 ---
MEDIA_PRESETS = {
    "雅虎": "https://finance.yahoo.com/news/rssindex",
    "鉅亨": "https://news.cnyes.com/rss/cat/headline",
    "聯合": "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
    "經濟": "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
    "moneydj": "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml",
    "商周": "https://www.businessweekly.com.tw/rss/latest",
    "科技": "https://technews.tw/feed/"
}

# --- 4. CSS 優化 (新聞標題連結化) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
    
    /* 股票卡片 */
    .compact-card {
        border: 1px solid #ddd; border-radius: 6px;
        padding: 5px 2px; text-align: center;
        background: white; margin-bottom: 5px;
        box-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        min-height: 85px;
    }
    .compact-name { font-size: 15px !important; font-weight: 900; color: #333; margin: 0; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
    .compact-price { font-size: 18px !important; font-weight: bold; margin: 2px 0; line-height: 1.2;}
    
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
    .rank-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 5px; border-bottom: 1px dashed #eee; }
    .rank-name { font-size: 16px; font-weight: bold; color: #333; }
    
    /* 產業新聞分類標題 */
    .news-category-header {
        background-color: #e3f2fd; color: #1565c0;
        padding: 10px 15px; border-left: 6px solid #1565c0;
        font-size: 22px !important; font-weight: 900;
        margin-top: 30px; margin-bottom: 15px;
        border-radius: 0 10px 10px 0;
    }
    
    /* 新聞超連結樣式 */
    .news-item { padding: 12px 5px; border-bottom: 1px solid #eee; }
    .news-link-text {
        text-decoration: none; color: #2c3e50;
        font-size: 20px !important; font-weight: 700;
        line-height: 1.5; display: block; margin-bottom: 5px;
    }
    .news-link-text:hover { color: #d32f2f; text-decoration: underline; }
    .news-meta { font-size: 13px; color: #888; }
    
    div[data-testid="column"] { padding: 0 2px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的股海顧問")
st.caption(f"產業新聞自動篩選系統 | 更新：{datetime.now().strftime('%H:%M')}")

# --- 5. 精細化產業關鍵字矩陣 (The Filtering Engine) ---
# 這是系統的大腦，負責把新聞歸類到正確的抽屜
KEYWORD_MAPPING = {
    "🤖 AI 與半導體": ["台積電", "聯電", "聯發科", "日月光", "AI", "半導體", "晶圓", "輝達", "NVIDIA", "CoWoS", "先進封裝", "伺服器", "緯創", "廣達", "技嘉"],
    "🏗️ 鋼鐵與水泥": ["中鋼", "中鴻", "大成鋼", "鋼鐵", "台泥", "亞泥", "水泥", "玻陶", "豐興", "鋼價", "基建"],
    "🚢 航運與運輸": ["長榮", "陽明", "萬海", "航運", "貨櫃", "散裝", "BDI", "航空", "華航", "長榮航", "星宇", "運價"],
    "🚗 汽車與供應鏈": ["裕隆", "和泰車", "中華車", "汽車", "電動車", "特斯拉", "Tesla", "鴻華", "充電樁", "車用", "東陽", "堤維西", "AM"],
    "💰 金融與銀行": ["金控", "銀行", "壽險", "富邦", "國泰", "中信", "玉山", "兆豐", "台新", "升息", "降息", "股利", "配息"],
    "⚡ 重電與綠能": ["華城", "士電", "中興電", "亞力", "重電", "綠能", "風電", "太陽能", "儲能", "台電", "電網"],
    "💊 生技與防疫": ["生技", "藥", "疫苗", "合一", "高端", "美時", "保瑞", "醫療"],
    "🏠 營建與房產": ["營建", "房地產", "房市", "遠雄", "興富發", "國產", "預售屋"]
}

# 熱門榜單
HOT_LISTS = {
    "🔥 熱門討論": ["2330.TW", "2317.TW", "3231.TW", "2382.TW", "2603.TW", "2609.TW"], 
    "💎 人氣 ETF": ["00878.TW", "0056.TW", "0050.TW", "00919.TW", "00929.TW", "00940.TW"], 
    "💡 焦點概念": ["1519.TW", "1513.TW", "2308.TW", "2454.TW", "6669.TW", "2376.TW"] 
}

# 漢化字典
STOCK_MAP = {
    "00878": "國泰永續高股息", "2301": "光寶科", "2308": "台達電", "2412": "中華電", 
    "2476": "鉅祥", "2884": "玉山金", "2892": "第一金", "3034": "聯詠", 
    "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "5880": "合庫金", "6191": "精成科", "6761": "穩得", "6788": "華景電", 
    "8926": "台汽電", "2330": "台積電", "2317": "鴻海", "2603": "長榮", 
    "2609": "陽明", "2615": "萬海", "2454": "聯發科", "3231": "緯創",
    "0056": "元大高股息", "0050": "元大台灣50", "00919": "群益台灣精選", "00929": "復華科技優息",
    "00940": "元大台灣價值", "1519": "華城", "1513": "中興電", "1503": "士電", "2382": "廣達", "6669": "緯穎",
    "2376": "技嘉", "2002": "中鋼", "1101": "台泥", "2201": "裕隆"
}

# --- 6. 核心函數 ---

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

@st.cache_data(ttl=300)
def fetch_and_filter_news(rss_urls):
    # 建立空的分類桶
    buckets = {key: [] for key in KEYWORD_MAPPING.keys()}
    buckets["🌍 其他頭條"] = []
    
    seen_titles = set()
    
    # 擴充預設新聞源：加入鉅亨頭條、鉅亨台股、MoneyDJ
    if not rss_urls:
        rss_urls = [
            "https://news.cnyes.com/rss/cat/headline", # 頭條
            "https://news.cnyes.com/rss/cat/200",      # 台股新聞
            "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
            "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml"
        ]

    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            # 抓取數量提升到 40 則，增加匹配成功率
            for entry in feed.entries[:40]: 
                title = entry.title
                if title[:10] in seen_titles: continue
                seen_titles.add(title[:10])
                
                # 簡單翻譯英文
                if "yahoo" in url and sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < len(title)*0.3:
                     try: title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                     except: pass
                
                item = {
                    "title": title, 
                    "link": entry.link, 
                    "date": entry.get('published', '')[:16], 
                    "src": feed.feed.get('title', '新聞')
                }
                
                # --- 關鍵字匹配引擎 ---
                matched = False
                for category, keywords in KEYWORD_MAPPING.items():
                    if any(kw in title for kw in keywords):
                        buckets[category].append(item)
                        matched = True
                        break # 歸類到第一個符合的分類
                
                if not matched:
                    buckets["🌍 其他頭條"].append(item)
                    
        except: continue
    return buckets

# --- 7. 介面佈局 ---

with st.sidebar:
    st.header("⚙️ 管理員後台")
    
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

    with st.expander("📰 新增【新聞頻道】"):
        st.info("輸入「鉅亨」、「雅虎」或網址")
        new_rss_input = st.text_input("媒體名稱", key="add_rss_input")
        if st.button("加入頻道"):
            url = new_rss_input
            if new_rss_input in MEDIA_PRESETS: url = MEDIA_PRESETS[new_rss_input]
            elif "http" not in new_rss_input and new_rss_input in MEDIA_PRESETS: url = MEDIA_PRESETS[new_rss_input] # 簡易防呆
            
            update_cloud("add", url, "news")
            st.success("已加入")
            st.cache_data.clear(); st.rerun()
        
        feeds = get_list_from_cloud("news")
        if feeds:
            st.write("已加入頻道：")
            for f in feeds:
                c1,c2=st.columns([4,1])
                c1.text(f[:20]+"...")
                if c2.button("刪", key=f"d_{f}"): update_cloud("remove",f,"news"); st.rerun()

    if st.button("🔄 強制更新"): st.cache_data.clear(); st.rerun()

# === 第一層：💰 媽媽的庫存 (6欄) ===
c1, c2 = st.columns([3, 1])
with c1: st.subheader("💰 媽媽的庫存")
with c2: 
    if st.button("更新"): st.cache_data.clear(); st.rerun()

inv_list = get_list_from_cloud("inventory")
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
            if st.button("✖", key=f"d_{row['code']}"): update_cloud("remove", row['full_code'], "inventory"); st.rerun()

# === 第二層：👀 有興趣的股票 (6欄) ===
st.subheader("👀 有興趣的股票")
watch_list = get_list_from_cloud("watchlist")
if watch_list:
    df_w = get_stock_data(watch_list)
    cols2 = st.columns(6)
    for i, row in df_w.iterrows():
        with cols2[i%6]:
            st.markdown(f"""<div class="compact-card"><div class="compact-name">{row['name']}</div><div class="compact-price" style="color:{row['color']}">{row['price']}</div></div>""", unsafe_allow_html=True)
            if st.button("✖", key=f"dw_{row['code']}"): update_cloud("remove", row['full_code'], "watchlist"); st.rerun()
else:
    st.info("目前沒有觀察名單，請從左側新增。")

# === 第三層：🏆 市場熱門戰情室 ===
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

# === 第四層：📰 自動分類產業新聞 (瀑布流) ===
st.markdown("---")
st.subheader("🗞️ 產業新聞快遞 (AI 自動分類)")

# 抓取雲端 + 預設 RSS
custom_rss = get_list_from_cloud("news")
active_rss = custom_rss if custom_rss else []

with st.spinner("正在為媽媽搜尋各大報，過濾產業新聞..."):
    # 呼叫過濾函數
    news_buckets = fetch_and_filter_news(active_rss)

# 定義顯示順序
display_order = [
    "🤖 AI 與半導體", "🏗️ 鋼鐵與水泥", "🚗 汽車與供應鏈", 
    "🚢 航運與運輸", "⚡ 重電與綠能", "💰 金融與銀行", 
    "💊 生技與防疫", "🏠 營建與房產", "🌍 其他頭條"
]

for category in display_order:
    items = news_buckets.get(category, [])
    # 只有當該類別有新聞時才顯示，避免版面空白
    if items:
        st.markdown(f'<div class="news-category-header">{category}</div>', unsafe_allow_html=True)
        
        # 顯示該類別的新聞 (標題即連結)
        for n in items[:6]: # 每類最多顯示6則，避免滑不到底
            st.markdown(f"""
            <div class="news-item">
                <a href="{n['link']}" target="_blank" class="news-link-text">
                    {n['title']}
                </a>
                <div class="news-meta">
                    {n['src']} • {n['date']}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)
