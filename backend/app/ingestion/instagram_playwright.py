import re
from playwright.sync_api import sync_playwright


class InstagramPlaywrightExtractor:

    def parse_count(self, value):

        if not value:
            return 0

        value = value.upper().replace(",", "").strip()

        try:

            if value.endswith("K"):
                return int(float(value[:-1]) * 1000)

            if value.endswith("M"):
                return int(float(value[:-1]) * 1000000)

            if value.endswith("B"):
                return int(float(value[:-1]) * 1000000000)

            return int(value)

        except:
            return 0

    def extract(self, reel_url):
        """
        Synchronous Playwright extraction — must be called via
        asyncio.to_thread() from async contexts so it runs in a
        worker thread (avoids Windows SelectorEventLoop subprocess
        transport limitations).
        """
        with sync_playwright() as p:

            context = p.chromium.launch_persistent_context(
                user_data_dir="./instagram_profile",
                headless=True,
            )

            page = context.new_page()

            try:

                page.goto(
                    reel_url,
                    wait_until="domcontentloaded",
                    timeout=90000,
                )

                page.wait_for_timeout(5000)

                og_url = None
                try:
                    og_url = page.locator(
                        'meta[property="og:url"]'
                    ).get_attribute("content", timeout=10000)
                except Exception as e:
                    print(f"Could not get og:url: {e}")

                reel_desc = None
                try:
                    reel_desc = page.locator(
                        'meta[property="og:description"]'
                    ).get_attribute("content", timeout=10000)
                except Exception as e:
                    print(f"Could not get og:description: {e}, trying og:title")
                    try:
                        reel_desc = page.locator(
                            'meta[property="og:title"]'
                        ).get_attribute("content", timeout=10000)
                    except Exception as e2:
                        print(f"Could not get og:title either: {e2}")

                username_match = re.search(
                    r"instagram\.com/([^/]+)/reel",
                    og_url or "",
                    re.IGNORECASE,
                )

                username = (
                    username_match.group(1)
                    if username_match
                    else None
                )

                likes = 0
                comments = 0

                if reel_desc:

                    likes_match = re.search(
                        r'([\d.,]+[KMB]?)\s+likes',
                        reel_desc,
                        re.I,
                    )

                    comments_match = re.search(
                        r'([\d.,]+[KMB]?)\s+comments',
                        reel_desc,
                        re.I,
                    )

                    if likes_match:
                        likes = self.parse_count(likes_match.group(1))

                    if comments_match:
                        comments = self.parse_count(
                            comments_match.group(1)
                        )

                followers = None

                if username:

                    profile_url = (
                        f"https://www.instagram.com/{username}/"
                    )

                    try:
                        page.goto(
                            profile_url,
                            wait_until="domcontentloaded",
                            timeout=60000,
                        )

                        page.wait_for_timeout(3000)

                        profile_desc = page.locator(
                            'meta[property="og:description"]'
                        ).get_attribute("content", timeout=10000)

                        if profile_desc:

                            followers_match = re.search(
                                r'([\d.,]+[KMB]?)\s+Followers',
                                profile_desc,
                                re.I,
                            )

                            if followers_match:
                                followers = self.parse_count(
                                    followers_match.group(1)
                                )
                    except Exception as e:
                        print(f"Could not fetch profile for {username}: {e}")

                return {
                    "creator": username,
                    "creator_id": username,
                    "follower_count": followers,
                    "likes": likes,
                    "comments": comments,
                    "shares": None,
                }

            except Exception as e:
                print(f"Playwright extraction failed: {e}")
                return {
                    "creator": None,
                    "creator_id": None,
                    "follower_count": None,
                    "likes": 0,
                    "comments": 0,
                    "shares": None,
                }
            finally:
                page.close()
                context.close()
