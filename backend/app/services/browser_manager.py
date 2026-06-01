# app/services/browser_manager.py

from playwright.sync_api import sync_playwright

class BrowserManager:

    def __init__(self):

        self.playwright = sync_playwright().start()

        self.context = (
            self.playwright.chromium
            .launch_persistent_context(
                user_data_dir="./instagram_profile",
                headless=True
            )
        )

    def new_page(self):
        return self.context.new_page()


browser_manager = BrowserManager()