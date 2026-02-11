from bs4 import BeautifulSoup
import re
import requests
from parser import Parser


class LightNovelWorldParser(Parser):
    name = "lightnovelworld"
    base_url = "https://lightnovelworld.org"

    max_clients = 2

    def grab(self, url, raw=False):
        # lightnovelworld requires an agent request
        AGENT = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/105.0.0.0 Safari/537.36"
        )
        req = requests.get(url, headers={"User-Agent": AGENT})
        return req if raw else req.text

    def _scrape_chapter_list(self, html, last):
        """lightnovelworld has an inconvenient page-based chapters page"""
        soup = BeautifulSoup(html, "lxml")

        chapter_links = {}

        cards = soup.find_all("div", {"class": "chapter-card"})
        for card in cards:
            ch_num = int(card.find("div", {"class": "chapter-number"}).text)
            if ch_num > last:
                last = ch_num
            ch_link = f"{self.base_url}{card["onclick"][15:-1]}"
            chapter_links[ch_num] = ch_link

        return chapter_links, last

    def parse_homepage(self, url):
        html = self.grab(url)
        soup = BeautifulSoup(html, "lxml")

        title = soup.find("h1", {"class": "novel-title"}).text
        author = soup.find("p", {"class": "novel-author"}).text
        desc = soup.find("div", {"class": "summary-content"}).text
        language = soup.find("html")["lang"]
        image = self.base_url + soup.find("img", {"class": "novel-cover"})["src"]

        url_chapters = f"{url}chapters/?page="

        # need to get the other chapter page ids
        chapter1_html = self.grab(f"{url_chapters}1")

        soupch = BeautifulSoup(chapter1_html, "lxml")

        # gets the id for each page of chapters without crashing
        pages_num = [
            x["value"]
            for x in soupch.find("select", {"id": "pageSelectBottom"}).find_all(
                "option"
            )
        ]
        pages_links = [f"{url_chapters}{x}" for x in pages_num]

        chapter_links = {}
        last = 0
        for page in pages_links:
            print(f"getting page {page}")
            new_chl, last = self._scrape_chapter_list(self.grab(page), last)
            chapter_links = chapter_links | new_chl

        return {
            "title": title,
            "author": author,
            "description": desc,
            "language": language,
            "last": last,
            "links": chapter_links,
            "image": image,
        }

    def parse_chapter(self, html, blacklist):
        soup = BeautifulSoup(html, "lxml")

        ch_title = soup.find("h1", {"class": "chapter-title"}).get_text(strip=True)

        body = soup.find("div", {"id": "chapterText"})
        body_str = "\n".join([x.get_text() for x in body])

        # Removing blacklisted text
        cleaned_body = blacklist.sub("", body_str)
        cleaned_body = cleaned_body.strip()

        lines = [l.strip() for l in cleaned_body.splitlines() if l.strip()]

        body_html = f"<h1>{ch_title}</h1>\n" "<p>" + "</p><p>".join(lines) + "</p>"

        return ch_title, body_html
