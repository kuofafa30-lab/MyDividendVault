import yfinance as yf
import pandas as pd
import datetime
import os

# ==========================================
# 1. 定義海巡範圍 (優質股票池)
# ==========================================
# 這裡先放 10 檔經典存股標的作為示範，你可以隨時新增！
stock_pool = [
    "2886.TW", "5880.TW", "2884.TW", "2892.TW", "2885.TW", # 金融股
    "2412.TW", "3045.TW", # 電信股
    "0056.TW", "00878.TW", "00713.TW" # 高息 ETF
]

print(f"🚀 啟動存股海巡大腦！本次預計掃描 {len(stock_pool)} 檔股票...")

golden_list = []
current_year = datetime.datetime.now().year

# ==========================================
# 2. 啟動逐檔掃描迴圈
# ==========================================
for ticker in stock_pool:
    try:
        print(f"🔍 正在探測 {ticker} ...", end=" ")
        stock = yf.Ticker(ticker)
        
        # 抓取配息與現價
        dividends = stock.dividends
        current_price = stock.fast_info['last_price']
        
        if not dividends.empty:
            # 篩選近 5 年的配息資料
            recent_5_years = dividends[dividends.index.year >= current_year - 5]
            
            if not recent_5_years.empty:
                # 算出近 5 次平均配息
                avg_dividend = recent_5_years.tail(5).mean()
                
                # 計算便宜價 (6% 殖利率)
                cheap_price = avg_dividend / 0.06
                
                # 🚨 核心邏輯：如果現價跌破便宜價，就撈進黃金名單！
                if current_price <= cheap_price:
                    print("✅ 發現特價目標！")
                    golden_list.append({
                        "股票代號": ticker,
                        "最新現價": round(current_price, 2),
                        "便宜價(6%)": round(cheap_price, 2),
                        "潛在殖利率": f"{(avg_dividend / current_price) * 100:.2f}%",
                        "近5次均息": round(avg_dividend, 2)
                    })
                else:
                    print("❌ 太貴了，跳過。")
            else:
                print("⚠️ 無近 5 年配息資料。")
        else:
            print("⚠️ 找不到配息紀錄。")
            
    except Exception as e:
        print(f"⚠️ 抓取失敗 ({e})")

# ==========================================
# 3. 儲存黃金名單
# ==========================================
print("\n==========================================")
if len(golden_list) > 0:
    df_golden = pd.DataFrame(golden_list)
    # 將結果存成 CSV 檔案，供網頁讀取
    df_golden.to_csv("golden_list.csv", index=False, encoding="utf-8-sig")
    print(f"🎉 海巡任務完成！共撈到 {len(golden_list)} 檔便宜好股，已存入 golden_list.csv。")
else:
    # 如果都沒跌到便宜價，就存一個空的 CSV，避免網頁讀取錯誤
    pd.DataFrame(columns=["狀態"]).to_csv("golden_list.csv", index=False, encoding="utf-8-sig")
    print("🥺 海巡任務完成！目前市場太熱，沒有股票落入便宜價。")
