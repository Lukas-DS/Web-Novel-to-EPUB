from bs4 import BeautifulSoup
import re
import requests
from parser import Parser


class ReaderNovelParser(Parser):
    name = "readernovel"
    base_url = "https://readernovel.net"

    max_clients = 10

    def grab(self, url, raw=False):
        req = requests.get(url)
        return req if raw else req.text

    def _link_to_num(self, link):
        match = re.findall(r"(\d+)", link)[2]
        return int(match)

    def parse_homepage(self, url):
        html = self.grab(url)
        soup = BeautifulSoup(html, "lxml")

        title = soup.find("h1", {"class": "page-title"}).text
        desc = soup.find("div", {"id": "collapseSummary"}).text.strip()
        language = soup.find("html")["lang"]

        author = (
            soup.find("ul", {"class": "list-group-flush"}).find("a").get_text().strip()
        )

        chapter_links_raw = soup.find(
            "div", {"class": "chapter-list-wrapper"}
        ).find_all(
            "a"
        )  # still contains tag info (not a string yet)

        chapter_links_clean = {}

        image = (
            self.base_url
            + soup.find("div", {"class": "manga-image"}).find("img")["data-src"]
        )

        # calculation for last chapter # and grabbing the numbers from each url
        last = 0
        for ch in chapter_links_raw:
            ch_num = self._link_to_num(ch["href"])
            if last < ch_num:
                last = ch_num
            chapter_links_clean[ch_num] = f"{self.base_url}{ch["href"]}"

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

        ch_title = soup.find("span", {"class": "chapter-title"}).get_text(strip=True)

        body = soup.find("div", {"id": "chapter-container"}).get_text()

        # Removing blacklisted text
        cleaned_body = blacklist.sub("", body)
        cleaned_body = cleaned_body.strip()

        lines = [l.strip() for l in cleaned_body.splitlines() if l.strip()]

        return ch_title, lines
