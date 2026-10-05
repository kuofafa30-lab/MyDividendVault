import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import os

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
# ==========================================
# 🧭 側邊欄：總司令部導覽選單
# ==========================================
st.sidebar.title("👨‍💻 量化交易終端機")
system_menu = st.sidebar.radio(
    "切換監控系統：",
    ["🏦 存股金庫 (長期價值)", "📈 波段戰情室 (短期動能)"]
)
st.sidebar.write("---")
st.sidebar.info("💡 提示：雷達名單皆由 GitHub Actions 自動於背景排程更新。")

# ==========================================
# 系統 A：存股金庫
# ==========================================
if system_menu == "🏦 存股金庫 (長期價值)":
    st.title("🏦 長期存股金庫 (Dividend Vault)")
    st.write("---")
    
    # ==========================================
    # 1. 📊 存股雙效估價與河流圖面板
    # ==========================================
    st.write("---")
    st.header("📊 1. 存股雙效估價與歷史河流圖")
    st.markdown("輸入股票代號，一次看懂「絕對殖利率 (654法則)」與「相對歷史位階 (河流圖)」。")
    
    # 只需要在這裡輸入一次代號！
    ticker = st.text_input("請輸入台股代號 (例如 2912.TW)：", "2912.TW")
    
    if st.button("開始雙效估價", type="primary"):
        with st.spinner(f"正在為您分析 {ticker} 的估價與歷史軌跡..."):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="5y")
                divs = stock.dividends
                
                if not hist.empty and not divs.empty:
                    # 取得最新現價
                    current_price = stock.fast_info['last_price']
                    
                    # 計算近 5 年平均配息
                    current_year = datetime.datetime.now().year
                    recent_5_years_div = divs[divs.index.year >= current_year - 5]
                    avg_div = recent_5_years_div.tail(5).mean()
                    
                    # 計算目前潛在殖利率
                    current_yield = (avg_div / current_price) * 100
    
                    # --- 準備河流圖數據 ---
                    monthly_price = hist['Close'].resample('ME').last()
                    df_river = pd.DataFrame({'現價': monthly_price})
                    df_river['年份'] = df_river.index.year
                    
                    yearly_divs = divs.groupby(divs.index.year).sum()
                    df_river['當年配息'] = df_river['年份'].map(yearly_divs)
                    df_river['當年配息'] = df_river['當年配息'].ffill() 
                    df_river = df_river.dropna()
                    
                    df_river['殖利率(%)'] = (df_river['當年配息'] / df_river['現價']) * 100
                    hist_avg_yield = df_river['殖利率(%)'].mean()
                    df_river['歷史平均線'] = hist_avg_yield
    
                    # ==========================================
                    # UI 展示：雙效估價面板
                    # ==========================================
                    col1, col2 = st.columns(2)
                    
                    # 左側：絕對估價 (傳統 654)
                    with col1:
                        st.subheader("🎯 絕對估價 (傳統 654 準則)")
                        cheap_price = avg_div / 0.06
                        fair_price = avg_div / 0.05
                        expensive_price = avg_div / 0.04
                        
                        st.write(f"**最新現價：** {current_price:.2f} 元 (潛在殖利率: {current_yield:.2f}%)")
                        
                        if current_price <= cheap_price:
                            st.success(f"🟢 便宜價 (6%)：{cheap_price:.2f} 以下")
                            st.write(f"🟡 合理價 (5%)：{fair_price:.2f}")
                            st.write(f"🔴 昂貴價 (4%)：{expensive_price:.2f}")
                        elif current_price <= fair_price:
                            st.write(f"🟢 便宜價 (6%)：{cheap_price:.2f}")
                            st.warning(f"🟡 合理價 (5%)：{fair_price:.2f} 以下")
                            st.write(f"🔴 昂貴價 (4%)：{expensive_price:.2f}")
                        else:
                            st.write(f"🟢 便宜價 (6%)：{cheap_price:.2f}")
                            st.write(f"🟡 合理價 (5%)：{fair_price:.2f}")
                            st.error(f"🔴 昂貴價 (4%)：{expensive_price:.2f} 以上")
    
                    # 右側：相對估價 (歷史均值)
                    with col2:
                        st.subheader("🌊 相對估價 (歷史均值法)")
                        st.write(f"**歷史 5 年平均殖利率：** {hist_avg_yield:.2f}%")
                        
                        if current_yield > hist_avg_yield:
                            st.success(f"🟢 突破歷史慣性！目前殖利率 ({current_yield:.2f}%) 高於歷史平均。以它自己的標準來看，現在正處於相對特價的深水區！")
                        else:
                            st.warning(f"🟡 歷史位階偏高。目前殖利率 ({current_yield:.2f}%) 低於歷史平均。建議觀望，等待股價回落或獲利提升。")
    
                    st.write("---")
                    # ==========================================
                    # UI 展示：殖利率走勢圖
                    # ==========================================
                    st.subheader(f"📈 {ticker} 過去 5 年殖利率走勢")
                    st.markdown("觀察下圖：當**波動的折線**向上突破**平直的歷史平均線**時，代表股價跌出超額殖利率，是這檔股票相對自身的特價買點。")
                    
                    chart_data = df_river[['殖利率(%)', '歷史平均線']]
                    # 設定 Streamlit 圖表的顏色 (若 Streamlit 版本支援，這會讓兩條線顏色更分明)
                    st.line_chart(chart_data)
                    
                else:
                    st.warning("這檔股票缺乏足夠的歷史股價或配息資料，無法進行分析。")
                    
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
# ==========================================
# 3. 🧠 智慧存股：定期不定額 (Smart DCA) 真實回測
# ==========================================
st.write("---")
st.header("🧠 3. 智慧存股：定期不定額 (真實回測)")
st.markdown("不想無腦扣款？來回測看看「價低買多、價高買少」的威力！我們以過去 5 年的真實歷史股價來對決。")

col_a, col_b = st.columns([1, 2])
with col_a:
    ticker_bt = st.text_input("輸入回測代號 (例如 0050.TW)：", "00878.TW", key="bt_ticker")
    base_amt = st.number_input("每月基準扣款 (元)", min_value=1000, value=10000, step=1000)

if st.button("🚀 啟動 5 年真實回測", type="primary"):
    with st.spinner(f"正在讀取 {ticker_bt} 過去 5 年的真實股價與計算技術指標..."):
        try:
            # 抓取過去 5 年的歷史資料
            hist = yf.Ticker(ticker_bt).history(period="5y")
            
            if not hist.empty:
                # 將每天的資料，濃縮成「每個月最後一天」的收盤價
                monthly_data = hist['Close'].resample('ME').last().to_frame()
                # 計算 6 個月移動平均線
                monthly_data['6MA'] = monthly_data['Close'].rolling(window=6).mean()
                monthly_data = monthly_data.dropna()
                
                fixed_shares = 0
                fixed_cost = 0
                
                smart_shares = 0
                smart_cost = 0
                
                # 啟動時光機
                for date, row in monthly_data.iterrows():
                    price = row['Close']
                    ma6 = row['6MA']
                    
                    # 定期定額
                    fixed_shares += base_amt / price
                    fixed_cost += base_amt
                    
                    # 定期不定額
                    if price < ma6 * 0.95:
                        invest = base_amt * 2
                    elif price > ma6 * 1.05:
                        invest = base_amt * 0.5
                    else:
                        invest = base_amt
                        
                    smart_shares += invest / price
                    smart_cost += invest
                
                # 結算
                final_price = monthly_data['Close'].iloc[-1]
                fixed_value = fixed_shares * final_price
                smart_value = smart_shares * final_price
                
                fixed_roi = (fixed_value / fixed_cost - 1) * 100
                smart_roi = (smart_value / smart_cost - 1) * 100
                
                # 顯示對決結果
                st.subheader(f"⚔️ 策略對決結果 (標的：{ticker_bt})")
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.info("🤖 策略一：憨憨存 (定期定額)")
                    st.metric("累積投入本金", f"${int(fixed_cost):,}")
                    st.metric("最終總市值", f"${int(fixed_value):,}", f"{fixed_roi:.2f}% (總報酬)")
                    
                with res_col2:
                    st.success("🧠 策略二：聰明存 (價低買多、價高買少)")
                    st.metric("累積投入本金", f"${int(smart_cost):,}")
                    st.metric("最終總市值", f"${int(smart_value):,}", f"{smart_roi:.2f}% (總報酬)")
                
                st.write("---")
                if smart_roi > fixed_roi:
                    st.success("🏆 **結論：** 在這檔股票上，『聰明存』的報酬率擊敗了傳統的定期定額！")
                else:
                    st.warning("🤔 **結論：** 這檔股票一路向上不回頭，導致『聰明存』一直縮手買太少，反而輸給了無腦扣款。")
                    
            else:
                st.warning("找不到這檔股票的歷史資料，請確認代號。")
        except Exception as e:
            st.error(f"發生錯誤：{e}")

# ==========================================
# 4. 🚨 本週雷達鎖定：便宜價黃金名單
# ==========================================
st.write("---")
st.header("🚨 4. 本週雷達鎖定：便宜價黃金名單")

if os.path.exists("golden_list.csv"):
    df_golden = pd.read_csv("golden_list.csv")
    if "狀態" not in df_golden.columns:
        st.success(f"🎉 探測器回報：本週共發現 {len(df_golden)} 檔落入 6% 殖利率便宜價的優質標的！")
        st.dataframe(df_golden, use_container_width=True, hide_index=True)
    else:
        st.info("🥺 探測器回報：本週市場太熱，沒有股票落入 6% 殖利率的便宜價區間。")
else:
    st.warning("⏳ 探測器尚未產出報告。請等待週五的自動掃描，或前往 GitHub 手動觸發。")

# ==========================================
# 系統 B：波段戰情室
# ==========================================
elif system_menu == "📈 波段戰情室 (短期動能)":
    st.title("📈 波段戰情室 (Swing Trading)")
    st.markdown("這裡是捕捉股價創高、爆量上漲的短期動能狙擊區。")
    
    # 👉 接下來，請把之前「波段戰情室」的 Python 程式碼全部貼在這裡！
    # ⚠️ 貼上後，一樣要記得把戰情室的程式碼「整段反白 + 按一次 Tab 鍵」，確保它們對齊在 elif 底下。
