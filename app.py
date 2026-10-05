import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os

# 設定網頁為寬版，並換上金庫的圖示
st.set_page_config(page_title="量化交易終端機", page_icon="👨‍💻", layout="wide")

# ==========================================
# 🔒 終極防護：金庫密碼鎖
# ==========================================
def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.title("🔒 量化終端機 - 系統登入")
        pwd = st.text_input("請輸入通行密碼：", type="password")
        if st.button("解鎖大門", type="primary"):
            if pwd == st.secrets["VAULT_PASSWORD"]:
                st.session_state["logged_in"] = True
                st.rerun() 
            else:
                st.error("❌ 密碼錯誤，拒絕存取！")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# 🧭 左側邊欄：總司令部導覽選單
# ==========================================
st.sidebar.title("👨‍💻 量化交易終端機")
system_menu = st.sidebar.radio(
    "切換監控系統：",
    ["🏦 存股金庫 (長期價值)", "📈 波段戰情室 (短期動能)"]
)
st.sidebar.write("---")

# ==========================================
# 系統 A：存股金庫 (專業終端機版面)
# ==========================================
if system_menu == "🏦 存股金庫 (長期價值)":
    
    # --- 1. 左側邊欄：雷達清單與選股器 ---
    st.sidebar.subheader("📋 存股雷達清單")
    
    # 讀取黃金名單
    ticker_list = ["2912.TW", "5903.TW", "2886.TW", "2330.TW", "00878.TW"]
    if os.path.exists("golden_list.csv"):
        df_golden = pd.read_csv("golden_list.csv")
        if "狀態" not in df_golden.columns:
            st.sidebar.success(f"🔥 雷達本週發現 {len(df_golden)} 檔特價股！")
            # 將黃金名單加入選單，並移除重複項
            ticker_list = list(set(ticker_list + df_golden['股票代號'].tolist()))
        else:
            st.sidebar.info("本週無特價股，顯示自選清單。")
            
    # 左側下拉選單：只要在這裡選，右邊的所有圖表都會跟著變！
    selected_ticker = st.sidebar.selectbox("🔍 點擊切換分析標的：", ticker_list)

    # --- 2. 右側主畫面：建立三大分頁 ---
    st.header(f"🏦 {selected_ticker} 戰情看板")
    tab1, tab2, tab3 = st.tabs(["📊 終端看板 (雙效估價)", "🧠 策略回測 (定期不定額)", "📋 綜合雷達 (菜單與名單)"])
    
    # 預先抓取共用資料
    with st.spinner(f"正在載入 {selected_ticker} 終端機數據..."):
        try:
            stock = yf.Ticker(selected_ticker)
            hist = stock.history(period="5y")
            divs = stock.dividends
            if not hist.empty:
                current_price = stock.fast_info['last_price']
                monthly_price = hist['Close'].resample('ME').last()
                df_river = pd.DataFrame({'現價': monthly_price})
                df_river['年份'] = df_river.index.year
                
                # 計算配息與殖利率
                current_year = datetime.datetime.now().year
                recent_5_years_div = divs[divs.index.year >= current_year - 5]
                avg_div = recent_5_years_div.tail(5).mean() if not divs.empty else 0
                current_yield = (avg_div / current_price) * 100 if avg_div > 0 else 0
                
                if not divs.empty:
                    yearly_divs = divs.groupby(divs.index.year).sum()
                    df_river['當年配息'] = df_river['年份'].map(yearly_divs).ffill()
                    df_river = df_river.dropna()
                    df_river['殖利率(%)'] = (df_river['當年配息'] / df_river['現價']) * 100
                    hist_avg_yield = df_river['殖利率(%)'].mean()
                    df_river['歷史均線'] = hist_avg_yield
                else:
                    hist_avg_yield = 0

                # ----------------------------------------
                # [分頁 1] 終端看板：河流圖與估價面板
                # ----------------------------------------
                with tab1:
                    if not divs.empty:
                        st.line_chart(df_river[['殖利率(%)', '歷史均線']], height=350)
                    else:
                        st.warning("無配息資料，僅顯示股價走勢。")
                        st.line_chart(hist['Close'], height=350)
                        
                    st.write("---")
                    st.subheader("📊 核心財務指標")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("最新收盤價", f"{current_price:.2f} 元")
                    col2.metric("潛在殖利率", f"{current_yield:.2f} %", 
                                f"{current_yield - hist_avg_yield:.2f}% (距歷史均值)" if not divs.empty else "")
                    col3.metric("近 5 年平均配息", f"{avg_div:.2f} 元")
                    
                    if not divs.empty and current_yield > hist_avg_yield:
                        col4.metric("系統判定狀態", "🟢 相對特價區")
                    else:
                        col4.metric("系統判定狀態", "🟡 估值偏高")
                        
                    st.markdown("**(傳統 654 絕對估價參考)**")
                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric("便宜價 (6%)", f"{(avg_div / 0.06):.2f}" if avg_div > 0 else "-")
                    col_b.metric("合理價 (5%)", f"{(avg_div / 0.05):.2f}" if avg_div > 0 else "-")
                    col_c.metric("昂貴價 (4%)", f"{(avg_div / 0.04):.2f}" if avg_div > 0 else "-")

                # ----------------------------------------
                # [分頁 2] 策略回測：定期不定額
                # ----------------------------------------
                with tab2:
                    st.markdown("不想無腦扣款？以過去 5 年真實股價對決「憨憨存」與「聰明存」。")
                    # 預設載入左側選單的股票
                    base_amt = st.number_input("每月基準扣款 (元)", min_value=1000, value=10000, step=1000, key="dca_amt")
                    
                    if st.button(f"🚀 啟動 {selected_ticker} 5 年真實回測", type="primary"):
                        monthly_data = hist['Close'].resample('ME').last().to_frame()
                        monthly_data['6MA'] = monthly_data['Close'].rolling(window=6).mean()
                        monthly_data = monthly_data.dropna()
                        
                        fixed_shares, fixed_cost, smart_shares, smart_cost = 0, 0, 0, 0
                        
                        for date, row in monthly_data.iterrows():
                            price, ma6 = row['Close'], row['6MA']
                            
                            # 定期定額
                            fixed_shares += base_amt / price
                            fixed_cost += base_amt
                            
                            # 定期不定額
                            invest = base_amt * 2 if price < ma6 * 0.95 else (base_amt * 0.5 if price > ma6 * 1.05 else base_amt)
                            smart_shares += invest / price
                            smart_cost += invest
                        
                        final_price = monthly_data['Close'].iloc[-1]
                        fixed_roi = ((fixed_shares * final_price) / fixed_cost - 1) * 100
                        smart_roi = ((smart_shares * final_price) / smart_cost - 1) * 100
                        
                        res_col1, res_col2 = st.columns(2)
                        with res_col1:
                            st.info("🤖 策略一：憨憨存 (定期定額)")
                            st.metric("最終總市值", f"${int(fixed_shares * final_price):,}", f"{fixed_roi:.2f}%")
                        with res_col2:
                            st.success("🧠 策略二：聰明存 (價低買多)")
                            st.metric("最終總市值", f"${int(smart_shares * final_price):,}", f"{smart_roi:.2f}%")

                # ----------------------------------------
                # [分頁 3] 綜合雷達：經典菜單與黃金名單
                # ----------------------------------------
                with tab3:
                    st.subheader("🚨 本週雷達鎖定：黃金名單")
                    if os.path.exists("golden_list.csv") and "狀態" not in df_golden.columns:
                        st.dataframe(df_golden, use_container_width=True, hide_index=True)
                    else:
                        st.info("目前市場無特價標的。")
                        
                    st.write("---")
                    st.subheader("📋 經典存股菜單")
                    default_stocks = [
                        {"代號": "2886.TW", "名稱": "兆豐金", "特色": "獲利穩健、外幣放款霸主"},
                        {"代號": "2412.TW", "名稱": "中華電", "特色": "超級防禦力、抗跌性強"},
                        {"代號": "00878.TW", "名稱": "國泰永續高息", "特色": "季配息設計、持股抗跌"}
                    ]
                    st.dataframe(pd.DataFrame(default_stocks), use_container_width=True, hide_index=True)

            else:
                st.warning("查無歷史資料，請確認代號。")
        except Exception as e:
            st.error(f"發生錯誤：{e}")

# ==========================================
# 系統 B：波段戰情室
# ==========================================
elif system_menu == "📈 波段戰情室 (短期動能)":
    st.title("📈 波段戰情室 (Swing Trading)")
    st.markdown("這裡是波段交易的版面，未來可將您寫好的均線突破策略貼在這裡。")
