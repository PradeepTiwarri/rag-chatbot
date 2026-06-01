from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(
        user_data_dir="./instagram_profile",
        headless=False
    )

    page = context.new_page()

    page.goto("https://www.instagram.com/")

    print("Login manually.")
    input("Press Enter after login...")

    context.close()