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

# [1. 설정]
NAVER_CLIENT_ID = os.environ.get('NAVER_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_SECRET')
NAVER_USER = os.environ.get('NAVER_USER')
NAVER_PW = os.environ.get('NAVER_PW')
try:
    RECIPIENTS = eval(os.environ.get('RECIPIENTS'))
except:
    RECIPIENTS = [os.environ.get('RECIPIENTS')]

font_path = '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rc('font', family='NanumBarunGothic')
plt.rcParams['axes.unicode_minus'] = False

target_stocks = {
    "삼성전자": "005930.KS",
    "한화에어로스페이스": "012450.KS",
    "휴림로봇": "090710.KQ",
    "코닝(Corning)": "GLW",
    "엔비디아": "NVDA"
}

# [2. 기능 함수들]
def clean_html(text):
    return re.sub('<.*?>', '', text).replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

def get_exchange_rate():
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return f"💵 현재 환율: {usd_krw:,.2f}원"
    except: return "환율 로드 실패"

def create_chart(name, ticker, hist, diff):
    chart_color = 'crimson' if diff >= 0 else 'royalblue'
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hist.index, hist['Close'], color=chart_color, linewidth=2)
    ax.set_title(f"{name} 추세", fontproperties=font_prop)
    img_path = f"{ticker.replace('.', '_')}.png"
    plt.savefig(img_path)
    plt.close()
    return img_path

# [3. 실행 메인 함수]
def start_robot():
    print("🚀 로봇 작동 시작...")
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📈 [자동리포트] {datetime.now().strftime('%Y-%m-%d')} 투자 요약"
    msg['From'] = NAVER_USER
    msg['To'] = ", ".join(RECIPIENTS)

    content_html = f"<h2>📅 {datetime.now().strftime('%Y-%m-%d')} 주식 브리핑</h2><p>{get_exchange_rate()}</p><hr>"
    
    img_attachments = []
    for name, ticker in target_stocks.items():
        print(f"🔍 {name} 데이터 분석 중...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty: continue
        
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        diff = curr - prev
        
        img_path = create_chart(name, ticker, hist, diff)
        content_html += f"📊 <b>{name}</b>: {curr:,.2f}원 ({diff:+,.2f})<br>"
        content_html += f'<img src="cid:{ticker}"><br><hr>'
        img_attachments.append((img_path, ticker))

    msg.attach(MIMEText(content_html, 'html'))
    for img_path, cid in img_attachments:
        with open(img_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<{cid}>')
            msg.attach(img)

    print("📧 메일 발송 중...")
    with smtplib.SMTP_SSL('smtp.naver.com', 465) as server:
        server.login(NAVER_USER, NAVER_PW)
        server.send_message(msg)
    print("✅ 발송 완료!")

# [4. 실제 시작 버튼 - 맨 왼쪽 벽에 붙임]
if __name__ == "__main__":
    start_robot()
