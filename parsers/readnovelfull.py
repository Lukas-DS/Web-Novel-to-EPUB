from bs4 import BeautifulSoup
import re
import requests
from parser import Parser


class ReadNovelFullParser(Parser):
    name = "readnovelfull"
    base_url = "https://readnovelfull.com"

    max_clients = 10

    def grab(self, url, raw=False):
        req = requests.get(url)
        return req if raw else req.text

    def _link_to_num(self, link):
        if "/prologue.html" in link:
            return 0
        match = re.findall(r"(\d+)", link)[0]
        return int(match)

    def parse_homepage(self, url):
        html = self.grab(url)
        soup = BeautifulSoup(html, "lxml")

        title = soup.find("h3", {"class": "title"}).text
        desc = soup.find("div", {"class": "desc-text"}).text  # .strip()
        language = soup.find("html")["lang"]

        author = soup.find("meta", {"itemprop": "name"})["content"]
        novelId = soup.find("div", {"id": "rating"})["data-novel-id"]

        # readnovelfull has an alternate frontend where chapters links are
        ajax_url = f"{self.base_url}/ajax/chapter-archive?novelId={novelId}"
        ajax_html = self.grab(ajax_url)
        soup_ajax = BeautifulSoup(ajax_html, "lxml")

        anchor_tags = soup_ajax.find_all("a")
        chapter_links_raw = [anchor["href"] for anchor in anchor_tags]
        chapter_links_clean = {}

        last = 0
        for ch in chapter_links_raw:
            ch_num = self._link_to_num(ch)
            if last < ch_num:
                last = ch_num
            chapter_links_clean[ch_num] = f"{self.base_url}{ch}"

        image = soup.find("meta", {"name": "image"})["content"]

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

        ch_title = soup.find("span", {"class": "chr-text"}).get_text(strip=True)

        body = soup.find("div", {"id": "chr-content"}).find_all("p")
        body_str = "\n".join([x.get_text() for x in body])

        # Removing blacklisted text
        cleaned_body = blacklist.sub("", body_str)
        cleaned_body = cleaned_body.strip()

        lines = [l.strip() for l in cleaned_body.splitlines() if l.strip()]

        return ch_title, lines
