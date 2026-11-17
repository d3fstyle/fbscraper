"""Quick Playwright smoke test for Meta Ads Library login."""

from playwright.sync_api import Playwright, sync_playwright

from config import FB_PASS, FB_USER


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.facebook.com/ads/library/?active_status=all")
    page.get_by_role("button", name="Only allow essential cookies").click()
    page.get_by_role("menuitem", name="Open navigation panel").click()
    page.get_by_role("link", name="Sign in").click()
    page.wait_for_url("https://www.facebook.com/")

    page.get_by_test_id("royal_email").fill(FB_USER)
    page.get_by_test_id("royal_email").press("Tab")
    page.get_by_test_id("royal_pass").fill(FB_PASS)
    page.get_by_test_id("royal_pass").press("Enter")
    page.wait_for_url("https://www.facebook.com/")

    page.goto(
        "https://www.facebook.com/ads/library/"
        "?active_status=all&ad_type=political_and_issue_ads&country=ES&media_type=all"
    )

    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
