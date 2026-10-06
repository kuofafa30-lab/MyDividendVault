import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os

# 設定網頁為寬版，並換上圖示
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
    st.sidebar.subheader("📋 存股雷達清單")
    
    ticker_list = ["2912.TW", "5903.TW", "2886.TW", "2330.TW", "00878.TW"]
    if os.path.exists("golden_list.csv"):
        df_golden = pd.read_csv("golden_list.csv")
        if "狀態" not in df_golden.columns:
            st.sidebar.success(f"🔥 雷達本週發現 {len(df_golden)} 檔特價股！")
            ticker_list = list(set(ticker_list + df_golden['股票代號'].tolist()))
        else:
            st.sidebar.info("本週無特價股，顯示自選清單。")
            
    selected_ticker = st.sidebar.selectbox("🔍 點擊切換分析標的：", ticker_list)

    st.header(f"🏦 {selected_ticker} 戰情看板")
    tab1, tab2, tab3 = st.tabs(["📊 終端看板 (雙效估價)", "🧠 策略回測 (定期不定額)", "📋 綜合雷達 (菜單與名單)"])
    
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

                with tab2:
                    st.markdown("不想無腦扣款？以過去 5 年真實股價對決「憨憨存」與「聰明存」。")
                    base_amt = st.number_input("每月基準扣款 (元)", min_value=1000, value=10000, step=1000, key="dca_amt")
                    
                    if st.button(f"🚀 啟動 {selected_ticker} 5 年真實回測", type="primary"):
                        monthly_data = hist['Close'].resample('ME').last().to_frame()
                        monthly_data['6MA'] = monthly_data['Close'].rolling(window=6).mean()
                        monthly_data = monthly_data.dropna()
                        
                        fixed_shares, fixed_cost, smart_shares, smart_cost = 0, 0, 0, 0
                        
                        for date, row in monthly_data.iterrows():
                            price, ma6 = row['Close'], row['6MA']
                            fixed_shares += base_amt / price
                            fixed_cost += base_amt
                            
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
# 系統 B：波段戰情室 (短期動能)
# ==========================================
elif system_menu == "📈 波段戰情室 (短期動能)":
    st.title("📈 波段戰情室 (Swing Trading)")
    
    # ----------------------------------------
    # [區塊 1] 戰術背包：真實損益監控
    # ----------------------------------------
    backpack_file = "tactical_backpack.csv"
    
    if os.path.exists(backpack_file):
        df_bp = pd.read_csv(backpack_file)
        # 自動防呆升級：如果舊檔案沒有股數欄位，預設補上 1000 股
        if "股數" not in df_bp.columns:
            df_bp["股數"] = 1000
    else:
        df_bp = pd.DataFrame(columns=["代號", "買進成本", "股數"])

    st.subheader("🎒 戰術背包 (即時損益監控)")
    col_add, col_close = st.columns(2)
    
    with col_add:
        with st.expander("➕ 新增實際持股 (買進後填寫)", expanded=False):
            new_ticker = st.text_input("股票代號 (記得加 .TW，如 3008.TW)：", key="add_ticker")
            new_cost = st.number_input("實際成交均價：", min_value=0.0, step=1.0, format="%.2f")
            # 🌟 新增的股數欄位！
            new_qty = st.number_input("持有股數 (1張 = 1000)：", min_value=1, value=1000, step=1)
            
            if st.button("📥 寫入背包"):
                if new_ticker:
                    if new_ticker in df_bp["代號"].values:
                        st.warning("這檔股票已經在背包裡了！")
                    else:
                        new_row = pd.DataFrame({"代號": [new_ticker], "買進成本": [new_cost], "股數": [new_qty]})
                        df_bp = pd.concat([df_bp, new_row], ignore_index=True)
                        df_bp.to_csv(backpack_file, index=False, encoding="utf-8-sig")
                        st.success(f"{new_ticker} ({new_qty}股) 已成功入庫！")
                        st.rerun()

    with col_close:
        with st.expander("🧨 執行平倉 (賣出後移除)", expanded=False):
            if not df_bp.empty:
                close_ticker = st.selectbox("選擇要平倉的標的：", df_bp["代號"].tolist())
                if st.button("💥 確認平倉"):
                    df_bp = df_bp[df_bp["代號"] != close_ticker]
                    df_bp.to_csv(backpack_file, index=False, encoding="utf-8-sig")
                    st.success(f"{close_ticker} 已平倉移除！")
                    st.rerun()
            else:
                st.info("目前背包空空如也，無須平倉。")

    # 即時監控面板
    if not df_bp.empty:
        bp_results = []
        with st.spinner("正在連線交易所抓取庫存即時報價..."):
            for index, row in df_bp.iterrows():
                try:
                    ticker = row["代號"]
                    cost = float(row["買進成本"])
                    qty = int(row.get("股數", 1000))
                    
                    stock = yf.Ticker(ticker)
                    current_price = stock.fast_info['last_price']
                    
                    # 計算帳面損益額 (台幣) 與 報酬率 (%)
                    pnl_pct = ((current_price / cost) - 1) * 100
                    pnl_amt = (current_price - cost) * qty
                    
                    hist = stock.history(period="1mo")
                    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else cost * 0.95
                    
                    bp_results.append({
                        "代號": ticker,
                        "股數": f"{qty:,}",
                        "買進均價": f"{cost:.2f}",
                        "最新現價": f"{current_price:.2f}",
                        "未實現損益(元)": f"{pnl_amt:+,.0f}",  # 顯示正負號的台幣損益
                        "報酬率(%)": f"{pnl_pct:+.2f}%",
                        "防守點位(月線)": f"{ma20:.2f}"
                    })
                except Exception as e:
                    bp_results.append({"代號": ticker, "買進均價": cost, "最新現價": "報價失敗"})
        
        st.dataframe(pd.DataFrame(bp_results), use_container_width=True, hide_index=True)
    else:
        st.info("您的戰術背包目前沒有任何庫存，請等待雷達訊號！")

    st.write("---")

    # ----------------------------------------
    # [區塊 2] 狙擊雷達：爆量突破掃描
    # ----------------------------------------
    st.subheader("🚀 狙擊雷達掃描")
    st.markdown("使用**「站上 20 日月線」**與**「爆量 (成交量 > 月均量 2 倍)」**來捕捉即將發動的飆股。")

    default_tickers = "2330.TW, 2317.TW, 2454.TW, 3231.TW, 2382.TW, 2603.TW, 3008.TW"
    user_tickers = st.text_input("🎯 輸入觀察清單 (請以逗號分隔)：", default_tickers)

    if st.button("啟動爆量突破雷達", type="primary"):
        ticker_list = [t.strip() for t in user_tickers.split(",") if t.strip()]
        sniper_results = []

        with st.spinner("雷達掃描中，正在比對量價型態..."):
            for ticker in ticker_list:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="3mo")

                    if len(hist) > 20:
                        hist['20MA'] = hist['Close'].rolling(window=20).mean()
                        hist['20V_MA'] = hist['Volume'].rolling(window=20).mean()

                        latest = hist.iloc[-1]
                        current_price = latest['Close']
                        current_open = latest['Open']
                        current_vol = latest['Volume']
                        ma20 = latest['20MA']
                        vol_ma20 = latest['20V_MA']

                        is_breakout = current_price > ma20
                        is_volume_surge = current_vol > (vol_ma20 * 2)
                        is_red_candle = current_price > current_open

                        if is_breakout and is_volume_surge and is_red_candle:
                            status = "🔥 爆量突破 (符合)"
                        else:
                            status = "⏳ 潛伏整理"

                        sniper_results.append({
                            "股票代號": ticker,
                            "最新收盤價": round(current_price, 2),
                            "20日月線": round(ma20, 2),
                            "今日成交量": f"{int(current_vol / 1000):,} 張",
                            "量能倍數": f"{current_vol / vol_ma20:.1f} 倍",
                            "狙擊判定": status
                        })
                except Exception as e:
                    pass 

        if sniper_results:
            df_results = pd.DataFrame(sniper_results)
            df_results = df_results.sort_values(by="狙擊判定", ascending=False)
            
            targets = df_results[df_results['狙擊判定'] == "🔥 爆量突破 (符合)"]
            if len(targets) > 0:
                st.success(f"🚨 警報！發現 {len(targets)} 檔具備飆股特徵的標的！")
            else:
                st.info("目前清單中尚未出現符合特徵的標的。")
                
            st.dataframe(df_results, use_container_width=True, hide_index=True)
