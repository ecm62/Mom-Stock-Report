import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
import requests
import json
from deep_translator import GoogleTranslator
from datetime import datetime

# --- 1. 基礎設定 ---
st.set_page_config(layout="wide", page_title="阿美的股海決策報")

# --- 2. 您的 API 地址 (請換成您 Apps Script 部署後的網址) ---
# 結尾應該是 /exec
GAS_URL = "https://script.google.com/macros/s/XXXXXXXXXXXXXXXXXXXX/exec" 

# --- 3. CSS 優化 (長輩模式) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: "Microsoft JhengHei", sans-serif; }
    .stock-card { border: 2px solid #eee; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 15px; background: white; box-shadow: 3px 3px 10px rgba(0,0,0,0.1); }
    .stock-name { font-size: 26px !important; font-weight: 900; color: #333; }
    .stock-price { font-size: 36px !important; font-weight: bold; }
    .action-btn { margin-top: 10px; }
    
    /* 加大按鈕 */
    .stButton > button { font-size: 20px !important; border-radius: 10px !important; height: 50px !important; width: 100% !important; }
    .remove-btn > button { background-color: #ffebee !important; color: #c62828 !important; border: 1px solid #ffcdd2 !important; }
    .add-btn > button { background-color: #e8f5e9 !important; color: #2e7d32 !important; border: 1px solid #c8e6c9 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的投資顧問")
st.caption(f"自動同步雲端資料庫 | 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 4. 核心與連線函數 ---

def get_stock_list():
    """從 GAS 讀取清單"""
    try:
        response = requests.get(GAS_URL, params={"action": "read"})
        return response.json()
    except:
        return []

def update_stock_list(action, code, price="0"):
    """發送指令給 GAS (新增或移除)"""
    try:
        requests.get(GAS_URL, params={"action": action, "code": code, "price": price})
        return True
    except:
        return False

# 漢化與抓價函數 (維持不變)
STOCK_MAP = {
    "00878": "國泰永續高股息", "2301": "光寶科", "2308": "台達電", "2412": "中華電", 
    "2476": "鉅祥", "2884": "玉山金", "2892": "第一金", "3034": "聯詠", 
    "3035": "智原", "3363": "上詮", "3715": "定穎投控", "4772": "台特化", 
    "5880": "合庫金", "6191": "精成科", "6761": "穩得", "6788": "華景電", 
    "8926": "台汽電", "2330": "台積電", "2317": "鴻海", "2603": "長榮", "2609": "陽明"
}

def get_name(ticker):
    code = ticker.split(".")[0]
    return STOCK_MAP.get(code, code)

def get_stock_data(ticker_list):
    if not ticker_list: return pd.DataFrame()
    data = []
    for t in ticker_list:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="5d")
            if len(hist) > 0:
                price = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else price
                change = price - prev
                pct = (change / prev) * 100
                
                if pct >= 0:
                    status_text = "🔺 漲"
                    color = "#E74C3C" 
                    bg = "#FFF5F5"
                else:
                    status_text = "🔻 跌"
                    color = "#27AE60"
                    bg = "#F0FFF4"
                
                data.append({
                    "name": get_name(t), "code": t.replace(".TW", "").replace(".TWO", ""),
                    "full_code": t,
                    "price": f"{price:.2f}", "raw_price": price,
                    "change": f"{change:.2f}", "pct": f"{pct:.2f}%", 
                    "color": color, "status": status_text, "bg": bg
                })
        except: continue
    return pd.DataFrame(data)

# --- 5. 側邊欄：媽媽的操作區 ---
with st.sidebar:
    st.header("🛠️ 股票管理中心")
    
    # === 新增股票區 ===
    with st.form("add_stock_form", clear_on_submit=True):
        st.subheader("➕ 新增股票")
        new_stock = st.text_input("輸入代碼 (例如 2330.TW)", placeholder="記得加 .TW 或 .TWO")
        submitted = st.form_submit_button("加入清單", type="primary")
        
        if submitted and new_stock:
            # 為了記錄歷史股價，我們先抓一次報價
            try:
                temp_tick = yf.Ticker(new_stock.upper())
                current_p = temp_tick.history(period="1d")['Close'].iloc[-1]
            except:
                current_p = 0
            
            # 發送指令
            with st.spinner("正在寫入雲端..."):
                update_stock_list("add", new_stock.upper(), str(current_p))
            st.success(f"已加入 {new_stock}")
            st.rerun() # 重新整理畫面

    st.markdown("---")
    if st.button("🔄 立即更新資料"):
        st.cache_data.clear()
        st.rerun()

# --- 6. 主畫面顯示 ---
st.header("1️⃣ 媽媽的股票庫存")

# 從 GAS 讀取最新清單
current_stocks = get_stock_list()

if not current_stocks:
    st.info("目前清單是空的，請在左側新增股票。")
else:
    df = get_stock_data(current_stocks)
    if not df.empty:
        # 使用直式排列，每張卡片下面都有移除按鈕
        # 為了讓移除按鈕能對應到正確股票，我們不使用 columns，改用 container
        
        # 電腦版改為 3欄
        cols = st.columns(3)
        for i, row in df.iterrows():
            with cols[i % 3]:
                # 顯示股票卡片
                st.markdown(f"""
                <div class="stock-card" style="background-color: {row['bg']};">
                    <div class="stock-name">{row['name']}</div>
                    <div class="stock-code">{row['code']}</div>
                    <div class="stock-price" style="color:{row['color']}">{row['price']}</div>
                    <div style="color:{row['color']}; font-size: 20px; font-weight:bold;">
                        {row['status']} {row['change']} ({row['pct']})
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 移除按鈕 (每一個股票都有自己的按鈕)
                # 使用 unique key 避免衝突
                if st.button(f"🗑️ 移除 {row['name']}", key=f"del_{row['code']}", help="點擊後將從清單移除並記錄賣出時間"):
                    with st.spinner("正在移除並記錄歷史..."):
                        update_stock_list("remove", row['full_code'], str(row['raw_price']))
                    st.success(f"已移除 {row['name']}")
                    st.rerun()

st.markdown("---")
# (新聞區塊省略，請保留原有的新聞程式碼)
st.header("2️⃣ 產業新聞快遞")
# ... 請保留之前的新聞區塊代碼 ...
RSS_SOURCES = {"鉅亨網": "https://news.cnyes.com/rss/cat/200", "Yahoo": "https://finance.yahoo.com/news/rssindex"}
@st.cache_data(ttl=1800)
def get_news_data(feeds):
    news_db = {'semicon':[], 'shipping':[], 'finance':[], 'general':[]}
    for src in feeds:
        url = RSS_SOURCES[src]
        feed = feedparser.parse(url)
        need_trans = "Yahoo" in src
        for entry in feed.entries[:5]:
            title = entry.title
            if need_trans: 
                try: 
                    if sum(1 for char in title if '\u4e00' <= char <= '\u9fff') < len(title)*0.3:
                         title = GoogleTranslator(source='auto', target='zh-TW').translate(title)
                except: pass
            
            # 簡易分類
            t = title.lower()
            cat = "general"
            if any(x in t for x in ['台積', '半導體', 'ai']): cat = "semicon"
            elif any(x in t for x in ['航運', '長榮']): cat = "shipping"
            elif any(x in t for x in ['金融', '銀行']): cat = "finance"
            
            news_db[cat].append({"title":title, "link":entry.link, "src":src, "date":entry.get('published','')[:16]})
    return news_db

news_data = get_news_data(list(RSS_SOURCES.keys()))
cats = [("🔥 電子與半導體", "semicon"), ("🚢 航運與傳產", "shipping"), ("💰 金融與銀行", "finance"), ("🌍 全球熱門頭條", "general")]
for label, key in cats:
    if news_data[key]:
        st.subheader(label)
        for n in news_data[key]:
            st.markdown(f'<div class="news-card"><a href="{n["link"]}" target="_blank" class="news-title">{n["title"]}</a><div style="font-size:16px; color:#666; margin-top:8px;">{n["src"]} | {n["date"]}</div></div>', unsafe_allow_html=True)
