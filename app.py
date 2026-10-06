import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os
import plotly.graph_objects as go  # 🌟 新增的專業 K 線圖套件

# 設定網頁為寬版
st.set_page_config(page_title="量化交易終端機", page_icon="👨‍💻", layout="wide")

# ==========================================
# 🔒 金庫密碼鎖
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
# 🧭 輔助工具箱
# ==========================================
# 1. 自動補上 .TW 的防呆函數
def auto_tw(ticker):
    t = str(ticker).strip().upper()
    if not t: return ""
    if not t.endswith(".TW") and not t.endswith(".TWO"):
        return f"{t}.TW"
    return t

# 2. 常見台股中文名稱對照表 (因 yfinance 預設回傳英文，先用字典對應)
TW_NAMES = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", 
    "3008.TW": "大立光", "2382.TW": "廣達", "3231.TW": "緯創",
    "2603.TW": "長榮", "2912.TW": "統一超", "5903.TW": "全家",
    "2886.TW": "兆豐金", "0050.TW": "元大台灣50", "00878.TW": "國泰永續高息"
}

# ==========================================
# 🧭 左側邊欄：總司令部導覽
# ==========================================
st.sidebar.title("👨‍💻 量化交易終端機")
system_menu = st.sidebar.radio(
    "切換監控系統：",
    ["🏦 存股金庫 (長期價值)", "📈 波段戰情室 (短期動能)"]
)
st.sidebar.write("---")

# =========================================================================
# 系統 A：存股金庫 (維持原樣)
# =========================================================================
if system_menu == "🏦 存股金庫 (長期價值)":
    st.sidebar.subheader("📋 存股雷達清單")
    ticker_list = ["2912", "5903", "2886", "2330", "00878"] # 把預設代號也改乾淨
    
    if os.path.exists("golden_list.csv"):
        df_golden = pd.read_csv("golden_list.csv")
        if "狀態" not in df_golden.columns:
            st.sidebar.success(f"🔥 雷達本週發現 {len(df_golden)} 檔特價股！")
            # 把黃金名單的 .TW 去掉顯示比較乾淨
            golden_raw = [t.replace(".TW", "") for t in df_golden['股票代號'].tolist()]
            ticker_list = list(set(ticker_list + golden_raw))
        else:
            st.sidebar.info("本週無特價股，顯示自選清單。")
            
    raw_selected = st.sidebar.selectbox("🔍 點擊切換分析標的：", ticker_list)
    selected_ticker = auto_tw(raw_selected)

    st.header(f"🏦 {selected_ticker} 戰情看板")
    tab1, tab2, tab3 = st.tabs(["📊 終端看板 (雙效估價)", "🧠 策略回測 (定期不定額)", "📋 綜合雷達 (菜單與名單)"])
    
    with st.spinner(f"正在載入 {selected_ticker} 數據..."):
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

                with tab2:
                    st.markdown("不想無腦扣款？以過去 5 年真實股價對決「憨憨存」與「聰明存」。")
                    base_amt = st.number_input("每月基準扣款 (元)", min_value=1000, value=10000, step=1000, key="dca_amt")
                    
                    if st.button(f"🚀 啟動 {selected_ticker} 回測", type="primary"):
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
                        res_col1.metric("🤖 定期定額總市值", f"${int(fixed_shares * final_price):,}", f"{fixed_roi:.2f}%")
                        res_col2.metric("🧠 聰明存總市值", f"${int(smart_shares * final_price):,}", f"{smart_roi:.2f}%")

                with tab3:
                    st.subheader("🚨 本週雷達鎖定：黃金名單")
                    if os.path.exists("golden_list.csv") and "狀態" not in df_golden.columns:
                        st.dataframe(df_golden, use_container_width=True, hide_index=True)
                    else:
                        st.info("目前市場無特價標的。")

            else:
                st.warning("查無資料。")
        except Exception as e:
            st.error(f"錯誤：{e}")


# =========================================================================
# 系統 B：波段戰情室 (🔥 終極升級版)
# =========================================================================
elif system_menu == "📈 波段戰情室 (短期動能)":
    
    # ----------------------------------------
    # 左側邊欄：輸入標的與雷達掃描
    # ----------------------------------------
    st.sidebar.subheader("🎯 目標個股分析")
    # 讓使用者輸入代號 (免加 .TW)
    raw_target = st.sidebar.text_input("🔍 查詢代號 (免輸入 .tw，如 3008)：", "3008")
    selected_target = auto_tw(raw_target)

    st.sidebar.write("---")
    st.sidebar.subheader("🚀 批次雷達掃描")
    default_radar = "2330, 2317, 2454, 3231, 2382, 2603, 3008"
    user_radar = st.sidebar.text_area("觀察清單 (逗號分隔)：", default_radar)
    
    if st.sidebar.button("啟動爆量突破雷達", type="primary"):
        ticker_list = [auto_tw(t) for t in user_radar.split(",") if t.strip()]
        sniper_results = []

        with st.sidebar.status("雷達掃描中..."):
            for ticker in ticker_list:
                try:
                    hist = yf.Ticker(ticker).history(period="3mo")
                    if len(hist) > 20:
                        hist['20MA'] = hist['Close'].rolling(window=20).mean()
                        hist['20V_MA'] = hist['Volume'].rolling(window=20).mean()

                        latest = hist.iloc[-1]
                        current_price, current_open, current_vol = latest['Close'], latest['Open'], latest['Volume']
                        ma20, vol_ma20 = latest['20MA'], latest['20V_MA']

                        is_breakout = current_price > ma20
                        is_volume_surge = current_vol > (vol_ma20 * 2)
                        is_red_candle = current_price > current_open

                        if is_breakout and is_volume_surge and is_red_candle:
                            status = "🔥 爆量"
                        else:
                            status = "⏳ 潛伏"

                        sniper_results.append({
                            "代號": ticker.replace(".TW", ""),
                            "判定": status,
                            "現價": round(current_price, 2)
                        })
                except Exception as e:
                    pass 

        if sniper_results:
            df_results = pd.DataFrame(sniper_results).sort_values(by="判定", ascending=False)
            st.sidebar.success("掃描完成！")
            st.sidebar.dataframe(df_results, use_container_width=True, hide_index=True)

    # ----------------------------------------
    # 右側主畫面：個股 K 線與戰術背包
    # ----------------------------------------
    # 取得中文名稱，若字典找不到則嘗試抓 yf 的預設名，最後預設為代號
    stock_info = yf.Ticker(selected_target)
    ch_name = TW_NAMES.get(selected_target, stock_info.info.get('shortName', selected_target))
    
    st.header(f"📈 {ch_name} ({selected_target})")
    
    tab_kline, tab_bp = st.tabs(["📊 專業 K 線與動能解析", "🎒 戰術背包 (即時庫存)"])

    # --- [分頁 1] 專業 Plotly K 線圖 ---
    with tab_kline:
        with st.spinner("正在繪製高階 K 線圖..."):
            try:
                hist_k = stock_info.history(period="6mo")
                if not hist_k.empty:
                    # 計算均線
                    hist_k['20MA'] = hist_k['Close'].rolling(window=20).mean()
                    hist_k['60MA'] = hist_k['Close'].rolling(window=60).mean()
                    
                    # 建立 Plotly 圖表物件
                    fig = go.Figure()
                    
                    # 畫 K 線 (設定台股專屬顏色：紅漲綠跌)
                    fig.add_trace(go.Candlestick(x=hist_k.index,
                                    open=hist_k['Open'], high=hist_k['High'],
                                    low=hist_k['Low'], close=hist_k['Close'],
                                    name='K線',
                                    increasing_line_color='#FF4136', # 台股紅漲
                                    decreasing_line_color='#2ECC40'  # 台股綠跌
                                    ))
                    
                    # 加入均線
                    fig.add_trace(go.Scatter(x=hist_k.index, y=hist_k['20MA'], line=dict(color='orange', width=1.5), name='月線 (20MA)'))
                    fig.add_trace(go.Scatter(x=hist_k.index, y=hist_k['60MA'], line=dict(color='cyan', width=1.5), name='季線 (60MA)'))
                    
                    # 隱藏下方的 range slider 讓畫面更大，並使用暗色主題
                    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0))
                    
                    # 將互動圖表顯示在網頁上
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 下方顯示當前量價動能狀態
                    latest_k = hist_k.iloc[-1]
                    st.write("---")
                    col_k1, col_k2, col_k3 = st.columns(3)
                    col_k1.metric("今日收盤", f"{latest_k['Close']:.2f}", f"{latest_k['Close'] - hist_k.iloc[-2]['Close']:.2f}")
                    col_k2.metric("20日均線 (月線)", f"{latest_k['20MA']:.2f}")
                    
                    if latest_k['Close'] > latest_k['20MA']:
                        col_k3.success("📈 趨勢偏多 (站上月線)")
                    else:
                        col_k3.warning("📉 趨勢偏空 (跌破月線)")
                else:
                    st.warning("查無此股票資料，請確認代號是否正確。")
            except Exception as e:
                st.error(f"繪圖發生錯誤：{e}")

    # --- [分頁 2] 戰術背包 (維持真實損益功能) ---
    with tab_bp:
        backpack_file = "tactical_backpack.csv"
        if os.path.exists(backpack_file):
            df_bp = pd.read_csv(backpack_file)
            if "股數" not in df_bp.columns:
                df_bp["股數"] = 1000
        else:
            df_bp = pd.DataFrame(columns=["代號", "買進成本", "股數"])

        st.subheader("🎒 真實庫存損益")
        col_add, col_close = st.columns(2)
        
        with col_add:
            with st.expander("➕ 新增實際持股", expanded=False):
                # 這裡也免加 .TW
                new_raw = st.text_input("輸入股票代號 (如 3008)：", key="add_ticker")
                new_ticker = auto_tw(new_raw)
                new_cost = st.number_input("實際成交均價：", min_value=0.0, step=1.0, format="%.2f")
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
            with st.expander("🧨 執行平倉", expanded=False):
                if not df_bp.empty:
                    close_ticker = st.selectbox("選擇要平倉的標的：", df_bp["代號"].tolist())
                    if st.button("💥 確認平倉"):
                        df_bp = df_bp[df_bp["代號"] != close_ticker]
                        df_bp.to_csv(backpack_file, index=False, encoding="utf-8-sig")
                        st.success(f"{close_ticker} 已平倉移除！")
                        st.rerun()
                else:
                    st.info("背包空空如也。")

        if not df_bp.empty:
            bp_results = []
            with st.spinner("抓取庫存即時報價..."):
                for index, row in df_bp.iterrows():
                    try:
                        ticker = row["代號"]
                        cost = float(row["買進成本"])
                        qty = int(row.get("股數", 1000))
                        
                        stk = yf.Ticker(ticker)
                        curr_price = stk.fast_info['last_price']
                        
                        pnl_pct = ((curr_price / cost) - 1) * 100
                        pnl_amt = (curr_price - cost) * qty
                        
                        # 把代號的 .TW 拿掉，並嘗試加上中文名
                        ch_name_bp = TW_NAMES.get(ticker, ticker.replace(".TW", ""))
                        
                        bp_results.append({
                            "名稱 (代號)": f"{ch_name_bp}",
                            "股數": f"{qty:,}",
                            "買進均價": f"{cost:.2f}",
                            "最新現價": f"{curr_price:.2f}",
                            "未實現損益(元)": f"{pnl_amt:+,.0f}",
                            "報酬率(%)": f"{pnl_pct:+.2f}%"
                        })
                    except Exception as e:
                        bp_results.append({"名稱 (代號)": ticker, "買進均價": cost, "最新現價": "報價失敗"})
            
            st.dataframe(pd.DataFrame(bp_results), use_container_width=True, hide_index=True)
        else:
            st.info("背包目前沒有任何庫存。")
