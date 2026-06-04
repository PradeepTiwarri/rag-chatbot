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
        Extract Instagram reel data using script tag JSON parsing.
        This is more reliable than meta tag scraping.
        """
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir="./instagram_profile",
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            page = context.new_page()

            try:
                page.goto(reel_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)

                # Method 1: Extract from script tags (most reliable)
                scripts = page.locator("script").all()
                target_script = None

                for script in scripts:
                    try:
                        txt = script.text_content()
                        if txt and "xdt_api__v1__clips__home__connection_v2" in txt:
                            target_script = txt
                            break
                    except:
                        pass

                if target_script:
                    # Extract data using regex patterns
                    username = self._extract_regex(r'"username":"([^"]+)"', target_script)
                    like_count = self._extract_regex(r'"like_count":(\d+)', target_script)
                    comment_count = self._extract_regex(r'"comment_count":(\d+)', target_script)
                    view_count = self._extract_regex(r'"view_count":(null|\d+)', target_script)
                    
                    # Handle view_count (can be "null")
                    if view_count and view_count != "null":
                        views = int(view_count)
                    else:
                        views = None
                    
                    likes = int(like_count) if like_count else 0
                    comments = int(comment_count) if comment_count else 0
                    
                    print(f"Script extraction - username: {username}, likes: {likes}, comments: {comments}, views: {views}")
                else:
                    # Fallback to meta tag extraction
                    print("Script tag not found, falling back to meta tags...")
                    og_url = self._get_meta_content(page, 'meta[property="og:url"]')
                    reel_desc = self._get_meta_content(page, 'meta[property="og:description"]')
                    
                    username = self._extract_username_from_url(og_url)
                    likes, comments = self._extract_likes_comments_from_desc(reel_desc)
                    views = None

                # Get follower count from profile page
                followers = None
                if username:
                    followers = self._get_follower_count(page, username)

                return {
                    "creator": username,
                    "creator_id": username,
                    "follower_count": followers,
                    "likes": likes,
                    "comments": comments,
                    "views": views,
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
                    "views": None,
                    "shares": None,
                }
            finally:
                page.close()
                context.close()

    def _extract_regex(self, pattern: str, text: str) -> str:
        """Extract first matching group from text using regex"""
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _get_meta_content(self, page, selector: str, timeout: int = 5000) -> str:
        """Get meta tag content safely"""
        try:
            return page.locator(selector).get_attribute("content", timeout=timeout)
        except Exception:
            return None

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
        """Get follower count from profile page using script tag first, then meta"""
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            print(f"Fetching profile for {username}...")
            
            page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Try script tag first (more reliable)
            scripts = page.locator("script").all()
            for script in scripts:
                try:
                    txt = script.text_content()
                    if txt and 'edge_followed_by' in txt:
                        # Look for follower count in the JSON
                        match = re.search(r'"edge_followed_by":\s*{\s*"count":\s*(\d+)', txt)
                        if match:
                            followers = int(match.group(1))
                            print(f"Found followers via script: {followers}")
                            return followers
                except:
                    pass
            
            # Fallback to meta tag
            description = page.locator('meta[property="og:description"]').get_attribute("content", timeout=5000)
            if description:
                match = re.search(r'([\d.,]+[KMB]?)\s+Followers', description, re.I)
                if match:
                    followers = self.parse_count(match.group(1))
                    print(f"Found followers via meta: {followers}")
                    return followers
            
            return None
            
        except Exception as e:
            print(f"Could not fetch follower count for {username}: {e}")
            return None
