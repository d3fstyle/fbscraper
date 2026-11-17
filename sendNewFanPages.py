# ----------------------------------------------------------------------------------- #
# [Description]: Sends resume of the possible advertisers found                       #
# ----------------------------------------------------------------------------------- #
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from config import scraperEngine, require_env
from datetime import datetime
import pandas as pd
import smtplib


linkList = []
kwList = []
classes = ['odd-row','even-row']  # To alternate colors in rows.
counterKw = 0
counterAd = 0

def generateAdvertiserLinks(row):
  ''' Creates html links from advertisers' dataframe '''
  global counterAd
  linkTemplate = '''\n<tr class="{}"><th class="left-column"><a href="{}">{}</a></th><th class="right-column">{}</th></tr>'''

  name = row['advertiser']
  page = row['page']
  kw = row['foundFromQuery']

  link = linkTemplate.format(classes[counterAd%2],page, name, kw)
  linkList.append(link)
  counterAd += 1

def generateKwLinks(row):
  ''' Creates html links from keywords' dataframe '''
  global counterKw
  template = '''\n<tr class="{}"><th class="left-column"><a href="{}">{}</a></th><th class="right-column">{}</th></tr>'''
  link_to_db = require_env("ADMINER_KW_URL_TEMPLATE")

  kw = row['foundFromQuery']
  if kw:
    count = row['count']
    href = link_to_db.format(kw=kw)

    link = template.format(classes[counterKw%2],href, kw, count)
    kwList.append(link)
    counterKw += 1

def run():
  ''' Main action'''

  date = datetime.strftime(datetime.now(), "%Y-%m-%d")
  sqlTodayPages = f'''SELECT `advertiser`,`page`,`foundFromQuery`
  FROM `fb_possible_advertisers`
  WHERE `date` = '{date}'
  LIMIT 25'''

  sqlCountByKw = '''select `foundFromQuery`, count(*) as count from `fb_possible_advertisers` group by `foundFromQuery`'''

  dfAlready = pd.read_sql(sqlTodayPages,scraperEngine)
  dfAlready.apply(generateAdvertiserLinks, axis=1)

  dfNew = pd.read_sql(sqlCountByKw,scraperEngine)
  dfNew.apply(generateKwLinks, axis=1)

  me = require_env("EMAIL_FROM")
  you = require_env("EMAIL_TO")

  msg = MIMEMultipart('alternative')
  msg['Subject'] = "Possible Advertisers"
  msg['From'] = me
  msg['To'] = you

  text = f'''<div class="title">New possible advertisers. Scrap date: {date}</div><br/>'''
  advertiserList = ''.join(linkList)
  keywordList = ''.join(kwList)
  html = f"""
  <html style="font-family: monospace !important;">
    <head>
      <style>
        html{{
          color:#454545;
        }}
        .title{{
          padding: 20px;
          background-color: #a7bb72;
          color: white;
          font-weight: 600;
          font-size: 1.5em;
          border-radius: 20px 20px 0 0;
        }}
        a {{
          text-decoration:none;
          color:#136788;
        }}
        .left-column{{
          text-align:left;
          padding:10px;
          width:40%;
        }}
        .right-column{{
          width:40%;
        }}
        .even-row{{
          background-color:#d3d7ca;
        }}
        .odd-row{{
          background-color:#e1e6d4;
        }}
        .header{{
          background-color:#d5ec98;
        }}
        .header-2{{
          background-color:#e9f9bf;
        }}
      </style>
    </head>
    <body>
      {text}
      <div style="">
        <div style="float:left;width:50%;">
          <table style="width:100%">
            <tr>
              <th class="header">Advertiser Name</th>
              <th class="header">Query</th>
            </tr>
            {advertiserList}
          </table>
        </div>
        <div style="float:right;width:36%;">
          <table style="width:100%">
            <tr>
              <th class="header" colspan="2">Statistics</th>
            </tr>
            <tr>
              <th class="header-2">Query</th>
              <th class="header-2">Pages found</th>
            </tr>
            {keywordList}
          </table>
        </div>
      </div>
    </body>
  </html>
  """

  # with open('mail.html','w') as file:
  #   file.write(html)


  # Sending the email
  part2 = MIMEText(html, 'html')
  msg.attach(part2)
  s = smtplib.SMTP('smtp.gmail.com', 587)
  s.starttls()
  s.login(me, require_env("GMAIL_APP_PASSWORD"))
  s.sendmail(msg['From'], msg['To'], msg.as_string())
  s.quit()


if __name__ == '__main__':
  run()