import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
from deep_translator import GoogleTranslator
from datetime import datetime

# --- 設定頁面 ---
st.set_page_config(layout="wide", page_title="阿美的股海決策報")

# --- CSS 優化 (加大字體) ---
st.markdown("""
    <style>
    .big-font { font-size:30px !important; font-weight:bold; color: #E74C3C; }
    .medium-font { font-size:24px !important; font-weight:bold; }
    .news-title { font-size:20px !important; font-weight:bold; color: #2E86C1; text-decoration: none; }
    .news-box { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("👵 阿美的股海決策顧問")
st.markdown(f"**更新時間：** {datetime.now().strftime('%Y-%m-%d %H:%M')} (請按右上角選單的 Rerun 更新)")

# --- 側邊欄參數 ---
st.sidebar.header("⚙️ 設定區")
my_stocks_str = st.sidebar.text_area("已持有股票 (代碼用逗號隔開)", "2330.TW, 2317.TW, 00878.TW, 2412.TW")
watch_stocks_str = st.sidebar.text_area("觀察名單", "2603.TW, 1101.TW, 1301.TW, 2618.TW")

# --- 核心函數 ---

@st.cache_data(ttl=3600)
def translate_to_chinese(text):
    """將英文翻譯成繁體中文 (快取1小時)"""
    try:
        # 如果是中文就不用翻
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return text
        return GoogleTranslator(source='auto', target='zh-TW').translate(text)
    except:
        return text

def get_stock_data(tickers_input):
    """抓取股價與漲跌"""
    if not tickers_input: return pd.DataFrame()
    ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
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
                
                # 簡單狀態判斷
                state = "🔴 大漲" if pct >= 3 else ("🟢 大跌" if pct <= -3 else "⚪ 盤整")
                if pct > 0: color_style = 'color: red;'
                elif pct < 0: color_style = 'color: green;'
                else: color_style = 'color: gray;'

                data.append({
                    "代碼": t.replace(".TW", ""),
                    "現價": f"{price:.2f}",
                    "漲跌": f"{change:.2f}",
                    "幅度%": f"{pct:.2f}%",
                    "狀態": state,
                    "raw_pct": pct # 用於排序
                })
        except: continue
    return pd.DataFrame(data)

def get_news(url, count=5, need_trans=False):
    """抓取並處理新聞"""
    feed = feedparser.parse(url)
    news_list = []
    for entry in feed.entries[:count]:
        title = entry.title
        if need_trans:
            title = translate_to_chinese(title)
        news_list.append({"title": title, "link": entry.link, "date": entry.get('published', '')[:16]})
    return news_list

# --- 介面佈局 ---

# 1. 持股與觀察區
col1, col2 = st.columns(2)

with col1:
    st.markdown('<p class="medium-font">💰 媽媽的持股</p>', unsafe_allow_html=True)
    df_own = get_stock_data(my_stocks_str)
    if not df_own.empty:
        # 使用 Styler 讓漲跌變色
        st.dataframe(df_own.drop(columns=['raw_pct']), use_container_width=True, hide_index=True)

with col2:
    st.markdown('<p class="medium-font">👀 重點觀察</p>', unsafe_allow_html=True)
    df_watch = get_stock_data(watch_stocks_str)
    if not df_watch.empty:
        st.dataframe(df_watch.drop(columns=['raw_pct']), use_container_width=True, hide_index=True)

st.divider()

# 2. 產業排行榜
st.markdown("## 🏆 產業龍頭漲跌排行")
SECTORS = {
    "水泥/傳產": ["1101.TW", "1102.TW", "2105.TW"],
    "塑化": ["1301.TW", "1303.TW", "1326.TW"],
    "航運": ["2603.TW", "2609.TW", "2615.TW"],
    "電子/AI": ["2330.TW", "2317.TW", "2454.TW", "3231.TW", "2382.TW"],
    "金融": ["2881.TW", "2882.TW", "2891.TW"]
}

# 抓取所有產業股
all_sector_tickers = ",".join([",".join(v) for v in SECTORS.values()])
df_sector = get_stock_data(all_sector_tickers)

if not df_sector.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.error("🔥 強勢股 (漲最多)")
        top_gain = df_sector.sort_values(by="raw_pct", ascending=False).head(5)
        st.table(top_gain[['代碼', '現價', '幅度%', '狀態']])
    with c2:
        st.success("🧊 弱勢股 (跌最多)")
        top_loss = df_sector.sort_values(by="raw_pct", ascending=True).head(5)
        st.table(top_loss[['代碼', '現價', '幅度%', '狀態']])

st.divider()

# 3. 新聞區
st.markdown("## 📰 全球財經新聞 (中譯版)")

tab1, tab2, tab3 = st.tabs(["🇹🇼 台灣焦點", "🇺🇸 美國財經", "🤖 AI 科技"])

with tab1:
    news = get_news("https://news.cnyes.com/rss/cat/200", need_trans=False)
    for n in news:
        st.markdown(f'<div class="news-box"><a href="{n["link"]}" target="_blank" class="news-title">{n["title"]}</a><br><small>{n["date"]}</small></div>', unsafe_allow_html=True)

with tab2:
    with st.spinner("正在翻譯美國新聞...請稍等"):
        news = get_news("https://finance.yahoo.com/news/rssindex", need_trans=True)
        for n in news:
            st.markdown(f'<div class="news-box"><a href="{n["link"]}" target="_blank" class="news-title">{n["title"]}</a><br><small>{n["date"]}</small></div>', unsafe_allow_html=True)

with tab3:
    with st.spinner("正在翻譯科技新聞...請稍等"):
        news = get_news("https://techcrunch.com/feed/", need_trans=True)
        for n in news:
            st.markdown(f'<div class="news-box"><a href="{n["link"]}" target="_blank" class="news-title">{n["title"]}</a><br><small>{n["date"]}</small></div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("Produced by Dr. Yang for Mom")
