from bs4 import BeautifulSoup
import re
import requests
from parser import Parser


class WattpadParser(Parser):
    name = "wattpad"
    base_url = "https://www.wattpad.com/"

    max_clients = 2

    def grab(self, url, raw=False):
        # Wattpad requires an agent request
        AGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/105.0.0.0 Safari/537.36"
        )
        req = requests.get(url, headers={"User-Agent": AGENT})
        return req if raw else req.text

    def _link_to_name(self, link):
        first = -1
        for i in range(len(link)):
            if link[i].isdigit() and first == -1:
                first = i
                continue
            if not link[i].isdigit() and first != -1:
                return link[i + 1 :].replace("-", " ").title()
        return link.replace("-", " ")

    def parse_homepage(self, url):
        html = self.grab(url)
        soup = BeautifulSoup(html, "lxml")

        title = self._link_to_name(url)
        desc = "WIP"  # wattpad has a very inconvenient website layout to parse
        language = soup.find("html")["lang"]

        author = soup.find("div", {"data-testid": "story-badges"}).findChild().text

        chapter_links_clean = {}

        chapter_links_s = soup.find("ul", {"aria-label": "story-parts"})
        last = 1
        for li in chapter_links_s:
            chapter_links_clean[last] = li.find("a")["href"]
            last += 1
        last -= 1

        image = soup.find("img", {"data-testid": "image"})["src"]

        return {
            "title": title,
            "author": author,
            "description": desc,
            "language": language,
            "image": image,
            "last": last,
            "links": chapter_links_clean,
        }

    def parse_chapter(self, html, blacklist):
        soup = BeautifulSoup(html, "lxml")

        ch_title = soup.find("h1", {"class": "h2"}).get_text(strip=True)

        body = soup.find("div", {"class": "first-page"}).find("pre")
        bstr = ""
        for b in body:
            bstr += b.get_text().strip() + "\n"

        # Removing blacklisted text
        bstr = blacklist.sub("", bstr)
        cleaned_body = bstr.strip()

        lines = [l.strip() for l in cleaned_body.splitlines() if l.strip()]

        return ch_title, lines
