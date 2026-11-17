# ------------------------------------------------------------------------------- #
# [Description]: Gets new advertisers and retrieve its page id for future searchs #
# [Inputs]: table fb_unique_advertisers, fb_pages                                 #
# [Outputs]: tables fb_pages                                                      #
# ------------------------------------------------------------------------------- #

from playwright.sync_api import Playwright, sync_playwright
from bs4 import BeautifulSoup as bs
from config import scraperEngine
from icecream import ic
import pandas as pd
import re

#GETPAGESQUERY = '''select advertiser, advertiser_page from fb_unique_advertisers where advertiser_page is not null'''
GETPAGESQUERY = '''select advertiser, advertiser_page from fb_unique_advertisers where advertiser_page not in (select advertiser_page from fb_pages)'''
GETSTOREDPAGESQUERY = '''select url, pageid, feed, valid from fb_pages'''
PATTERN = r'"associated_page_id":"(\d+)"'

def run_once(f):
    ''' Decorator to run only once'''
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper


class RetrievePages():

    def __init__(self):
        self.storedPages = None  # To hold pages already set in db
        self.newPages = None  # To hold new pages scraped and in need to be processed
        self.newPageWithId = pd.DataFrame(
            {
                'url':pd.Series(dtype='str'),
                'pageid':pd.Series(dtype='str'),
                'feed':pd.Series(dtype='str'),
                'valid':pd.Series(dtype='int')
            })
        self.lostRows = pd.DataFrame(
            {
                'url':pd.Series(dtype='str'),
                'advertiser':pd.Series(dtype='str')
            })
        
    @run_once
    def allowCookiesFromPage(self, pageObject):
        ''' Run once for fb page '''
        pageObject.get_by_role("button", name="Only allow essential cookies").first.click()
        return

    def getPages(self):
        ''' Retrieves all scraped pages '''
        self.newPages = pd.read_sql(GETPAGESQUERY, scraperEngine)


    def getStoredPages(self):
        ''' Retrieves all scraped pages '''
        self.storedPages = pd.read_sql(GETSTOREDPAGESQUERY, scraperEngine)


    def appendToDb(self, newRows):
        ''' Appends new pages with its id and feed to db '''
        newRows.to_sql(
            'fb_pages',
            con=scraperEngine,
            index=False,
            if_exists='append',
            chunksize=10000
        )

    def run(self, playwright: Playwright):
        ''' Main '''
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        self.getStoredPages()
        self.getPages()
        
        for index, row in self.newPages.iterrows():
            page.goto(row['advertiser_page'])
            self.allowCookiesFromPage(page)
            html = page.content()
            soup = bs(html, 'html.parser')

            match = re.search(PATTERN, str(soup))
            if match:
                message_box_id = match.group(1)
                print('[INFO] - Advertiser "%s" has the id %s' %(row['advertiser'], message_box_id))
                newRow = {
                'url':[row['advertiser_page']],
                'pageid':[message_box_id],
                'feed':['sedo'],
                'valid':[1]
                }
                self.newPageWithId = pd.concat([self.newPageWithId, pd.DataFrame(newRow)])
            else:
                print('[ERROR] - No id found for "%s"' % row['advertiser'])
                lostRow = {
                    'url':[row['advertiser_page']],
                    'name':[row['advertiser']]
                }
                self.lostRows = pd.concat([self.lostRows, pd.DataFrame(lostRow)])
        
        merged  = pd.merge(self.newPageWithId, self.storedPages, how='outer', indicator=True)
        merged = merged.drop_duplicates(subset='pageid', keep=False)
        newRows = merged[merged['_merge']=='left_only'].drop(columns=['_merge'])
        newRows.to_csv('NewPagesToAdd.csv',index=False)
        self.lostRows.to_csv('MissingIds.csv')
        self.appendToDb(newRows)
        context.close()
        browser.close()

if __name__ == '__main__':
    rp = RetrievePages()
    with sync_playwright() as playwright:
        rp.run(playwright)
