import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection  # 🌟 新增的 Google Sheets 連線套件

# ==========================================
# 0. 網頁初始設定與金庫密碼鎖
# ==========================================
st.set_page_config(page_title="量化交易終端機", page_icon="👨‍💻", layout="wide")

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.title("🔒 量化終端機 - 系統登入")
        
        # 🌟 建立專屬登入表單，支援 Enter 鍵快捷送出
        with st.form("login_form"):
            pwd = st.text_input("請輸入通行密碼：", type="password")
            
            # 這裡把原本的 st.button 替換成 st.form_submit_button
            submitted = st.form_submit_button("解鎖大門", type="primary")
            
            # 判斷是否點擊了按鈕或按下了 Enter
            if submitted:
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
# 🧭 核心輔助工具箱 (防呆與翻譯)
# ==========================================
# 1. 自動補上 .TW 的防呆函數 (讓你輸入 3008 就好)
def auto_tw(ticker):
    t = str(ticker).strip().upper()
    if not t: return ""
    if not t.endswith(".TW") and not t.endswith(".TWO"):
        return f"{t}.TW"
    return t

# 2. 專屬台股中文名稱對照表 (把你的持股都加進來了！)
TW_NAMES = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", 
    "3008.TW": "大立光", "2382.TW": "廣達", "3231.TW": "緯創",
    "2603.TW": "長榮", "2912.TW": "統一超", "5903.TW": "全家",
    "2886.TW": "兆豐金", "0050.TW": "元大台灣50", "00878.TW": "國泰永續高息",
    "2025.TW": "千興", "6155.TW": "鈞寶", "6438.TW": "迅得", "8162.TW": "微矽電子-創"
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
st.sidebar.markdown("---")
st.sidebar.subheader("📡 雲端雷達名單管理")
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    # 連線並讀取「雷達名單」分頁
    df_radar = conn.read(worksheet="雷達名單", ttl=0)
    if df_radar is None or df_radar.empty:
        df_radar = pd.DataFrame(columns=["代號"])
    else:
        df_radar = df_radar.dropna(how="all")
        if "代號" in df_radar.columns:
            df_radar["代號"] = df_radar["代號"].astype(str).str.replace(r'\.0$', '', regex=True)

    # 顯示目前監控數量
    st.sidebar.write(f"📋 目前監控中：{len(df_radar)} 檔標的")
    
    # 新增雷達標的
    with st.sidebar.expander("➕ 新增監控標的", expanded=False):
        new_radar_raw = st.text_input("輸入代號 (如 3008)：", key="add_radar")
        new_radar = auto_tw(new_radar_raw)
        if st.button("加入雷達網"):
            if new_radar:
                if new_radar in df_radar["代號"].values:
                    st.warning("已經在監控名單中囉！")
                else:
                    new_row = pd.DataFrame({"代號": [new_radar]})
                    df_radar = pd.concat([df_radar, new_row], ignore_index=True)
                    conn.update(worksheet="雷達名單", data=df_radar)
                    st.success(f"{new_radar} 已加入！")
                    st.rerun()

    # 移除雷達標的
    with st.sidebar.expander("🗑️ 移除監控標的", expanded=False):
        if not df_radar.empty:
            del_radar = st.selectbox("選擇要移除的標的：", df_radar["代號"].tolist())
            if st.button("解除監控"):
                df_radar = df_radar[df_radar["代號"] != del_radar]
                conn.update(worksheet="雷達名單", data=df_radar)
                st.success(f"{del_radar} 已移除！")
                st.rerun()
        else:
            st.info("目前沒有監控標的")
            
except Exception as e:
    st.sidebar.error(f"⚠️ 系統真實錯誤：{e}")
    st.sidebar.info("請把這個錯誤訊息截圖給我看！")
# =========================================================================
# 系統 A：存股金庫 (價值投資)
# =========================================================================
if system_menu == "🏦 存股金庫 (長期價值)":
    st.sidebar.subheader("📋 存股雷達清單")
    
    # 預設清單加上自訂輸入功能
    ticker_list = ["2912", "5903", "2886", "2330", "00878"]
    
    if os.path.exists("golden_list.csv"):
        df_golden = pd.read_csv("golden_list.csv")
        if "狀態" not in df_golden.columns:
            st.sidebar.success(f"🔥 雷達本週發現 {len(df_golden)} 檔特價股！")
            golden_raw = [t.replace(".TW", "") for t in df_golden['股票代號'].tolist()]
            ticker_list = list(set(ticker_list + golden_raw))
        else:
            st.sidebar.info("本週無特價股，顯示自選清單。")
            
    # --- 🌟 雙棲輸入法：下拉選單 + 任意輸入 ---
    ticker_list.insert(0, "✍️ 自行輸入代號...")
    raw_selected = st.sidebar.selectbox("🔍 點擊切換或選擇標的：", ticker_list)
    
    if raw_selected == "✍️ 自行輸入代號...":
        custom_ticker = st.sidebar.text_input("💡 請輸入任意台股代號 (如 2885)：", "2885")
        selected_ticker = auto_tw(custom_ticker)
    else:
        selected_ticker = auto_tw(raw_selected)

    # 取得中文名稱
    stock_info_a = yf.Ticker(selected_ticker)
    ch_name_a = TW_NAMES.get(selected_ticker, selected_ticker)

    st.header(f"🏦 {ch_name_a} 戰情看板")
    tab1, tab2, tab3 = st.tabs(["📊 終端看板 (雙效估價)", "🧠 策略回測 (定期不定額)", "📋 綜合雷達 (菜單與名單)"])
    
    with st.spinner(f"正在載入 {ch_name_a} 數據..."):
        try:
            hist = stock_info_a.history(period="5y")
            divs = stock_info_a.dividends
            if not hist.empty:
                current_price = stock_info_a.fast_info['last_price']
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
                    
                    if st.button(f"🚀 啟動 {ch_name_a} 回測", type="primary"):
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
# 系統 B：波段戰情室 (🔥 Google Sheets 雲端連線版)
# =========================================================================
elif system_menu == "📈 波段戰情室 (短期動能)":
    
    # --- 左側邊欄：輸入標的與雷達掃描 ---
    st.sidebar.subheader("🎯 目標個股分析")
    raw_target = st.sidebar.text_input("🔍 查詢代號 (免加 .tw，如 3008)：", "3008")
    selected_target = auto_tw(raw_target)

    # --- 右側主畫面：個股 K 線與戰術背包 ---
    stock_info_b = yf.Ticker(selected_target)
    
    # ✅ 升級：直接比對我們自己寫的 TW_NAMES 字典，避開 yfinance info 的快取地雷
    ch_name_b = TW_NAMES.get(selected_target, selected_target.replace(".TW", ""))
    
    # ✅ 確保表頭是綁定變數，隨著你輸入的代號連動改變
    st.header(f"📈 {ch_name_b} ({selected_target})")
    
    tab_kline, tab_bp = st.tabs(["📊 專業 K 線與動能解析", "🎒 戰術背包"])

    # [分頁 1] 專業 Plotly K 線圖
    with tab_kline:
        with st.spinner("正在繪製高階 K 線圖..."):
            try:
                hist_k = stock_info_b.history(period="6mo")
                if not hist_k.empty:
                    hist_k['20MA'] = hist_k['Close'].rolling(window=20).mean()
                    hist_k['60MA'] = hist_k['Close'].rolling(window=60).mean()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=hist_k.index,
                                    open=hist_k['Open'], high=hist_k['High'],
                                    low=hist_k['Low'], close=hist_k['Close'],
                                    name='K線', increasing_line_color='#FF4136', decreasing_line_color='#2ECC40'))
                    
                    fig.add_trace(go.Scatter(x=hist_k.index, y=hist_k['20MA'], line=dict(color='orange', width=1.5), name='月線 (20MA)'))
                    fig.add_trace(go.Scatter(x=hist_k.index, y=hist_k['60MA'], line=dict(color='cyan', width=1.5), name='季線 (60MA)'))
                    
                    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                    
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

    # [分頁 2] 戰術背包 (🚀 串接 Google 試算表)   
    with tab_bp:
        try:
            # 建立與 Google Sheets 的連線
            conn = st.connection("gsheets", type=GSheetsConnection)
            # 讀取試算表 (ttl=0 代表不快取，每次都抓最新)
            df_bp = conn.read(ttl=0)
            
            # 若為空表，建立預設 DataFrame
            if df_bp is None or df_bp.empty:
                df_bp = pd.DataFrame(columns=["代號", "買進成本", "股數"])
            else:
                df_bp = df_bp.dropna(how="all") # 清除完全空白的行
                if "代號" in df_bp.columns:
                    df_bp["代號"] = df_bp["代號"].astype(str).str.replace(r'\.0$', '', regex=True)
                
        except Exception as e:
            st.error(f"連線 Google 試算表失敗，請檢查 Secrets 權限或網路：{e}")
            df_bp = pd.DataFrame(columns=["代號", "買進成本", "股數"])

        st.subheader("🎒 真實庫存損益 (已連線 Google 雲端)")
        col_add, col_close = st.columns(2)
        
        with col_add:
            with st.expander("➕ 新增實際持股", expanded=False):
                new_raw = st.text_input("輸入股票代號 (如 3008)：", key="add_ticker")
                new_ticker = auto_tw(new_raw)
                new_cost = st.number_input("實際成交均價：", min_value=0.0, step=1.0, format="%.2f")
                new_qty = st.number_input("持有股數 (1張 = 1000)：", min_value=1, value=1000, step=1)
                
                if st.button("📥 寫入雲端金庫"):
                    if new_ticker:
                        if new_ticker in df_bp["代號"].values:
                            st.warning("這檔股票已經在背包裡了！")
                        else:
                            new_row = pd.DataFrame({"代號": [new_ticker], "買進成本": [new_cost], "股數": [new_qty]})
                            df_bp = pd.concat([df_bp, new_row], ignore_index=True)
                            
                            # ✨ 直接回寫至 Google 試算表
                            conn.update(data=df_bp)
                            
                            st.success(f"{new_ticker} ({new_qty}股) 已成功寫入 Google 試算表！")
                            st.rerun()

        with col_close:
            with st.expander("🧨 執行平倉", expanded=False):
                if not df_bp.empty:
                    close_ticker = st.selectbox("選擇要平倉的標的：", df_bp["代號"].tolist())
                    if st.button("💥 確認平倉"):
                        # 過濾掉要平倉的標的，並回寫
                        df_bp = df_bp[df_bp["代號"] != close_ticker]
                        conn.update(data=df_bp)
                        
                        st.success(f"{close_ticker} 已平倉並從雲端移除！")
                        st.rerun()
                else:
                    st.info("背包空空如也。")

        # =========================================
        # ⬇️ 這裡才是剛剛升級的「即時報價與損益」區塊 ⬇️
        # =========================================
        if not df_bp.empty:
            bp_results = []
            with st.spinner("抓取庫存即時報價..."):
                for index, row in df_bp.iterrows():
                    # 1. 確保防呆：不管 Google Sheets 裡有沒有寫 .TW，這裡一律強制補上
                    raw_ticker = str(row["代號"]).strip()
                    ticker = auto_tw(raw_ticker) 
                    
                    # 確保數字格式正確，避免抓到空值
                    try:
                        cost = float(row["買進成本"])
                        qty = int(row.get("股數", 1000))
                    except:
                        cost, qty = 0.0, 1000

                    # 取得中文名稱
                    ch_name_bp = TW_NAMES.get(ticker, ticker.replace(".TW", ""))
                    display_name = f"{ch_name_bp} ({ticker})"

                    try:
                        stk = yf.Ticker(ticker)
                        # 抓取近一個月歷史資料，為了同時拿最新價與算 20MA
                        hist = stk.history(period="1mo")
                        
                        if not hist.empty:
                            curr_price = hist['Close'].iloc[-1]
                            # 計算 20MA 防守點位 (若上市天數不足20天，則抓成本的 95% 為防守線)
                            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else cost * 0.95
                            
                            pnl_pct = ((curr_price / cost) - 1) * 100
                            pnl_amt = (curr_price - cost) * qty
                            
                            bp_results.append({
                                "名稱 (代號)": display_name,
                                "股數": f"{qty:,}",
                                "買進均價": f"{cost:.2f}",
                                "最新現價": f"{curr_price:.2f}",
                                "未實現損益(元)": f"{pnl_amt:+,.0f}",
                                "報酬率(%)": f"{pnl_pct:+.2f}%",
                                "防守點位(月線)": f"{ma20:.2f}"
                            })
                        else:
                            raise ValueError("無報價資料")
                            
                    except Exception as e:
                        # 2. 欄位固定機制：即使報價失敗，也要把所有欄位印出來，表格才不會縮水
                        bp_results.append({
                            "名稱 (代號)": display_name,
                            "股數": f"{qty:,}",
                            "買進均價": f"{cost:.2f}",
                            "最新現價": "報價失敗",
                            "未實現損益(元)": "-",
                            "報酬率(%)": "-",
                            "防守點位(月線)": "-"
                        })
            
            # 使用專業的 DataFrame 顯示，並隱藏左側索引值
            st.dataframe(pd.DataFrame(bp_results), use_container_width=True, hide_index=True)
        else:
            st.info("背包目前沒有任何庫存。")
