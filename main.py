import os
import yfinance as yf
import requests
import smtplib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
import re

# 1. 깃허브 금고(Secrets)에서 데이터 가져오기
NAVER_CLIENT_ID = os.environ.get('NAVER_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_SECRET')
NAVER_USER = os.environ.get('NAVER_USER')
NAVER_PW = os.environ.get('NAVER_PW')
# RECIPIENTS는 ["abc@gmail.com"] 형태여야 합니다.
raw_recipients = os.environ.get('RECIPIENTS')
try:
    RECIPIENTS = eval(raw_recipients)
except:
    RECIPIENTS = [raw_recipients]

# 2. 폰트 설정 (깃허브 서버용)
font_path = '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rc('font', family='NanumBarunGothic')
plt.rcParams['axes.unicode_minus'] = False

# 3. 분석할 종목 (김훈 님 관심 종목)
target_stocks = {
    "삼성전자": "005930.KS",
    "한화에어로스페이스": "012450.KS",
    "휴림로봇": "090710.KQ",
    "코닝(Corning)": "GLW",
    "엔비디아": "NVDA",
    "테슬라": "TSLA"
}

def clean_html(text):
    return re.sub('<.*?>', '', text).replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

def get_exchange_rate():
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return f"💵 현재 환율: {usd_krw:,.2f}원"
    except: return "환율 정보 없음"

def create_chart(name, ticker, hist):
    diff = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
    color = 'crimson' if diff >= 0 else 'royalblue'
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hist.index, hist['Close'], color=color, linewidth=2)
    ax.set_title(f"{name} ({ticker})", fontproperties=font_prop, fontsize=14)
    img_path = f"{ticker.replace('.', '_')}.png"
    plt.savefig(img_path)
    plt.close()
    return img_path

# --- 여기서부터 로봇이 실제로 일을 시작하는 부분입니다 ---
def run_stock_bot():
    print("🚀 [1/3] 주식 데이터 분석을 시작합니다...")
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📈 [자동리포트] {datetime.now().strftime('%Y-%m-%d')} 투자 브리핑"
    msg['From'] = NAVER_USER
    msg['To'] = ", ".join(RECIPIENTS)

    html = f"<h2>📅 {datetime.now().strftime('%Y-%m-%d')} 리포트</h2><p>{get_exchange_rate()}</p><hr>"
    imgs = []

    for name, ticker in target_stocks.items():
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty: continue
        
        curr = hist['Close'].iloc[-1]
        diff = curr - hist['Close'].iloc[-2]
        img_path = create_chart(name, ticker, hist)
        
        html += f"<b>{name}</b>: {curr:,.2f} ({diff:+,.2f})<br>"
        html += f'<img src="cid:{ticker}"><br><hr>'
        imgs.append((img_path, ticker))

    msg.attach(MIMEText(html, 'html'))
    for path, cid in imgs:
        with open(path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<{cid}>')
            msg.attach(img)

    print("🚀 [2/3] 네이버 메일 서버에 접속 중...")
    try:
        with smtplib.SMTP_SSL('smtp.naver.com', 465) as server:
            server.login(NAVER_USER, NAVER_PW)
            server.send_message(msg)
        print("✅ [3/3] 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

# [핵심] 이 두 줄이 로봇의 시작 버튼입니다. 반드시 맨 왼쪽 벽에 붙어야 합니다!
if __name__ == "__main__":
    run_stock_bot()
