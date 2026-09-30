import yfinance as yf
import pandas as pd
import datetime
import os

# ==========================================
# 1. 定義海巡範圍 (優質股票池)
# ==========================================
stock_pool = [
    "2886.TW", "5880.TW", "2884.TW", "2892.TW", "2885.TW", "2881.TW",
    "2412.TW", "3045.TW", 
    "0056.TW", "00878.TW", "00713.TW",
    "2330.TW", "2912.TW", "5903.TW" 
]

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
