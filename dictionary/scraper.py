import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor


class AkanDict:
    """Scrapper for the Akan Dictionary website."""

    BASE_URL = "https://www.akandictionary.com"
    MAX_WORKERS = 10

    def __init__(self, headers):
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.failed_urls = []

    def get_html(self, url):
        response = self.session.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            self.failed_urls.append(url)
            raise ValueError(
                f"Failed to retrieve page. Status code: {response.status_code}"
            )

    def get_words_url(self):
        alphabet_urls = [
            f"https://www.akandictionary.com/{letter}/"
            for letter in "abcdefghijklmnopqrstuvwxyz"
        ]

        all_links = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(self._scrape_alphabet_page, alphabet_urls)
            for links in results:
                all_links.extend(links)

        print(f"Found {len(all_links)} total words")
        return all_links

    def _scrape_alphabet_page(self, url):
        try:
            html = self.get_html(url)
            if not html:
                return []

            page = BeautifulSoup(html, "html.parser")
            word_lists = page.find_all("ul", class_="wp-block-list")

            # if len(word_lists) < 2:
            #     return []
            if len(word_lists) < 2:
                word_list = word_lists[0]
            else:
                word_list = word_lists[1]
            links = word_list.find_all("a")
            return links
        except Exception as e:
            ValueError(f"Error scraping {url}: {e}")
            return []

    def _parse_word_page(self, link):
        word_url = link.get("href")

        try:
            html = self.get_html(word_url)
            if not html:
                return None

            page = BeautifulSoup(html, "html.parser")

            word_data = {"english_word": "", "twi_word": "", "part_of_speech": ""}

            twi_word = page.find("h1", class_="wp-block-post-title")
            if twi_word:
                word_data["twi_word"] = twi_word.text.strip()

            entry_content = page.find("div", class_="entry-content")
            if entry_content:
                paragraphs = entry_content.find_all("p")

                for p in paragraphs:
                    text = p.text.strip()
                    if text.startswith("Part of speech:"):
                        word_data["part_of_speech"] = text.replace(
                            "Part of speech:", ""
                        ).strip()
                    elif "english" in text.lower():
                        english_word = text.split(":", maxsplit=1)
                        word_data["english_word"] = english_word[1].strip()

            return word_data

        except Exception as e:
            ValueError(f"Error scraping {word_url}: {e}")
            return None

    def make_dictionary(self):
        word_links = self.get_words_url()
        print(f"Scraping {len(word_links)} word pages...")

        dictionary = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(self._parse_word_page, word_links)

            for i, word_data in enumerate(results, 1):
                if word_data:
                    dictionary.append(word_data)

                if i % 50 == 0:
                    print(f"Progress: {i}/{len(word_links)} words scraped")

        df = pd.DataFrame(
            dictionary, columns=["english_word", "twi_word", "part_of_speech"]
        )
        df = df.sort_values("english_word").reset_index(drop=True)
        df.to_csv("./eng_akan_dict.csv", index=False)

        print(f"Dictionary saved! Total entries: {len(df)}")

        if self.failed_urls:
            print(" Failed to scrape:")
            for url in self.failed_urls:
                print(f"  - {url}")


if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    scraper = AkanDict(headers)
    scraper.make_dictionary()
