import re
import json
from playwright.sync_api import sync_playwright


class InstagramPlaywrightExtractor:

    def parse_count(self, value):
        if not value:
            return 0
        if isinstance(value, int):
            return value
        value = str(value).upper().replace(",", "").strip()
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
        Extract Instagram reel data using Playwright.
        Follows the same reliable pattern as get_instagram_reel_data.
        """
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir="/app/instagram_profile",
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            page = context.new_page()

            try:
                # Step 1: Go to reel page
                page.goto(reel_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # Step 2: Get og:url to extract username
                og_url = page.locator('meta[property="og:url"]').get_attribute("content", timeout=10000)
                username = self._extract_username_from_url(og_url)
                
                # Step 3: Try to get likes/comments from script tag first
                likes = 0
                comments = 0
                
                scripts = page.locator("script").all()
                for script in scripts:
                    try:
                        txt = script.text_content()
                        if txt and "xdt_api__v1__clips__home__connection_v2" in txt:
                            like_count = self._extract_regex(r'"like_count":(\d+)', txt)
                            comment_count = self._extract_regex(r'"comment_count":(\d+)', txt)
                            if like_count:
                                likes = int(like_count)
                            if comment_count:
                                comments = int(comment_count)
                            print(f"Script extraction - likes: {likes}, comments: {comments}")
                            break
                    except:
                        pass
                
                # If script didn't work, try meta description
                if likes == 0:
                    reel_desc = page.locator('meta[property="og:description"]').get_attribute("content", timeout=10000)
                    if reel_desc:
                        likes, comments = self._extract_likes_comments_from_desc(reel_desc)
                        print(f"Meta extraction - likes: {likes}, comments: {comments}")
                
                # Step 4: Get follower count from profile page
                followers = None
                if username:
                    followers = self._get_follower_count(page, username)

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

    def _extract_regex(self, pattern: str, text: str) -> str:
        """Extract first matching group from text using regex"""
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _extract_username_from_url(self, og_url: str) -> str:
        """Extract username from og:url"""
        if not og_url:
            return None
        match = re.search(r"instagram\.com/([^/]+)/reel", og_url, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_likes_comments_from_desc(self, description: str):
        """Extract likes and comments from meta description"""
        likes = 0
        comments = 0
        if description:
            likes_match = re.search(r'([\d.,]+[KMB]?)\s+likes', description, re.I)
            comments_match = re.search(r'([\d.,]+[KMB]?)\s+comments', description, re.I)
            if likes_match:
                likes = self.parse_count(likes_match.group(1))
            if comments_match:
                comments = self.parse_count(comments_match.group(1))
        return likes, comments

    def _get_follower_count(self, page, username: str) -> int:
        """Get follower count from profile page using multiple methods"""
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            print(f"Fetching profile for {username}...")
            
            # Navigate to profile page
            page.goto(profile_url, wait_until="networkidle", timeout=60000)
            
            # Wait longer for content to load
            page.wait_for_timeout(5000)
            
            # Method 1: Try script tag (most reliable)
            scripts = page.locator("script").all()
            for script in scripts:
                try:
                    txt = script.text_content()
                    if txt and ('edge_followed_by' in txt or 'follower_count' in txt):
                        # Try different regex patterns
                        match = re.search(r'"edge_followed_by":\s*{\s*"count":\s*(\d+)', txt)
                        if not match:
                            match = re.search(r'"follower_count":\s*(\d+)', txt)
                        if match:
                            followers = int(match.group(1))
                            print(f"Found followers via script: {followers}")
                            return followers
                except:
                    pass
            
            # Method 2: Wait for meta description with retry
            for attempt in range(3):
                try:
                    description = page.locator('meta[property="og:description"]').get_attribute("content", timeout=10000)
                    if description:
                        # Try different patterns
                        match = re.search(r'([\d.,]+[KMB]?)\s+Followers', description, re.I)
                        if not match:
                            match = re.search(r'([\d.,]+[KMB]?)\s+followers', description, re.I)
                        if match:
                            followers_raw = match.group(1)
                            followers = self.parse_count(followers_raw)
                            print(f"Found followers via meta: {followers} ({followers_raw})")
                            return followers
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    page.wait_for_timeout(2000)
            
            # Method 3: Try to get from page title or body
            try:
                page.wait_for_selector('header section', timeout=10000)
                content = page.content()
                match = re.search(r'([\d.,]+[KMB]?)\s+Followers', content, re.I)
                if match:
                    followers_raw = match.group(1)
                    followers = self.parse_count(followers_raw)
                    print(f"Found followers via page content: {followers} ({followers_raw})")
                    return followers
            except:
                pass
            
            print(f"No follower count found for {username}")
            return None
            
        except Exception as e:
            print(f"Could not fetch follower count for {username}: {e}")
            return None
