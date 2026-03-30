
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

# 1. 깃허브 환경변수 설정
NAVER_CLIENT_ID = os.environ.get('NAVER_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_SECRET')
NAVER_USER = os.environ.get('NAVER_USER')
NAVER_PW = os.environ.get('NAVER_PW')
try:
    RECIPIENTS = eval(os.environ.get('RECIPIENTS'))
except:
    RECIPIENTS = [os.environ.get('RECIPIENTS')]

# 2. 폰트 및 종목 설정
font_path = '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rc('font', family='NanumBarunGothic')
plt.rcParams['axes.unicode_minus'] = False

target_stocks = {
    "삼성전자": "005930.KS",
    "한화에어로스페이스": "012450.KS",
    "휴림로봇": "090710.KQ",
    "KODEX 미국S&P500": "379800.KS",
    "코닝(Corning)": "GLW",
    "SCHD (배당ETF)": "SCHD",
    "엔비디아": "NVDA",
    "테슬라": "TSLA"
}

def clean_html(text):
    return re.sub('<.*?>', '', text).replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

def get_exchange_rate():
    try:
        usd_krw = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return f"💵 현재 환율: {usd_krw:,.2f}원"
    except:
        return "💵 환율 정보를 가져올 수 없습니다."

def create_upgraded_chart(name, ticker, hist, diff):
    is_kr = ".KS" in ticker or ".KQ" in ticker
    unit = "원" if is_kr else "$"
    chart_color = 'crimson' if diff >= 0 else 'royalblue'
    if not is_kr: chart_color = 'forestgreen' if diff >= 0 else 'crimson'
    
    hist['MA5'] = hist['Close'].rolling(window=5).mean()
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hist.index, hist['Close'], color=chart_color, linewidth=2.5, label='종가')
    ax.fill_between(hist.index, hist['Close'], hist['Close'].min()*0.99, color=chart_color, alpha=0.1)
    
    # 주요 지점 가격 표시
    interval = 5
    for i in range(0, len(hist), interval):
        ax.text(hist.index[i], hist['Close'].iloc[i], f"{hist['Close'].iloc[i]:,.0f}", 
                fontproperties=font_prop, fontsize=9, ha='center', va='bottom')

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.xticks(rotation=45, fontproperties=font_prop)
    ax.set_title(f"{name} ({ticker}) 추세", fontproperties=font_prop, fontsize=15, fontweight='bold')
    
    plt.tight_layout()
    img_path = f"{ticker.replace('.', '_')}.png"
    plt.savefig(img_path, dpi=100)
    plt.close()
    return img_path

def get_stock_details(name, ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    if hist.empty: return f"📊 <b>{name}</b>: 데이터 없음<br>", None
    curr = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2]
    diff, pct = curr - prev, ((curr - prev) / prev) * 100
    info = stock.info
    cap_val = info.get('marketCap', 0) / (10**12 if ".K" in ticker else 10**9)
    img_path = create_upgraded_chart(name, ticker, hist, diff)
    report = f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>"
    report += f"📊 <b>{name} ({ticker})</b><br>"
    report += f"현재가: {curr:,.2f} ({diff:+,.2f}, {pct:+.2f}%)<br>시총: {cap_val:,.1f} / PER: {info.get('trailingPE','N/A')}</div>"
    return report, img_path

def get_detailed_news(name):
    url = f"https://openapi.naver.com/v1/search/news.json?query={name}&display=2&sort=sim"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    try:
        items = requests.get(url, headers=headers).json().get('items', [])
        news_html = "<b>📰 뉴스 요약:</b><br>"
        for i, item in enumerate(items, 1):
            news_html += f"{i}. <a href='{item['link']}'>{clean_html(item['title'])}</a><br>"
        return news_html + "<br>"
    except: return "뉴스 로드 실패<br>"

def send_report():
    msg = MIMEMultipart('related')
    msg['Subject'] = f"📈 [자동리포트] {datetime.now().strftime('%Y-%m-%d')} 투자 요약"
    msg['From'] = NAVER_USER
    msg['To'] = ", ".join(RECIPIENTS)
    content_html = f"<h2>📅 {datetime.now().strftime('%Y-%m-%d')} 주식 브리핑</h2><p>{get_exchange_rate()}</p><hr>"
    img_attachments = []
    for name, ticker in target_stocks.items():
        text, img_path = get_stock_details(name, ticker)
        news = get_detailed_news(name)
        content_html += text + news
        if img_path:
            content_html += f'<img src="cid:{ticker}"><br><hr>'
            img_attachments.append((img_path, ticker))
    msg.attach(MIMEText(content_html, 'html'))
    for img_path, cid in img_attachments:
        with open(img_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<{cid}>')
            msg.attach(img)
    with smtplib.SMTP_SSL('smtp.naver.com', 465) as server:
        server.login(NAVER_USER, NAVER_PW)
        server.send_message(msg)

# 이 부분이 반드시 맨 왼쪽 끝에 있어야 합니다!
if __name__ == "__main__":
 send_report()
