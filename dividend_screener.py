import yfinance as yf
import pandas as pd
import datetime
import os

import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. 雲端大腦連線與讀取「存股名單」
# ==========================================
stock_pool = []
try:
    # 建立 Google 試算表連線
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds_json = os.environ.get("GCP_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    # 讀取你的 tactical_backpack 試算表
    SHEET_ID = "1duoJGMw_b6xyZSeY5Gt-QfY2KfKZuOI7-Lkwjo85V0c"
    sh = gc.open_by_key(SHEET_ID)
    
    print("📡 正在連接 Google 試算表獲取存股名單...")
    ws_div = sh.worksheet("存股名單")
    div_records = ws_div.get_all_records(numericise_ignore=["代號"])
    
    for row in div_records:
        t = str(row.get("代號", "")).strip()
        if t: 
            # 確保加上 .TW 讓 yfinance 認得是台股
            if not t.endswith(".TW") and not t.endswith(".TWO"):
                t += ".TW" 
            stock_pool.append(t)
            
    print(f"✅ 成功載入 {len(stock_pool)} 檔存股標的！")
    
except Exception as e:
    print(f"⚠️ 讀取雲端名單失敗，原因：{e}")
    # 預防萬一連線失敗，給它一個備用的基本名單以免當機
    stock_pool = ["2884.TW", "2891.TW", "2881.TW", "2885.TW", "00878.TW"]

print(f"🚀 啟動動態存股海巡大腦！本次預計掃描 {len(stock_pool)} 檔股票...")
golden_list = []
current_year = datetime.datetime.now().year

# ==========================================
# 2. 啟動「與自己比較」的動態掃描
# ==========================================
for ticker in stock_pool:
    try:
        print(f"🔍 正在探測 {ticker} ...", end=" ")
        stock = yf.Ticker(ticker)
        
        # 同時抓取歷史配息與過去 5 年的真實股價
        dividends = stock.dividends
        hist_5y = stock.history(period="5y")
        current_price = stock.fast_info['last_price']
        
        if not dividends.empty and not hist_5y.empty:
            recent_5_years_div = dividends[dividends.index.year >= current_year - 5]
            
            if not recent_5_years_div.empty:
                # 算歷史平均配息
                avg_div_5y = recent_5_years_div.tail(5).mean()
                # 算歷史 5 年平均股價
                avg_price_5y = hist_5y['Close'].mean()
                
                # 🌟 動態核心指標 1：算出這檔股票專屬的「歷史平均殖利率」
                hist_avg_yield = avg_div_5y / avg_price_5y
                
                # 🌟 動態核心指標 2：算出「現在的潛在殖利率」
                current_yield = avg_div_5y / current_price
                
                # 🚨 判定邏輯：現在殖利率 > 歷史平均，代表跌破歷史均價，是特價！
                if current_yield > hist_avg_yield:
                    print(f"✅ 發現特價目標！(目前 {current_yield*100:.2f}% > 歷史 {hist_avg_yield*100:.2f}%)")
                    golden_list.append({
                        "股票代號": ticker,
                        "最新現價": round(current_price, 2),
                        "歷史平均殖利率": f"{hist_avg_yield*100:.2f}%",
                        "目前殖利率": f"{current_yield*100:.2f}%",
                        "近5次均息": round(avg_div_5y, 2)
                    })
                else:
                    print(f"❌ 太貴了 (目前 {current_yield*100:.2f}% < 歷史 {hist_avg_yield*100:.2f}%)")
            else:
                print("⚠️ 無近 5 年配息資料。")
        else:
            print("⚠️ 資料不足。")
            
    except Exception as e:
        print(f"⚠️ 抓取失敗 ({e})")

# ==========================================
# 3. 儲存動態黃金名單
# ==========================================
print("\n==========================================")
if len(golden_list) > 0:
    df_golden = pd.DataFrame(golden_list)
    df_golden.to_csv("golden_list.csv", index=False, encoding="utf-8-sig")
    print(f"🎉 海巡任務完成！共撈到 {len(golden_list)} 檔便宜好股，已存入 golden_list.csv。")
else:
    pd.DataFrame(columns=["狀態"]).to_csv("golden_list.csv", index=False, encoding="utf-8-sig")
    print("🥺 海巡任務完成！目前市場太熱，沒有股票比自己的歷史平均更便宜。")
