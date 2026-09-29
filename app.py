import streamlit as st
import pandas as pd
import yfinance as yf

# 設定網頁為寬版，並換上金庫的圖示
st.set_page_config(page_title="長期存股金庫", page_icon="🏦", layout="wide")

st.title("🏦 長期存股金庫 (Dividend Vault)")
st.write("---")

st.info("🚧 系統建置中：準備載入高殖利率名單與歷年配息數據...")
