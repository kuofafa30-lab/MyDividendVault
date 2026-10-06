import os
import json
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import requests
import time

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")
GCP_JSON = os.environ.get("GCP_CREDENTIALS")

TW_NAMES = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", 
    "3008.TW": "大立光", "2382.TW": "廣達", "3231.TW": "緯創",
    "2603.TW": "長榮", "2912.TW": "統一超", "5903.TW": "全家",
    "2886.TW": "兆豐金", "0050.TW": "元大台灣50", "00878.TW": "國泰永續高息",
    "2025.TW": "千興", "6155.TW": "鈞寶", "6438.TW": "迅得", "8162.TW": "微矽電子-創"
}

def auto_tw(ticker):
    t = str(ticker).strip().upper()
    if not t: return ""
    return t if (t.endswith(".TW") or t.endswith(".TWO")) else f"{t}.TW"

def send_line_message(message):
    if not LINE_TOKEN or not LINE_USER_ID:
        print("❌ 缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID，無法發送")
        return
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    
    max_retries = 3
    for i in range(max_retries):
        try:
            # 官方帳號 API 必須用 json 格式傳遞資料
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                print("✅ 戰報發送成功！")
                return
            else:
                print(f"發送失敗 (第 {i+1} 次嘗試): 狀態碼 {response.status_code}, 錯誤訊息: {response.text}")
        except Exception as e:
            print(f"發送發生例外錯誤 (第 {i+1} 次嘗試): {e}")
            
        if i < max_retries - 1:
            time.sleep(5)
            
    print("❌ 連續 3 次發送 Line 失敗，放棄執行。")

msg = "\n📊 【波段戰情室】每日收盤戰報\n"
msg += "="*20 + "\n"

# ==========================================
# 1. 讀取 Google Sheets，結算真實庫存損益
# ==========================================
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GCP_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # 打開我們共用的試算表
    sh = gc.open("tactical_backpack")
    worksheet = sh.sheet1
    records = worksheet.get_all_records()
    
    total_pnl = 0
    msg += "🎒 [真實庫存損益]\n"
    
    if not records:
        msg += "目前背包空空如也。\n"
    else:
        for row in records:
            ticker = auto_tw(row.get("代號", ""))
            if not ticker: continue
            
            try:
                cost = float(row.get("買進成本", 0))
                qty = int(row.get("股數", 1000))
            except:
                cost, qty = 0, 1000
            
            try:
                stk = yf.Ticker(ticker)
                curr_price = stk.fast_info['last_price']
                pnl_amt = (curr_price - cost) * qty
                pnl_pct = ((curr_price / cost) - 1) * 100
                total_pnl += pnl_amt
                
                ch_name = TW_NAMES.get(ticker, ticker.replace(".TW", ""))
                msg += f"🔹 {ch_name}: 現價 {curr_price:.2f}\n"
                msg += f"   損益: {pnl_amt:+,.0f}元 ({pnl_pct:+.2f}%)\n"
            except Exception as e:
                msg += f"🔹 {ticker}: 報價抓取失敗\n"
                
        msg += "-"*20 + "\n"
        msg += f"💰 總未實現損益: {total_pnl:+,.0f} 元\n"

except Exception as e:
    msg += f"⚠️ 讀取庫存失敗，請檢查 GCP 金鑰或試算表共用狀態。\n"

msg += "="*20 + "\n"

# ==========================================
# 2. 執行狙擊雷達掃描 (改為讀取雲端雷達名單)
# ==========================================
msg += "🚀 [爆量狙擊雷達]\n"
radar_tickers = []
radar_results = []

try:
    # 🌟 讀取試算表中的「雷達名單」分頁
    ws_radar = sh.worksheet("雷達名單")
    radar_records = ws_radar.get_all_records()
    for row in radar_records:
        t = auto_tw(row.get("代號", ""))
        if t: 
            radar_tickers.append(t)
            
    if not radar_tickers:
        msg += "⚠️ 雷達名單目前為空，請至系統新增。\n"
        
except Exception as e:
    msg += "⚠️ 讀取雷達名單失敗，請確認試算表分頁名稱是否為「雷達名單」。\n"

# 開始掃描 (這段邏輯跟之前一樣)
for ticker in radar_tickers:
    try:
        hist = yf.Ticker(ticker).history(period="3mo")
        if len(hist) > 20:
            hist['20MA'] = hist['Close'].rolling(window=20).mean()
            hist['20V_MA'] = hist['Volume'].rolling(window=20).mean()
            
            latest = hist.iloc[-1]
            close, open_p, vol = latest['Close'], latest['Open'], latest['Volume']
            ma20, vol_ma20 = latest['20MA'], latest['20V_MA']

            # 突破月線 且 爆量2倍 且 收紅K
            if close > ma20 and vol > (vol_ma20 * 2) and close > open_p:
                ch_name = TW_NAMES.get(ticker, ticker.replace(".TW", ""))
                radar_results.append(f"🔥 {ch_name} (收: {close:.1f})")
    except:
        pass

if radar_tickers:
    if radar_results:
        msg += "\n".join(radar_results)
    else:
        msg += "💤 今日無標的符合爆量突破條件。"
# ==========================================
# 3. 執行存股海巡掃描 (本土官方 API 升級版)
# ==========================================
import requests

msg += "\n\n🏦 [存股海巡探測器]\n"
div_tickers = []
div_results = []
TARGET_YIELD = 5.0  # 🎯 設定你的理想殖利率標準 (目前設為 5%)

try:
    ws_div = sh.worksheet("存股名單")
    div_records = ws_div.get_all_records(numericise_ignore=["代號"])
    for row in div_records:
        t = str(row.get("代號", "")).strip()
        if t: div_tickers.append(t)
except Exception as e:
    msg += "⚠️ 尚未讀取到「存股名單」分頁，請至試算表建立。\n"

# 🌟 呼叫台灣本土官方開放資料 API (一次性抓取全市場殖利率)
official_yields = {}
try:
    # 上市公司 (證交所)
    tw_url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
    for item in requests.get(tw_url, timeout=10).json():
        official_yields[item['Code']] = item['DividendYield']
    # 上櫃公司 (櫃買中心)
    otc_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"
    for item in requests.get(otc_url, timeout=10).json():
        official_yields[item['SecuritiesCompanyCode']] = item['DividendYield']
except Exception as e:
    print(f"官方 API 抓取失敗: {e}")

for ticker in div_tickers:
    try:
        # 確保代號是乾淨的數字 (過濾掉 .TW)
        clean_ticker = ticker.replace(".TW", "").replace(".TWO", "")
        ch_name = TW_NAMES.get(auto_tw(clean_ticker), clean_ticker)
        
        # 抓取今日收盤價 (維持用 yfinance 最快)
        tk = yf.Ticker(auto_tw(clean_ticker))
        hist = tk.history(period="1d")
        close = hist['Close'].iloc[-1] if not hist.empty else 0
        
        # 🌟 從本土 API 字典中精準比對殖利率
        yield_str = official_yields.get(clean_ticker, "0")
        
        # 處理無資料或顯示為 "-" 的情況 (例如 ETF 通常不在證交所此清單內)
        if yield_str == "-" or not yield_str.replace('.', '', 1).isdigit():
            yield_pct = 0.0
            # 針對 ETF 的備案：向 Yahoo 備用欄位抓取年度配息率
            fallback_yield = tk.info.get("trailingAnnualDividendYield", 0)
            if fallback_yield:
                yield_pct = fallback_yield * 100
        else:
            yield_pct = float(yield_str)
            
        if close > 0:
            if yield_pct >= TARGET_YIELD:
                div_results.append(f"🟢 {ch_name}: {yield_pct:.2f}% (便宜！收:{close:.1f})")
            elif yield_pct > 0:
                div_results.append(f"⚪ {ch_name}: {yield_pct:.2f}% (收:{close:.1f})")
            else:
                div_results.append(f"⚪ {ch_name}: API 暫無殖利率 (收:{close:.1f})")

    except Exception as e:
        pass

if div_tickers:
    if div_results:
        msg += "\n".join(div_results)
    else:
        msg += "今日存股清單無動靜。" 
# 發送通知
if LINE_TOKEN and LINE_USER_ID:
    send_line_message(msg)
else:
    print("❌ 找不到 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID，請檢查 Secrets 設定。")
