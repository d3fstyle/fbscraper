# ----------------------------------------------------------------------------------- #
# [Description]: Sends resume of the scrapping session by email                       #
# ----------------------------------------------------------------------------------- #
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from config import scraperEngine, require_env
from datetime import datetime
from tabulate import tabulate
import os
import pandas as pd
import smtplib


def run():
  ''' Main action'''

  date = datetime.strftime(datetime.now(), "%Y-%m-%d")
  sqlAlreadySeenAds = f'''SELECT `seen_count`,`clones`,`copy`
  FROM `fb_ads_filtered`
  WHERE `date` = '{date}'
  ORDER BY `seen_count` DESC, `clones` DESC
  LIMIT 10'''

  sqlNewAdsByClones = f'''SELECT `seen_count`,`clones`,`copy`
  FROM `fb_ads_filtered`
  WHERE `date` = '{date}'
  ORDER BY `seen_count`, `clones` DESC
  LIMIT 10'''

  dfAlready = pd.read_sql(sqlAlreadySeenAds,scraperEngine)
  dfAlready = dfAlready.reset_index(drop=True)
  dfAlreadyString = tabulate(dfAlready,headers=['Count', 'Clones', 'Copy'],showindex="false",tablefmt='html', numalign="center")

  dfNew = pd.read_sql(sqlNewAdsByClones,scraperEngine)
  dfNew = dfNew.reset_index(drop=True)
  dfNewString = tabulate(dfNew,headers=['Count', 'Clones', 'Copy'],showindex="false",tablefmt='html', numalign="center")

  me = require_env("EMAIL_FROM")
  you = require_env("EMAIL_TO")
  bcc = os.environ.get("EMAIL_BCC", "")

  msg = MIMEMultipart('alternative')
  msg['Subject'] = "Scraping session results"
  msg['From'] = me
  msg['To'] = you
  if bcc:
    msg['Cc'] = bcc

  adminer_ads_url = require_env("ADMINER_ADS_URL_TEMPLATE").format(date=date)

  text = f'''<div class="first">Already seen ads, ordered by 'seen count' and clones.</div>{dfAlreadyString}<br/><div class="second">New ads, ordered by clones.</div>{dfNewString}'''
  html = f"""
  <html style="font-family: monospace !important;">
    <head>
    <style>
      a {{
        color:#c60b0b;
      }}
      .table-name{{
        background-color: #ee925c;
        color: white;
        font-weight: 600;
        font-size: 1.6em;
        padding: 10px 20px;
        border-radius: 10px;
      }}
      table{{
        border-radius: 0 10px 10px 10px;
        padding: 10px;
        overflow: hidden;
        font-family: inherit;
        background-color: #ffe7d9;
      }}
      .first, .second{{
        background-color: #fbcaad;
        padding: 5px 15px;
        border-radius: 10px 10px 0 0px;
        font-weight: 600;
        color: #732b01;
        width: 50%;
      }}
      .date {{
        background-color: #fbcaad;
        width: 13%;
        text-align: center;
        padding: 22px 0;
        border-radius: 10px 10px 0 0;
      }}
    </style>
    </head>
    <body>
      <div class="table-name"><a href="{adminer_ads_url}" style="text-decoration:none;">Filtered Ads</a> Date: {date}</div>
      <p>{text}</p>
    </body>
  </html>
  """

  # Sending the email
  part2 = MIMEText(html, 'html')
  msg.attach(part2)
  s = smtplib.SMTP('smtp.gmail.com', 587)
  s.starttls()
  s.login(me, require_env("GMAIL_APP_PASSWORD"))
  recipients = msg['To'].split(',')
  if bcc:
    recipients = recipients + bcc.split(',')
  s.sendmail(msg['From'], recipients, msg.as_string())
  s.quit()


if __name__ == '__main__':
  run()