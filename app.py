import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
from deep_translator import GoogleTranslator
from datetime import datetime

# --- 1. 頁面設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海決策", initial_sidebar_state="collapsed")

# --- 2. 您的 GAS API (請務必確認這是您部署後的正確網址) ---
GAS_URL = "https://script.google.com/macros/library/d/1dOn69U1V5kqsde1kwg0SCdkU1ww694ahWUNhktSKZc08fi_wKiB1-IJI/1"

# --- 3. CSS 極致優化 (手機閱讀/緊湊版) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
    
    /* 緊湊型股票卡片 (手機優化) */
    .compact-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 8px 5px;
        text-align: center;
        background: white;
        margin-bottom: 5px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .compact-name { font-size: 18px !important; font-weight: 900; color: #333; margin: 0; line-height: 1.2;}
    .compact-code { font-size: 12px; color: #888; margin-bottom: 2px; }
    .compact-price { font-size: 22px !important; font-weight: bold; margin: 0; line-height: 1.2;}
    .compact-change { font-size: 14px !important; font-weight: bold; }
    
    /* 新聞連結樣式 */
    .news-link {
        text-decoration: none;
        color: #2E86C1;
        font-size: 18px; /* 標題字大一點方便點擊 */
        font-weight: 600;
        display: block;
        padding: 8px 0;
        border-bottom: 1px dashed #eee;
    }
    .news-meta { font-size: 12px; color: #999; }
    
    /* 分類標題 Bar */
    .category-header {
        background-color: #f0f2f6;
        padding: 5px 10px;
        border-left: 5px solid #2E86C1;
        font-weight: bold;
        margin-top: 10px;
    }

    /* 按鈕優化 */
    .stButton > button { font-size: 16px !important; padding: 5px 10px !important; }
    
    /* 調整手機上的欄位間距 */
    div[data-testid="column"] { padding: 0 5px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的股海顧問")
st.caption(f"手機閱讀最佳化版 | 更新時間：{datetime.now().strftime('%H:%M')}")

# --- 4. 數據與分類設定 ---

# (A) 新聞來源 (RSS 對應) - 為了能抓到標題，我們使用這些媒體的 RSS 源
DEFAULT_RSS = {
    "Yahoo 財經 (頭條)": "https://finance.yahoo.com/news/rssindex",
    "鉅亨網 (台股)": "https://news.cnyes.com/rss/cat/200",
    "聯合新聞網 (財經)": "https://money.udn.com/rssfeed/news/1001/5590/5591?ch=money",
    "MoneyDJ (即時)": "https://www.moneydj.com/rss/xa/mdj_xa_rss.xml",
    "華爾街日報 (中文)": "https://cn.wsj.com/zh-hans/rss",
}

# (B) 龐大的分類關鍵字庫 (依照您的需求建立對應)
# 邏輯：若新聞標題包含 List 中的關鍵字，就歸類到該 Key
CATEGORY_KEYWORDS = {
    "📊 上市類股": {
        "半導體/電子": ["台積電", "聯電", "聯發科", "晶圓", "IC", "半導體", "電子"],
        "航運/運輸": ["長榮", "陽明", "萬海", "航運", "散裝", "貨櫃", "航空", "華航", "長榮航"],
        "金融/保險": ["金控", "銀行", "壽險", "富邦", "國泰", "中信", "玉山", "升息", "降息"],
        "塑化/紡織": ["台塑", "南亞", "台化", "塑膠", "紡織", "儒鴻", "聚陽"],
        "生技/醫療": ["生技", "疫苗", "新藥", "藥證", "合一", "高端", "美時"],
        "傳產/水泥/鋼鐵": ["台泥", "亞泥", "中鋼", "鋼鐵", "水泥", "玻璃", "造紙"],
        "營建/資產": ["營建", "房地產", "房市", "遠雄", "興富發"],
        "觀光/餐飲": ["觀光", "餐飲", "王品", "晶華", "旅遊", "飯店"]
    },
    "💡 概念股": {
        "AI/機器人": ["AI", "人工智慧", "機器人", "伺服器", "廣達", "緯創", "輝達", "NVIDIA", "ChatGPT"],
        "蘋果概念股": ["蘋果", "Apple", "iPhone", "iPad", "Mac", "鴻海", "大立光", "Type-C"],
        "電動車/車用": ["電動車", "特斯拉", "Tesla", "車用", "電池", "充電樁", "裕隆", "鴻華"],
        "綠能/儲能": ["綠能", "風電", "太陽能", "儲能", "台電", "離岸風電"],
        "被動元件/矽晶圓": ["被動元件", "國巨", "華新科", "矽晶圓", "環球晶"],
        "元宇宙/VR": ["元宇宙", "VR", "AR", "宏達電", "威盛"]
    },
    "🏢 集團股": {
        "台積電集團": ["台積電", "精材", "創意", "世界先進"],
        "鴻海集團": ["鴻海", "鴻準", "群創", "業成", "樺漢"],
        "台塑集團": ["台塑", "南亞", "台化", "台塑化"],
        "長榮集團": ["長榮", "榮運", "長榮航", "長榮鋼"],
        "國泰/富邦集團": ["國泰金", "富邦金", "富邦媒"],
        "聯華神通/遠東": ["聯強", "神基", "遠東新", "遠傳"]
    }
}

# 漢化字典
STOCK_MAP = {
    "00878": "國泰永續高股息", "2301": "光寶科", "2308": "台達電", "2412": "中華電", 
    "2476": "鉅祥", "2884": "玉山金", "2892": "第一金", "3034": "聯詠", 
    "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "5880": "合庫金", "6191": "精成科", "6761": "穩得", "6788": "華景電", 
    "8926": "台汽電", "2330": "台積電", "2317": "鴻海", "2603": "長榮", 
    "2609": "陽明", "2615": "萬海", "2454": "聯發科"
}

# --- 5. 核心函數 ---

def get_stock_list_from_gas():
    try:
        response = requests.get(GAS_URL, params={"action": "read"}, timeout=5)
        return response.json()
    except:
        return []

def update_gas(action, code, price="0"):
    try:
        requests.get(GAS_URL, params={"action": action, "code": code, "price": price}, timeout=1)
        return True
    except: return False

def get_name(ticker):
    code = ticker.split(".")[0]
    return STOCK_MAP.get(code, code)

def get_stock_data(ticker_list):
    if not ticker_list: return pd.DataFrame()
    data = []
    # 批次抓取優化速度
    valid_tickers = [t for t in ticker_list if t.strip()]
    if not valid_tickers: return pd.DataFrame()

    try:
        # 使用 yfinance 一次抓取所有代碼會比迴圈快
        tickers_str = " ".join(valid_tickers)
        stocks = yf.Tickers(tickers_str)
        
        for t in valid_tickers:
            try:
                info = stocks.tickers[t].history(period="5d")
                if len(info) > 0:
                    price = info['Close'].iloc[-1]
                    prev = info['Close'].iloc[-2] if len(info) > 1 else price
                    change = price - prev
                    pct = (change / prev) * 100
                    
                    if pct >= 0:
                        color = "#e53935" # 紅
                        bg = "#ffebee"
                        sign = "▲"
                    else:
                        color = "#43a047" # 綠
                        bg = "#e8f5e9"
                        sign = "▼"
                    
                    data.append({
                        "name": get_name(t),
                        "code": t.replace(".TW", "").replace(".TWO", ""),
                        "full_code": t,
                        "price": f"{price:.0f}" if price > 10 else f"{price:.2f}", # 價格顯示優化
                        "change": f"{change:.2f}",
                        "pct": f"{pct:.2f}%",
                        "color": color,
                        "bg": bg,
                        "sign": sign
                    })
            except: continue
    except: pass
    
    return pd.DataFrame(data)

@st.cache_data(ttl=1800)
def fetch_and_classify_news(feed_urls):
    """抓取新聞並自動分類"""
    classified_news = {
        "📊 上市類股": {}, "💡 概念股": {}, "🏢 集團股": {}, "未分類": []
    }
    
    # 初始化子類別
    for main_cat, sub_cats in CATEGORY_KEYWORDS.items():
        for sub_cat in sub_cats:
            classified_news[main_cat][sub_cat] = []

    for src_name, url in feed_urls.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # 每家抓10則
                title = entry.title
                link = entry.link
                date = entry.get('published', '')[:16]
                
                # 自動翻譯標題 (若是英文源)
                if "Yahoo" in src_name or "WSJ" in src_name:
                     try:
                        if sum(1 for char in title if '\u4e00' <= char <= '\u9fff') < len(title)*0.3:
                            title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                     except: pass

                news_item = {"title": title, "link": link, "source": src_name, "date": date}
                
                # 開始分類
                matched = False
                for main_cat, sub_cats in CATEGORY_KEYWORDS.items():
                    for sub_cat, keywords in sub_cats.items():
                        # 檢查標題是否包含關鍵字
                        if any(kw in title for kw in keywords):
                            classified_news[main_cat][sub_cat].append(news_item)
                            matched = True
                
                if not matched:
                    classified_news["未分類"].append(news_item)
        except: continue
        
    return classified_news

# --- 6. 主畫面佈局 ---

# === 區塊 A: 媽媽的股票 (緊湊模式) ===
with st.container():
    c1, c2 = st.columns([3, 1])
    with c1: st.subheader("💰 媽媽的股票")
    with c2: 
        if st.button("🔄 更新"):
            st.cache_data.clear()
            st.rerun()

current_stocks = get_stock_list_from_gas()
if current_stocks:
    df = get_stock_data(current_stocks)
    if not df.empty:
        # 手機版面邏輯：使用 st.columns 自動流式排列
        # 我們設定每行顯示 2-3 個 (視螢幕寬度自動調整)
        cols = st.columns(3) 
        for i, row in df.iterrows():
            with cols[i % 3]:
                st.markdown(f"""
                <div class="compact-card" style="background-color: {row['bg']};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div class="compact-name">{row['name']}</div>
                        <div class="compact-code">{row['code']}</div>
                    </div>
                    <div style="margin-top:5px;">
                        <span class="compact-price" style="color:{row['color']}">{row['price']}</span>
                        <span class="compact-change" style="color:{row['color']}; margin-left:5px;">
                            {row['sign']} {row['change']} ({row['pct']})
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 為了美觀，移除按鈕做成小小的連結或放在設定區
                # 這裡為了媽媽方便，我們做一個簡單的移除Expander
                with st.expander("管理"):
                    if st.button("🗑️ 移除", key=f"rm_{row['code']}"):
                         update_gas("remove", row['full_code'])
                         st.rerun()

# === 區塊 B: 新聞來源設定 ===
with st.expander("📰 設定新聞來源 (點此展開)"):
    # 讓媽媽可以添加自訂連結
    user_rss = st.text_input("添加新聞 RSS 網址 (選填)", placeholder="貼上網址後按 Enter")
    
    # 建立目前要抓取的清單
    active_feeds = DEFAULT_RSS.copy()
    if user_rss:
        active_feeds["自訂來源"] = user_rss

    # 顯示所有來源的快速連結 (Launcher)
    st.markdown("**🌐 快速前往新聞網站 (點擊直接看)**")
    links_html = ""
    my_links = [
        ("Yahoo股市", "https://tw.stock.yahoo.com/"),
        ("PChome股市", "https://pchome.megatime.com.tw/"),
        ("鉅亨網", "https://www.cnyes.com/twstock"),
        ("聯合新聞網", "https://money.udn.com/money/index"),
        ("玩股網", "https://www.wantgoo.com/")
    ]
    for name, url in my_links:
        links_html += f'<a href="{url}" target="_blank" style="margin-right:10px; padding:5px 10px; background:#eee; border-radius:15px; text-decoration:none; color:#333; font-size:14px;">{name} ↗</a>'
    st.markdown(links_html, unsafe_allow_html=True)

# === 區塊 C: 分類新聞閱讀器 (手風琴模式) ===
st.markdown("---")
st.subheader("🗞️ 分類新聞快遞")

with st.spinner("正在為媽媽整理各大報新聞..."):
    news_data = fetch_and_classify_news(active_feeds)

# 使用 Tabs 分出三大類
tab1, tab2, tab3, tab4 = st.tabs(["📊 上市類股", "💡 概念股", "🏢 集團股", "🌍 綜合頭條"])

def render_news_group(category_key):
    # 取得該大類下的所有子分類
    sub_categories = news_data.get(category_key, {})
    
    # 如果完全沒新聞
    has_news = False
    
    for sub_cat, items in sub_categories.items():
        if items: # 只有當該分類有新聞時才顯示
            has_news = True
            # 使用 Expander (可折疊)，預設收起，點擊才打開
            with st.expander(f"{sub_cat} ({len(items)} 則)"):
                for n in items:
                    st.markdown(f"""
                    <a href="{n['link']}" target="_blank" class="news-link">
                        {n['title']}
                    </a>
                    <div class="news-meta">{n['source']} | {n['date']}</div>
                    """, unsafe_allow_html=True)
    
    if not has_news:
        st.info("目前這個類別沒有抓到相關關鍵字的新聞。")

with tab1:
    render_news_group("📊 上市類股")

with tab2:
    render_news_group("💡 概念股")

with tab3:
    render_news_group("🏢 集團股")

with tab4:
    # 顯示未分類新聞 (也就是綜合新聞)
    general_news = news_data.get("未分類", [])
    if general_news:
        for n in general_news[:20]: # 只顯示前20則
            st.markdown(f"""
            <a href="{n['link']}" target="_blank" class="news-link">
                {n['title']}
            </a>
            <div class="news-meta">{n['source']} | {n['date']}</div>
            """, unsafe_allow_html=True)

# --- 側邊欄新增股票功能 ---
with st.sidebar:
    st.header("➕ 新增股票")
    new_code = st.text_input("代碼", placeholder="如 2330.TW")
    if st.button("加入"):
        update_gas("add", new_code.upper())
        st.success("已加入")
        st.rerun()
