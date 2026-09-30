import streamlit as st
import pandas as pd
import yfinance as yf
import datetime

# 設定網頁為寬版，並換上金庫的圖示
st.set_page_config(page_title="長期存股金庫", page_icon="🏦", layout="wide")

# ==========================================
# 🔒 終極防護：金庫密碼鎖
# ==========================================
def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.title("🔒 存股金庫 - 系統登入")
        pwd = st.text_input("請輸入金庫通行密碼：", type="password")
        if st.button("解鎖大門", type="primary"):
            if pwd == st.secrets["VAULT_PASSWORD"]:
                st.session_state["logged_in"] = True
                st.rerun() # 密碼正確，自動重整進入主畫面
            else:
                st.error("❌ 密碼錯誤，拒絕存取！")
        return False
    return True

# 執行攔截：如果密碼沒過，就強制停止執行後面的所有程式碼！
if not check_password():
    st.stop()

st.title("🏦 長期存股金庫 (Dividend Vault)")
st.write("---")

# ==========================================
# 1. 股利估價計算機
# ==========================================
st.header("🧮 1. 殖利率估價計算機")
st.markdown("輸入股票代號，系統將自動抓取近年股利，並推算 **便宜價(6%)**、**合理價(5%)** 與 **昂貴價(4%)**。")

col1, col2 = st.columns([1, 2])
with col1:
    ticker_input = st.text_input("請輸入台股代號 (記得加上 .TW，例如玉山金 2884.TW)：", "2884.TW")

if st.button("開始估價", type="primary"):
    with st.spinner(f"正在計算 {ticker_input} 的估價區間..."):
        try:
            stock = yf.Ticker(ticker_input)
            
            # 抓取歷史股利資料
            dividends = stock.dividends
            
            if not dividends.empty:
                # 篩選近 5 年的資料
                current_year = datetime.datetime.now().year
                recent_5_years = dividends[dividends.index.year >= current_year - 5]
                
                if not recent_5_years.empty:
                    # 台股通常一年發一次，我們取最近 5 次發放的平均值
                    recent_divs = recent_5_years.tail(5) 
                    avg_dividend = recent_divs.mean()
                    
                    # 核心估價公式
                    cheap_price = avg_dividend / 0.06
                    fair_price = avg_dividend / 0.05
                    exp_price = avg_dividend / 0.04
                    
                    # 抓取最新現價
                    current_price = stock.fast_info['last_price']
                    
                    # --- 顯示結果區塊 ---
                    st.subheader(f"📊 {ticker_input} 估價結果")
                    st.write(f"近 5 次平均配息：**{avg_dividend:.2f} 元** ｜ 最新現價：**{current_price:.2f} 元**")
                    
                    # 使用 3 個欄位漂亮地顯示價位
                    c1, c2, c3 = st.columns(3)
                    c1.success(f"🟢 便宜價 (6% 殖利率)\n\n### {cheap_price:.2f} 元")
                    c2.warning(f"🟡 合理價 (5% 殖利率)\n\n### {fair_price:.2f} 元")
                    c3.error(f"🔴 昂貴價 (4% 殖利率)\n\n### {exp_price:.2f} 元")
                    
                    # 自動判斷目前的位階
                    st.write("---")
                    if current_price <= cheap_price:
                        st.success(f"💡 戰術判定：目前現價 ({current_price:.2f}) 低於便宜價，是絕佳的長線買點！")
                    elif current_price <= fair_price:
                        st.info(f"💡 戰術判定：目前現價 ({current_price:.2f}) 落在便宜與合理價之間，可分批佈局。")
                    elif current_price <= exp_price:
                        st.warning(f"💡 戰術判定：目前現價 ({current_price:.2f}) 偏高，建議觀望或用定期定額。")
                    else:
                        st.error(f"💡 戰術判定：目前現價 ({current_price:.2f}) 高於昂貴價，千萬別當接盤俠！")
                        
                    # ==========================================
                    # 🌟 新增：近 10 年配息長條圖
                    # ==========================================
                    st.write("---")
                    st.subheader("📈 近 10 年現金股利發放趨勢")
                    
                    # 從一開始抓到的 dividends 裡，篩選出近 10 年的資料
                    recent_10_years = dividends[dividends.index.year > current_year - 10]
                    
                    if not recent_10_years.empty:
                        # 💡 關鍵巧思：將同年度的股利加總 (對付季配息、半年配息的股票)
                        yearly_divs = recent_10_years.groupby(recent_10_years.index.year).sum()
                        
                        # 直接召喚 Streamlit 的長條圖魔法
                        st.bar_chart(yearly_divs)
                    else:
                        st.info("沒有足夠的 10 年歷史配息資料可供繪製圖表。")
                        
                else:
                    st.warning("找不到近 5 年的股利資料。")
            else:
                st.warning("這檔股票似乎沒有穩定發放股利的紀錄！")
                
        except Exception as e:
            st.error(f"發生錯誤，請確認股票代號是否正確：{e}")
# ==========================================
# 2. 經典存股菜單 (自動報價版)
# ==========================================
st.write("---")
st.header("📋 2. 經典存股菜單 (不知道存什麼看這裡)")
st.markdown("不知道該存什麼？可以先從以下台股最經典的標的開始研究。點擊下方按鈕，機器人會為您抓取最新現價！")

# 建立預設的經典存股清單
default_stocks = [
    {"分類": "🏦 官股金融", "代號": "2886.TW", "名稱": "兆豐金", "特色": "獲利穩健、外幣放款霸主"},
    {"分類": "🏦 官股金融", "代號": "5880.TW", "名稱": "合庫金", "特色": "配息穩定、官股避風港"},
    {"分類": "🏦 民營金融", "代號": "2884.TW", "名稱": "玉山金", "特色": "散戶最愛、常配股票股利"},
    {"分類": "📡 防禦電信", "代號": "2412.TW", "名稱": "中華電", "特色": "超級防禦力、大盤暴跌也不怕"},
    {"分類": "🧺 高息 ETF", "代號": "0056.TW", "名稱": "元大高股息", "特色": "老牌高息 ETF、歷史填息紀錄佳"},
    {"分類": "🧺 高息 ETF", "代號": "00878.TW", "名稱": "國泰永續高息", "特色": "季配息設計、持股抗跌性強"}
]

# 加入一個更新報價的按鈕
if st.button("🔄 抓取最新現價"):
    with st.spinner("機器人正在連線抓取最新報價，請稍候..."):
        # 用迴圈一檔一檔抓取價格
        for stock in default_stocks:
            try:
                ticker = yf.Ticker(stock["代號"])
                # 抓取最新現價並四捨五入到小數點後兩位
                current_price = ticker.fast_info['last_price']
                stock["最新現價"] = round(current_price, 2)
            except:
                stock["最新現價"] = "抓取失敗"
        
        # 將清單轉換為表格
        df_menu = pd.DataFrame(default_stocks)
        # 重新排列欄位順序，把最新現價排在名稱後面
        df_menu = df_menu[["分類", "代號", "名稱", "最新現價", "特色"]]
        st.dataframe(df_menu, use_container_width=True, hide_index=True)
        st.success("✅ 報價更新完成！你可以將看順眼的代號複製到上方進行估價。")
else:
    # 如果還沒按按鈕，先顯示沒有現價的靜態版本
    df_menu = pd.DataFrame(default_stocks)
    st.dataframe(df_menu, use_container_width=True, hide_index=True)
