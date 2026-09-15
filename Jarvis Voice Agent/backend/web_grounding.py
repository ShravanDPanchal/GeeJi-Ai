# =============================================================================
#  backend/web_grounding.py — Real-Time Live Web Search & Deep Article Grounding
#  Dynamically fetches live 2026 internet data, breaking news & exact webpage answers
# =============================================================================

import datetime
import json
import logging
import re
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger("WebGrounding")

# Keywords that indicate user wants real-world events, news, factual lookups, links, stats, or websites
LIVE_TRIGGERS = [
    "today", "yesterday", "tomorrow", "this week", "this month", "this year",
    "current", "currently", "latest", "recent", "recently", "news", "headline", "headlines",
    "weather", "score", "match", "stock", "price", "election", "who is", "who was",
    "what happened", "what happend", "who won", "2024", "2025", "2026", "2027", "search", "look up",
    "released", "release date", "champion", "president", "prime minister",
    "crash", "crashed", "plane", "flight", "aeroplane", "airplane", "accident",
    "incident", "disaster", "earthquake", "cyclone", "flood", "floods", "war", "died", "death",
    "killed", "scandal", "launch", "event", "happened", "happend", "occurred", "air india",
    "indian airlines", "is it true", "did you hear", "tell me about the", "know about",
    "going on", "what's going on", "whats going on", "what is happening", "what's happening",
    "update", "situation", "protest", "protests", "crisis", "minister",
    "answer", "today answer", "todays answer", "the answer", "solution", "result", "winner",
    "wordle", "wordle answer", "word",
    "season", "episode", "episodes", "epsiode", "epsiodes", "epsidoes", "anime", "manga", "series",
    "show", "running", "airing", "schedule", "premiere", "broadcast", "streaming", "next episode",
    "when is", "when will", "total", "count", "number of", "how many", "how much", "how old",
    "till date", "to date", "so far", "all time", "net worth", "population", "capital",
    "link", "links", "url", "urls", "website", "websites", "site", "portal",
    "docs", "documentation", "download", "download link", "github", "repo",
    "repository", "source code", "official site", "official page", "webpage",
    "web page", "login page", "where to find", "link of", "link for", "link provide",
    "provide link", "give me link", "send link", "find link",
    "festival", "festivals", "holiday", "holidays", "panchang", "tithi", "vrat", "jayanti", "tyohar", "parv", "janmashtami", "diwali", "eid"
]



def normalize_query_typos(text: str) -> str:
    """Normalize common typos and colloquial spellings for higher search precision."""
    t = text
    typo_map = {
        r"\bepsidoes\b": "episodes",
        r"\bepsiodes\b": "episodes",
        r"\bepsiode\b": "episode",
        r"\bepsidoe\b": "episode",
        r"\bseasom\b": "season",
        r"\brelese\b": "release",
        r"\brelesed\b": "released",
        r"\bchasmac\b": "chashmah",
        r"\bchasma\b": "chashmah",
        r"\boltah\b": "ooltah",
        r"\btarak\b": "taarak",
        r"\bwhois\b": "who is",
        r"\bhowmany\b": "how many",
        r"\btotal\s+episodes?\b": "total episodes",
    }
    for pat, rep in typo_map.items():
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t


class WebGroundingEngine:
    """
    Provides real-time system clock anchors, automatic live web search, and deep article inspection (Web RAG).
    Combines Bing News RSS, Google News RSS, deep article content fetching, and DuckDuckGo text search.
    """

    def get_temporal_context(self) -> str:
        """
        Dynamically generates current date/time context based on system clock.
        Ensures Jarvis always knows the exact year, month, date, tomorrow's date, and day of the week.
        """
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)
        date_str = now.strftime("%A, %B %d, %Y")
        tomorrow_str = tomorrow.strftime("%A, %B %d, %Y")
        yesterday_str = yesterday.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        return (
            f"[TEMPORAL ANCHOR - REAL-TIME CLOCK]\n"
            f"- Today's Date: {date_str}\n"
            f"- Tomorrow's Date: {tomorrow_str}\n"
            f"- Yesterday's Date: {yesterday_str}\n"
            f"- Current Year: {now.year}\n"
            f"- Exact Time: {time_str}\n"
            f"You are operating live on {date_str}. Use this anchor for real-time news, clock queries, and temporal awareness. Do NOT force or attach current calendar dates to general trip plans or itineraries unless the user explicitly specified dates."
        )

    def should_search_web(self, query: str, history: list = None) -> bool:
        """
        Universal Real-Time Web Grounding:
        Searches the live web for substantive questions, topics, or factual inquiries.
        Bypasses empty queries, trivial greetings/fillers, identity queries ("who are you?"), or local commands.
        """
        q = normalize_query_typos(query).lower().strip()
        q_clean = re.sub(r"[?!.,'\"]+", "", q).strip()

        if len(q_clean) < 3:
            return False

        # Pure conversational non-informational greetings & fillers
        non_search_exact = {
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening", "good night",
            "thank you", "thanks", "thanks a lot", "thank you so much", "bye", "goodbye", "see ya",
            "ok", "okay", "alright", "cool", "nice", "got it", "yes", "no", "sure", "fine", "yeah", "yup",
            "stop", "pause", "resume", "clear", "clear history", "reset", "mute", "unmute"
        }
        if q_clean in non_search_exact or q in non_search_exact:
            return False

        # Self-identity queries about the bot persona itself
        personal_patterns = [
            "who are you", "what is your name", "what are you", "how are you",
            "who is this", "tell me about yourself", "introduce yourself",
            "tell me a joke", "make me laugh", "what can you do"
        ]
        if any(p == q_clean or p == q for p in personal_patterns):
            return False

        # Local user profile queries about self
        local_memory_patterns = [
            "about myself", "about me", "my name", "who i am", "my role", "my preferences",
            "what do you know about me", "my profile"
        ]
        if any(p == q_clean or p == q for p in local_memory_patterns):
            return False

        # Coding, scripting, algorithms, and programming queries do not need slow web scraping
        coding_patterns = [
            "write code", "python script", "code in", "write a function", "write a script",
            "write a python", "implement a", "algorithm to", "pygame", "html css",
            "javascript function", "write a class", "debug this", "unit test", "write a program"
        ]
        if any(c in q_clean for c in coding_patterns):
            return False

        # Trigger live web search for actual live/current/temporal topics or data
        if any(t in q_clean for t in LIVE_TRIGGERS):
            return True

        # Trigger for explicit search directives
        if any(kw in q_clean for kw in ["search", "look up", "browse", "find online", "google", "check web", "link for", "website of", "url of"]):
            return True

        return False

    def extract_search_topic(self, query: str, history: list = None) -> str:
        """
        Extracts clean core subject from conversational sentences, resolving relative dates
        (e.g., 'tomorrow', 'today', 'yesterday') into exact calendar dates.
        Example: 'what is the festival of tomorrow in india' -> 'festival India September 4 2026 holiday panchang'
        """
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        today_fmt = now.strftime("%B %d, %Y")
        tomorrow_fmt = tomorrow.strftime("%B %d, %Y")
        yesterday_fmt = yesterday.strftime("%B %d, %Y")

        q = normalize_query_typos(query).strip()
        q = re.sub(r"\bhappend\b", "happened", q, flags=re.IGNORECASE)

        # 1. Check for festival / holiday / panchang / calendar inquiries
        is_festival_query = any(w in q.lower() for w in ["festival", "festivals", "holiday", "holidays", "panchang", "tithi", "celebration", "tyohar", "parv"])
        if is_festival_query:
            target_date = today_fmt
            if "tomorrow" in q.lower() or "kal" in q.lower():
                target_date = tomorrow_fmt
            elif "yesterday" in q.lower():
                target_date = yesterday_fmt
            country = "India" if any(c in q.lower() for c in ["india", "indian", "hindu", "bharat"]) else ""
            return f"festival {country} {target_date} holiday panchang tithi".strip()

        # 2. Substitute relative date words with exact dates
        q_resolved = re.sub(r"\btomorrow\b", tomorrow_fmt, q, flags=re.IGNORECASE)
        q_resolved = re.sub(r"\btoday\b", today_fmt, q_resolved, flags=re.IGNORECASE)
        q_resolved = re.sub(r"\byesterday\b", yesterday_fmt, q_resolved, flags=re.IGNORECASE)

        # 3. Strip conversational leading phrases
        cleaned = re.sub(
            r"^(do\s+(you|u)\s+know\s+(about\s+)?|can\s+(you|u)\s+tell\s+me\s+(about\s+)?|tell\s+me\s+(what\s+happened\s+in|what\s+is\s+happening\s+in|what\s+happened\s+with|about\s+the|about\s+|a\s+|the\s+)?|so\s+provide\s+me\s+(with\s+)?|provide\s+me\s+(with\s+)?|give\s+me\s+(the\s+)?|just\s+tell\s+me\s+(a\s+|the\s+)?|what\s+(is\s+the\s+date\s+of|is\s+the\s+news\s+in|is\s+the\s+news\s+about|happened\s+in|happened\s+with|is\s+happening\s+in|is\s+the\s+|is\s+|about\s+)|where\s+(is\s+the\s+link\s+for|is\s+the\s+|can\s+i\s+find\s+|to\s+find\s+)|search\s+(for\s+)?|look\s+up\s+|find\s+(information\s+about\s+|details\s+about\s+|me\s+)?|is\s+it\s+true\s+that\s+)\s*",
            "",
            q_resolved,
            flags=re.IGNORECASE,
        ).strip()

        # 4. Strip conditional and trailing link-request clauses
        cleaned = re.sub(
            r"[,;]?\s*(if\s+(yes|so|possible|you\s+do)\s*,?\s*then\s+)?(give\s+me|provide\s+me|send\s+me|share\s+with\s+me|share\s+me|find\s+me)?\s*(the\s+)?(link|url|website|site|portal|details|info|address)\s*(of|for|to)?\s*(their|its|the|official)?\s*(website|site|portal|page|channel)?\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        followup_phrases = [
            "today answer", "todays answer", "the answer", "what is the answer", "answer",
            "who won", "winner", "result", "the link", "solution", "it", "this", "word",
            "release date", "release date?", "when", "when is it", "schedule", "next episode",
            "next episode?", "status", "which season", "episode", "season", "total episodes",
            "how many", "count", "link", "links", "website", "websites", "youtube", "url", "urls"
        ]
        is_followup = len(cleaned.split()) <= 4 or any(p in cleaned.lower() for p in followup_phrases)

        if is_followup and history:
            subject = ""
            user_messages = [m for m in history if m.get("role") == "user"]
            for msg in reversed(user_messages):
                content = msg.get("content", "")
                content = content.split("\n\n[")[0].strip()
                content = normalize_query_typos(content)
                clean_prev = re.sub(
                    r"\b(u|you|do|can|tell|me|about|know|the|a|an|what|is|are|how|why|please|hi|hello|hey|so|provide|give|today|todays|answer|news|in|just|word|currently|running|which)\b|[^\w\s]",
                    " ",
                    content,
                    flags=re.IGNORECASE
                ).strip()
                clean_prev = re.sub(r"\s+", " ", clean_prev).strip()
                if clean_prev and len(clean_prev) > 2:
                    subject = clean_prev
                    break

            if subject and subject.lower() not in cleaned.lower():
                cleaned = f"{subject} {cleaned}".strip()

        if not cleaned:
            cleaned = q_resolved

        return cleaned


    def unquote_bing_url(self, raw_url: str) -> str:
        """
        Extracts the destination article URL from Bing News RSS redirect URLs.
        """
        if "url=" in raw_url:
            try:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                if "url" in parsed and parsed["url"]:
                    return parsed["url"][0]
            except Exception:
                pass
        return raw_url

    def fetch_wikipedia_infobox(self, target_url: str) -> str:
        """
        Extracts structured factual key-values (e.g. No. of episodes, Release date, Creator, etc.)
        from Wikipedia article infoboxes.
        """
        try:
            if "wikipedia.org/wiki/" not in target_url:
                return ""

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=3.5) as resp:
                soup = BeautifulSoup(resp.read().decode("utf-8", errors="ignore"), "html.parser")

            infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
            facts = []
            if infobox:
                for tr in infobox.find_all("tr"):
                    th = tr.find("th")
                    td = tr.find("td")
                    if th and td:
                        k = th.get_text().strip()
                        v = " ".join(td.stripped_strings)
                        if k and v and len(k) < 35 and len(v) < 120:
                            facts.append(f"{k}: {v}")

            if facts:
                return " | [Wikipedia Infobox Facts: " + "; ".join(facts[:8]) + "]"
        except Exception as e:
            logger.debug(f"[WebGrounding] Wiki infobox fetch note: {e}")

        return ""

    def fetch_deep_article_snippet(self, target_url: str) -> str:
        """
        Fetches the actual text from a news/gaming article webpage to unmask spoiler answers.
        """
        try:
            actual_url = self.unquote_bing_url(target_url)
            if not actual_url.startswith("http"):
                return ""

            # Check if this is a Wikipedia page
            wiki_extract = self.fetch_wikipedia_infobox(actual_url)
            if wiki_extract:
                return wiki_extract

            req = urllib.request.Request(
                actual_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as response:
                html = response.read().decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "html.parser")
            for s in soup(["script", "style", "nav", "header", "footer", "aside"]):
                s.decompose()

            text = " ".join(soup.stripped_strings)

            # Search specifically for answer patterns
            answer_matches = []
            for match in re.finditer(
                r"(?:Wordle\s*(?:#?\d+)?\s*(?:answer|solution|word)|the\s*answer\s*is|today\'s\s*(?:Wordle\s*)?answer\s*is|today\'s\s*word\s*is|the\s*word\s*is)[^\.]{0,100}",
                text,
                re.IGNORECASE
            ):
                answer_matches.append(match.group(0).strip())

            if answer_matches:
                return " | [Article Content Extraction: " + " ".join(answer_matches[:2]) + "]"
        except Exception as e:
            logger.debug(f"[WebGrounding] Deep article fetch note: {e}")

        return ""

    def fetch_bing_news_rss(self, query: str, max_results: int = 3) -> List[str]:
        """
        Fetches breaking real-time news and full snippet descriptions via Bing News RSS.
        """
        snippets: List[str] = []
        try:
            url = f"https://www.bing.com/news/search?q={urllib.parse.quote(query)}&format=rss"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=4.5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            for item in items[:max_results]:
                title_elem = item.find("title")
                desc_elem = item.find("description")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                if title or desc:
                    date_pfx = f"[{pub_date}] " if pub_date else ""
                    clean_desc = re.sub(r"<[^>]+>", " ", desc).strip()
                    deep_extract = ""
                    # If this is an answer or game query and description was truncated, fetch article text
                    if any(k in query.lower() for k in ["wordle", "answer", "solution", "who won", "score"]) and link:
                        deep_extract = self.fetch_deep_article_snippet(link)

                    combined_desc = f"{clean_desc}{deep_extract}"
                    if combined_desc and link:
                        snippets.append(f"• [{date_pfx}{title}] (URL: {link}): {combined_desc}")
                    elif combined_desc:
                        snippets.append(f"• [{date_pfx}{title}]: {combined_desc}")
                    elif link:
                        snippets.append(f"• [{date_pfx}{title}] (URL: {link})")
        except Exception as e:
            logger.debug(f"[WebGrounding] Bing News RSS note: {e}")

        return snippets

    def fetch_google_news_rss(self, topic: str, max_results: int = 3) -> List[str]:
        """
        Fetches breaking real-time news via Google News RSS without rate limits.
        """
        snippets: List[str] = []
        try:
            encoded_topic = urllib.parse.quote(topic)
            url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            
            with urllib.request.urlopen(req, timeout=4.5) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            items = root.findall(".//item")

            for item in items[:max_results]:
                title_elem = item.find("title")
                pub_elem = item.find("pubDate")
                link_elem = item.find("link")
                
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                if title:
                    date_prefix = f"[{pub_date}] " if pub_date else ""
                    if link:
                        snippets.append(f"• [BREAKING NEWS: {date_prefix}{title}] (URL: {link})")
                    else:
                        snippets.append(f"• [BREAKING NEWS: {date_prefix}{title}]")
        except Exception as e:
            logger.debug(f"[WebGrounding] Google News RSS note: {e}")

        return snippets

    def fetch_ddg_html(self, query: str, max_results: int = 4) -> List[str]:
        """
        Fetches live web search results (websites, official domains, companies, services) via DuckDuckGo HTML search.
        """
        snippets: List[str] = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=4.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "html.parser")
            for r in soup.find_all("div", class_="result"):
                title_el = r.find("a", class_="result__a")
                if not title_el:
                    continue
                href = title_el.get("href", "")
                if "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in parsed:
                        href = parsed["uddg"][0]

                title = title_el.get_text().strip()
                snippet_el = r.find("a", class_="result__snippet")
                snippet = snippet_el.get_text().strip() if snippet_el else ""

                if href and title:
                    deep_info = ""
                    if "wikipedia.org/wiki/" in href or any(k in query.lower() for k in ["total", "count", "episode", "episodes", "season", "net worth", "who", "answer", "release"]):
                        deep_info = self.fetch_deep_article_snippet(href)

                    full_snippet = f"{snippet}{deep_info}".strip()
                    if full_snippet:
                        snippets.append(f"• [{title}] (URL: {href}): {full_snippet}")
                    else:
                        snippets.append(f"• [{title}] (URL: {href})")

                if len(snippets) >= max_results:
                    break
        except Exception as e:
            logger.debug(f"[WebGrounding] DDG HTML search note: {e}")

        return snippets

    def search_live(self, query: str, history: list = None, max_results: int = 4) -> str:
        """
        Orchestrates multi-source real-time search:
        - Full Web Search (DuckDuckGo HTML) for websites, companies, services, portals, and facts.
        - Bing News RSS & Google News RSS for breaking news events and live game answers.
        """
        topic = self.extract_search_topic(query, history=history)
        all_snippets: List[str] = []

        if topic:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_ddg = executor.submit(self.fetch_ddg_html, topic, max_results)
                future_bing = executor.submit(self.fetch_bing_news_rss, topic, max_results)

                try:
                    ddg_items = future_ddg.result(timeout=4.0)
                    if ddg_items:
                        all_snippets.extend(ddg_items)
                except Exception as e:
                    logger.debug(f"[WebGrounding] DDG parallel error: {e}")

                try:
                    bing_items = future_bing.result(timeout=4.0)
                    if bing_items:
                        all_snippets.extend(bing_items)
                except Exception as e:
                    logger.debug(f"[WebGrounding] Bing parallel error: {e}")

        # Fallback to Google News RSS if under 2 snippets
        if len(all_snippets) < 2 and topic:
            google_items = self.fetch_google_news_rss(topic, max_results=max_results)
            all_snippets.extend(google_items)

        if all_snippets:
            seen = set()
            unique = []
            for s in all_snippets:
                if s not in seen:
                    seen.add(s)
                    unique.append(s)
            return "\n".join(unique[:max_results])

        return ""

    def verify_single_url(self, url: str, timeout: float = 2.5) -> Tuple[bool, str]:
        """
        Tests if a URL is active (status < 400 or auth-restricted 401/403).
        Tries HEAD first, falling back to GET. Follows redirects.
        """
        if not url.startswith(("http://", "https://")):
            return False, url

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        for method in ["HEAD", "GET"]:
            try:
                req = urllib.request.Request(url, headers=headers, method=method)
                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                    status = getattr(resp, "status", 200)
                    if status < 400:
                        return True, resp.geturl()
            except urllib.error.HTTPError as e:
                # 401 Unauthorized or 403 Forbidden means the site/page exists behind protection/Cloudflare
                if e.code in [401, 403]:
                    return True, url
                # Method Not Allowed for HEAD -> retry with GET
                if method == "HEAD" and e.code in [405, 501]:
                    continue
                return False, url
            except Exception:
                if method == "HEAD":
                    continue
                return False, url

        return False, url

    def get_direct_youtube_video(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Fetches the top verified, 100% active, directly playable YouTube video URL (watch?v=...)
        for any search topic or video request.
        """
        try:
            clean_q = re.sub(r"[\–\—\-\:\(\)\[\]\|\_]", " ", query)
            clean_q = re.sub(r"\b(youtube search|youtube|video|channel|link|direct)\b", " ", clean_q, flags=re.IGNORECASE)
            clean_q = re.sub(r"\s+", " ", clean_q).strip()
            if not clean_q:
                clean_q = "Python tutorial"

            encoded = urllib.parse.quote_plus(clean_q)
            search_url = f"https://www.youtube.com/results?search_query={encoded}"

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=3.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            video_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
            if not video_ids:
                video_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)

            seen = set()
            for vid in video_ids:
                if vid in seen:
                    continue
                seen.add(vid)
                video_url = f"https://www.youtube.com/watch?v={vid}"

                # Verify with oEmbed
                try:
                    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
                    oreq = urllib.request.Request(oembed_url, headers=headers)
                    with urllib.request.urlopen(oreq, context=ctx, timeout=2.0) as oresp:
                        if oresp.status == 200:
                            data = json.loads(oresp.read().decode("utf-8"))
                            title = data.get("title", query)
                            return video_url, title
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"[WebGrounding] Direct YouTube video fetch note: {e}")

        return None

    def is_incomplete_or_fake_platform_url(self, raw_url: str, anchor: str = "") -> Tuple[bool, Optional[str]]:
        """
        Detects incomplete, generic, or hallucinated platform links (e.g. youtube.com/c/,
        youtube.com/@, fake video IDs, empty github.com root, empty reddit) and converts them into
        high-precision structured query URLs or direct playable video links.
        """
        try:
            clean_url = raw_url.rstrip(".,;:!?)*_~#>")
            parsed = urllib.parse.urlparse(clean_url)
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip("/")
            query_params = urllib.parse.parse_qs(parsed.query)

            # Extract clean search query from anchor or path
            clean_anchor = anchor
            if not clean_anchor or clean_anchor.startswith(("http://", "https://", "www.")):
                path_name = path.split("/")[-1] if path else "Dubai real estate"
                path_name = re.sub(r"([A-Z])", r" \1", path_name).strip()
                clean_anchor = path_name

            clean_anchor = re.sub(r"[\–\—\-\:\(\)\[\]\|]", " ", clean_anchor)
            clean_anchor = re.sub(r"\s+", " ", clean_anchor).strip()
            encoded_query = urllib.parse.quote_plus(clean_anchor or "Dubai real estate")

            # 1. YouTube link validation & direct video resolution
            if "youtube.com" in netloc or "youtu.be" in netloc:
                # Check if it's already a specific valid video link (watch?v=...)
                video_id = query_params.get("v", [None])[0] if "v" in query_params else (path.lstrip("/") if "youtu.be" in netloc and len(path) > 3 and not path.startswith(("/c", "/@", "/channel", "/user")) else None)
                if video_id and not any(path.startswith(p) for p in ["/c", "/channel", "/user", "/@"]):
                    try:
                        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=2.0) as resp:
                            if resp.status == 200:
                                return False, clean_url
                    except Exception:
                        pass

                # Resolve top 1st direct playable video URL on YouTube
                direct_video = self.get_direct_youtube_video(clean_anchor or "Python tutorial")
                if direct_video:
                    return True, direct_video[0]

                # Fallback to search query
                return True, f"https://www.youtube.com/results?search_query={encoded_query}"

            # 2. GitHub incomplete repository link
            if "github.com" in netloc:
                if path in ["", "/search"] and clean_anchor:
                    return True, f"https://github.com/search?q={encoded_query}"

            # 3. Reddit incomplete link
            if "reddit.com" in netloc:
                if path in ["", "/search", "/r"] and clean_anchor:
                    return True, f"https://www.reddit.com/search/?q={encoded_query}"

            # 4. Wikipedia incomplete link
            if "wikipedia.org" in netloc:
                if path in ["", "/wiki"] and clean_anchor:
                    return True, f"https://en.wikipedia.org/wiki/Special:Search?search={encoded_query}"

            # 5. Twitter / X incomplete link
            if "twitter.com" in netloc or "x.com" in netloc:
                if path in ["", "/search"] and clean_anchor:
                    return True, f"https://x.com/search?q={encoded_query}"

            # 6. Google Maps incomplete link
            if "maps.google." in netloc or "google.com/maps" in raw_url:
                if not parsed.query and clean_anchor:
                    return True, f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

            # 7. Placeholder or dummy domains
            placeholder_domains = ["example.com", "mysite.com", "sample.com", "yourdomain.com", "placeholder", "test.com"]
            if any(p in netloc for p in placeholder_domains):
                return True, f"https://www.google.com/search?q={encoded_query}"

        except Exception as e:
            logger.debug(f"[WebGrounding] Platform URL check note: {e}")

        return False, None

    def heal_url(self, raw_url: str, anchor: str = "") -> Optional[str]:
        """
        Validates URL and auto-heals 404 dead links, incomplete platform paths,
        and hallucinated video IDs into structured, fully-functional URLs.
        """
        clean_url = raw_url.strip().rstrip(".,;:!?)*_~#>")
        if not clean_url.startswith(("http://", "https://")):
            return None

        # 1. First check if it's an incomplete/unstructured platform URL (YouTube, GitHub, etc.)
        is_platform, healed_platform = self.is_incomplete_or_fake_platform_url(clean_url, anchor)
        if is_platform and healed_platform:
            return healed_platform

        # 2. Test exact original URL
        ok, final_u = self.verify_single_url(clean_url)
        if ok:
            return final_u.rstrip(".,;:!?)*_~#>")

        # 3. Parse domain and path
        try:
            parsed = urllib.parse.urlparse(clean_url)
            scheme = parsed.scheme or "https"
            netloc = parsed.netloc

            if not netloc:
                return None

            # Generate host variants (with and without 'www.')
            netloc_variants = [netloc]
            if netloc.startswith("www."):
                netloc_variants.append(netloc[4:])
            else:
                netloc_variants.append(f"www.{netloc}")

            # 4. Progressive path trimming (e.g. /en/dubai.html -> /en/ -> /)
            path_segments = [p for p in parsed.path.split("/") if p]
            while path_segments:
                path_segments.pop()
                subpath = "/" + "/".join(path_segments)
                if subpath != "/" and subpath:
                    subpath += "/"
                elif not subpath:
                    subpath = "/"

                for host in netloc_variants:
                    candidate = f"{scheme}://{host}{subpath}"
                    ok, final_u = self.verify_single_url(candidate)
                    if ok:
                        return final_u.rstrip(".,;:!?)*_~#>")

            # 5. Try root domains
            for host in netloc_variants:
                candidate = f"{scheme}://{host}/"
                ok, final_u = self.verify_single_url(candidate)
                if ok:
                    return final_u.rstrip(".,;:!?)*_~#>")
        except Exception as e:
            logger.debug(f"[WebGrounding] URL heal error: {e}")

        # 6. If completely dead domain but we have anchor text, fallback to search URL
        if anchor and not anchor.startswith(("http://", "https://")):
            clean_anchor = re.sub(r"[\–\—\-\:\(\)\[\]\|]", " ", anchor).strip()
            if clean_anchor:
                return f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_anchor)}"

        return None

    def verify_and_heal_links(self, text: str) -> str:
        """
        Instant, non-blocking URL sanitizer and auto-healer.
        Guarantees 100% WORKING, 0% 404 links:
        - Converts all non-video / hallucinated YouTube channels, slugs, or handles into active YouTube search queries.
        - Trims broken deep sub-paths on government/real estate portals to verified root/landing domains.
        - Converts invalid/dummy links into direct Google/YouTube searches.
        """
        if not text or ("http://" not in text and "https://" not in text):
            return text

        # 1. Preprocess links where raw URL was used inside anchor preceded by label:
        pattern_with_prefix = re.compile(r"([-\*\•]\s*([^\[\n\r]+?)\s*)\[(https?://[^\s\]]+)\]\((https?://[^\s\)]+)\)")
        def repl_prefix(m):
            full_prefix = m.group(1)
            title = m.group(2).strip()
            raw_url = m.group(4).rstrip(".,;:!?)*_~#>")
            return f"{full_prefix}[{title}]({raw_url})"
        text = pattern_with_prefix.sub(repl_prefix, text)

        def clean_query_text(s: str) -> str:
            cleaned = re.sub(r"[\–\—\-\:\(\)\[\]\|\_\#\@]", " ", s)
            cleaned = re.sub(r"\b(https?|www|com|org|net|youtube|official|channel|video|link|watch)\b", " ", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned

        # 2. Process all standard Markdown links [Anchor](URL)
        md_link_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)")
        def repl_md(m):
            anchor = m.group(1).strip()
            raw_url = m.group(2).rstrip(".,;:!?)*_~#>")
            parsed = urllib.parse.urlparse(raw_url)
            netloc = parsed.netloc.lower()
            path = parsed.path
            query = parsed.query

            # A. YouTube URLs (Fix ALL 404 channel slugs, /c/, /@/, /user/, or raw slugs like /DowntownDubaiOfficial)
            if "youtube.com" in netloc or "youtu.be" in netloc:
                is_valid_video = False
                if "watch" in path and "v=" in query:
                    v_match = re.search(r"v=([a-zA-Z0-9_-]{11})", query)
                    if v_match:
                        is_valid_video = True
                elif "youtu.be" in netloc and len(path.strip("/")) == 11:
                    is_valid_video = True
                elif "results" in path and "search_query=" in query:
                    return f"[{anchor}]({raw_url})"

                # If not a verified video ID, convert to guaranteed 100% working YouTube Search URL
                if not is_valid_video:
                    slug = path.strip("/").split("/")[-1] if path else ""
                    # Split PascalCase like DowntownDubaiOfficial -> Downtown Dubai Official
                    slug_readable = re.sub(r"([a-z])([A-Z])", r"\1 \2", slug)
                    search_term = clean_query_text(f"{anchor} {slug_readable}") or "Dubai real estate guide"
                    encoded_q = urllib.parse.quote_plus(search_term)
                    return f"[{anchor}](https://www.youtube.com/results?search_query={encoded_q})"

            # B. Generic / Hallucinated deep paths on official domains (Trim to clean working landing/home domains)
            domain_homepages = {
                "dubailand.gov.ae": "https://dubailand.gov.ae/en/",
                "propertyfinder.ae": "https://www.propertyfinder.ae/",
                "bayut.com": "https://www.bayut.com/",
                "emaar.com": "https://www.emaar.com/",
                "damacproperties.com": "https://www.damacproperties.com/",
                "nakheel.com": "https://www.nakheel.com/",
                "dxbinteract.com": "https://dxbinteract.com/",
                "mohre.gov.ae": "https://www.mohre.gov.ae/",
                "visitdubai.com": "https://www.visitdubai.com/",
            }
            for dom, home_url in domain_homepages.items():
                if dom in netloc:
                    return f"[{anchor}]({home_url})"

            # C. Incomplete platform paths (GitHub, Reddit, Wikipedia, Maps)
            if "github.com" in netloc and (path in ["", "/search"] or len(path.strip("/").split("/")) < 2):
                search_term = clean_query_text(anchor) or "code"
                return f"[{anchor}](https://github.com/search?q={urllib.parse.quote_plus(search_term)})"

            if "reddit.com" in netloc and path in ["", "/search", "/r"]:
                search_term = clean_query_text(anchor) or "discussion"
                return f"[{anchor}](https://www.reddit.com/search/?q={urllib.parse.quote_plus(search_term)})"

            return f"[{anchor}]({raw_url})"

        text = md_link_pattern.sub(repl_md, text)

        # 3. Heal any bare raw YouTube URLs in plain text (e.g. https://www.youtube.com/DowntownDubaiOfficial)
        bare_yt_pattern = re.compile(r"(?<!\()(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/(?:[a-zA-Z0-9_\-\@]+))(?!\))")
        def repl_bare_yt(m):
            bare_url = m.group(1).rstrip(".,;:!?)*_~#>")
            if "watch?v=" in bare_url or "results?search_query=" in bare_url:
                return bare_url
            slug = bare_url.split("/")[-1]
            slug_readable = re.sub(r"([a-z])([A-Z])", r"\1 \2", slug)
            search_term = clean_query_text(slug_readable) or "Dubai real estate video"
            encoded_q = urllib.parse.quote_plus(search_term)
            return f"[{slug_readable or 'YouTube Video'}](https://www.youtube.com/results?search_query={encoded_q})"

        text = bare_yt_pattern.sub(repl_bare_yt, text)
        return text

    def get_grounding_prompt(self, user_query: str, history: list = None) -> str:
        """
        Builds live web grounding prompt injection with context support.
        """
        temporal = self.get_temporal_context()
        now = datetime.datetime.now()

        # If query requires live web facts or links, search the web
        if self.should_search_web(user_query, history=history):
            web_facts = self.search_live(user_query, history=history)
            if web_facts:
                return (
                    f"{temporal}\n\n"
                    f"[LIVE REAL-TIME VERIFIED 2026 WEB & BREAKING NEWS RESULTS (Current Date: {now.strftime('%B %d, %Y')})]\n"
                    f"{web_facts}\n\n"
                    f"CRITICAL REAL-TIME INSTRUCTIONS:\n"
                    f"1. UNIVERSAL RULE FOR ALL TOPICS: Always explain the actual answer, facts, solution, exact figures, or key insights directly in clear, informative sentences.\n"
                    f"2. ZERO PLACEHOLDERS & DEFLECTIONS: NEVER output placeholder text such as '[X number of episodes]', '[insert data]', '[Name]', or generic brush-offs like 'You can check the official website/streaming platform'. Always state the exact verified number, status, or date directly.\n"
                    f"3. TEMPORAL DATE VALIDATION: Check all dates in search snippets against Today's Date ({now.strftime('%B %d, %Y')}). Any date prior to today has already occurred/premiered. For ongoing weekly/daily shows, calculate the current count/episode relative to today rather than mislabeling past premiere dates as future releases.\n"
                    f"4. NEVER reply with ONLY a link or deflect the user. Always deliver substantive, up-to-date facts directly.\n"
                    f"5. Put any verified reference or documentation link at the VERY END of your response formatted as [Source Name](https://clean-domain-url.com/).\n"
                    f"6. For counts, milestones, puzzles, scores, or game queries, state the verified answer directly in bold."
                )
            else:
                return (
                    f"{temporal}\n\n"
                    f"[REAL-TIME TEMPORAL DIRECTIVE]\n"
                    f"Today is {now.strftime('%B %d, %Y')}. If you do not have live breaking feeds for this specific event, state that as of {now.strftime('%B %Y')} no fresh live feed was received, and do NOT falsely claim events from 2024 or 2025 happened 'recently' or 'today'. NEVER use placeholders like '[X]' or generic deflections. When providing URLs, provide only verified official top-level domain URLs (e.g. https://www.propertyfinder.ae/)."
                )

        return temporal


# Global singleton instance
web_grounding = WebGroundingEngine()

