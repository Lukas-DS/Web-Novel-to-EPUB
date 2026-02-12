from abc import ABC, abstractmethod


# Base parser, all the parsers are based off of this
class Parser(ABC):
    # All parsers must have these two variables
    # String base_url
    # String name
    base_url = None
    name = None  # name must be contained in the url

    # max scraping clients for rate limits
    # Integer max_clients
    max_clients = None

    @abstractmethod
    def grab(self, url, raw=False):
        """
        Takes url
        Returns plain html (usually request.text)
        """
        pass

    @abstractmethod
    def parse_homepage(self, url):
        """
        Takes in url of homepage
        Return dict:
        {
            title, #string
            author, #string
            description, #string
            language, #string
            image, #string (url)
            last, #integer
            links, #dictionary {int key: string (url)}
        }
        see: example parser in /parsers for details
        """
        pass

    @abstractmethod
    def parse_chapter(self, html, blacklist):
        """
        Takes in raw chapter HTML, and Re.Pattern object
        Return tuple: (chapter_title, body_list)
        body_list contains each line or portion of text that should be contained within a <p> tag as each row
        """
        pass
