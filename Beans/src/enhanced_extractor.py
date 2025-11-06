from typing import Any, Dict, List, Optional
from datetime import datetime
import re

from bs4 import BeautifulSoup
import trafilatura
from newspaper import Article as NewspaperArticle
from selectolax.parser import HTMLParser

from url_utils import normalize_url


class EnhancedContentExtractor:
    # Combines multiple extractors to produce reliable article metadata and text.

    def __init__(self):
        # Keyword list for quick relevance scoring.
        self.fashion_keywords = [
            "wear",
            "fit",
            "color",
            "match",
            "pair",
            "dress",
            "style",
            "fashion",
            "shirt",
            "pants",
            "jacket",
            "suit",
            "shoes",
            "tie",
            "belt",
            "formal",
            "casual",
            "business",
            "wardrobe",
            "outfit",
            "tailoring",
        ]

    def extract_article(self, html_content: str, article_url: str) -> Dict:
        # Merge multiple extractor outputs with simple fallbacks.

        trafilatura_result = self._extract_data_with_trafilatura(
            html_content, article_url
        )
        newspaper_result = self._extract_data_with_newspaper(
            html_content, article_url
        )
        selectolax_result = self._extract_data_with_selectolax(
            html_content, article_url
        )

        text_content = (
            trafilatura_result.get("text")
            or selectolax_result.get("text")
            or newspaper_result.get("text")
            or ""
        )
        paragraphs = (
            trafilatura_result.get("paragraphs")
            or selectolax_result.get("paragraphs", [])
        )
        headings = selectolax_result.get("headings", [])
        lists = selectolax_result.get("lists", [])
        sections = selectolax_result.get("sections", [])

        title = (
            newspaper_result.get("title")
            or trafilatura_result.get("title")
            or selectolax_result.get("title")
        )
        author = (
            newspaper_result.get("author") or trafilatura_result.get("author")
        )
        publish_date = newspaper_result.get("publish_date") or trafilatura_result.get(
            "publish_date"
        )

        combined_data = {
            "url": normalize_url(article_url),
            "raw_url": article_url,
            "title": title,
            "author": author,
            "publish_date": publish_date,
            "top_image": newspaper_result.get("top_image"),
            "images": newspaper_result.get("images", []),
            "text": text_content,
            "word_count": len(text_content.split()),
            "paragraphs": paragraphs,
            "headings": headings,
            "lists": lists,
            "sections": sections,
            "content_type": self._classify_content_by_type(
                newspaper_result.get("title", ""), text_content
            ),
            "language": trafilatura_result.get("language"),
            "tags": newspaper_result.get("keywords", []),
            "has_lists": len(lists) > 0,
            "has_sections": len(sections) > 0,
            "fashion_relevance": self._calculate_fashion_content_relevance(
                text_content
            ),
            "extracted_at": datetime.utcnow().isoformat(),
        }

        return combined_data

    def _extract_data_with_trafilatura(self, html_content: str, url: str) -> Dict:
        # Use trafilatura to pull cleaned text and paragraphs.
        try:
            metadata = trafilatura.extract_metadata(html_content)

            text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                include_links=False,
            )

            xml_content = trafilatura.extract(
                html_content,
                output_format="xml",
                include_comments=False,
                include_tables=True,
            )

            paragraphs = []
            if xml_content:
                xml_soup = BeautifulSoup(xml_content, "xml")
                for p in xml_soup.find_all("p"):
                    para_text = p.get_text(strip=True)
                    if para_text and len(para_text) > 20:
                        paragraphs.append(para_text)

            return {
                "title": metadata.title if metadata else None,
                "author": metadata.author if metadata else None,
                "publish_date": self._normalize_date_to_iso_format(
                    metadata.date if metadata else None
                ),
                "language": metadata.language if metadata else None,
                "text": text or "",
                "paragraphs": paragraphs,
            }
        except Exception as error:
            print(f"WARNING:  Trafilatura extraction failed: {error}")
            return {}

    def _extract_data_with_newspaper(self, html_content: str, url: str) -> Dict:
        # Let newspaper3k gather metadata and body text.
        try:
            article = NewspaperArticle(url)
            article.set_html(html_content)
            article.parse()

            try:
                article.nlp()
            except Exception:
                pass

            return {
                "title": article.title,
                "author": ", ".join(article.authors) if article.authors else None,
                "publish_date": self._normalize_date_to_iso_format(
                    article.publish_date
                ),
                "text": article.text or "",
                "top_image": article.top_image,
                "images": list(article.images) if article.images else [],
                "keywords": article.keywords if hasattr(article, "keywords") else [],
            }
        except Exception as error:
            print(f"WARNING:  Newspaper3k extraction failed: {error}")
            return {}

    def _extract_data_with_selectolax(self, html_content: str, url: str) -> Dict:
        # Use selectolax to capture structure such as headings and lists.
        try:
            tree = HTMLParser(html_content)
            if not tree.body:
                return {}

            def clean_text_from_node(node) -> str:
                if node is None:
                    return ""
                raw_text = node.text(separator=" ") if hasattr(node, "text") else ""
                return " ".join(raw_text.split())

            container = (
                tree.css_first("main") or tree.css_first("article") or tree.body
            )

            title_node = (
                tree.css_first("head > title") or container.css_first("h1")
            )
            title = clean_text_from_node(title_node) or None

            paragraphs: List[str] = []
            for node in container.css("p"):
                paragraph = clean_text_from_node(node)
                if paragraph and len(paragraph) > 20:
                    paragraphs.append(paragraph)

            headings = []
            for heading in container.css("h1, h2, h3, h4, h5, h6"):
                if not heading.tag:
                    continue
                heading_text = clean_text_from_node(heading)
                if heading_text and len(heading_text) > 2:
                    headings.append(
                        {"level": int(heading.tag[-1]), "text": heading_text}
                    )

            lists = []
            for list_elem in container.css("ul, ol"):
                if not list_elem.tag:
                    continue
                items = []
                for li in list_elem.css("li"):
                    if li.parent != list_elem:
                        continue
                    item_text = clean_text_from_node(li)
                    if item_text and len(item_text) > 5:
                        items.append(item_text)

                if items:
                    lists.append(
                        {
                            "type": "ordered"
                            if list_elem.tag == "ol"
                            else "unordered",
                            "items": items,
                        }
                    )

            sections = []
            for heading in container.css("h2, h3"):
                if not heading.tag:
                    continue
                heading_text = clean_text_from_node(heading)
                if not heading_text:
                    continue

                content = []
                sibling = heading.next
                while sibling:
                    if sibling.tag in {"h2", "h3"}:
                        break
                    if sibling.tag == "p":
                        para_text = clean_text_from_node(sibling)
                        if para_text:
                            content.append(para_text)
                    sibling = sibling.next

                if content:
                    sections.append(
                        {
                            "heading": heading_text,
                            "level": int(heading.tag[-1]),
                            "paragraphs": content,
                        }
                    )

            return {
                "title": title,
                "text": " ".join(paragraphs)
                if paragraphs
                else clean_text_from_node(container),
                "headings": headings,
                "lists": lists,
                "sections": sections,
                "paragraphs": paragraphs,
            }
        except Exception as error:
            print(f"WARNING:  Selectolax fallback extraction failed: {error}")
            return {}

    def _classify_content_by_type(self, title: str, text: str) -> str:
        # Use keyword heuristics to label the article type.
        combined_text = (title + " " + text).lower()

        if any(
            keyword in combined_text
            for keyword in ["outfit formula", "how to wear", "what to wear with"]
        ):
            return "outfit_formula"

        if any(
            keyword in combined_text
            for keyword in ["style guide", "how to", "ultimate guide", "complete guide"]
        ):
            return "style_guide"

        if any(
            keyword in combined_text
            for keyword in [
                "fabric",
                "material",
                "wool",
                "cotton",
                "linen",
                "season",
            ]
        ):
            return "fabric_season_guide"

        if any(
            keyword in combined_text
            for keyword in [
                "dress code",
                "black tie",
                "white tie",
                "business casual",
                "smart casual",
            ]
        ):
            return "dress_code_breakdown"

        if any(
            keyword in combined_text
            for keyword in ["rule", "principle", "essential", "fundamental"]
        ):
            return "rules_to_live_by"

        if any(
            keyword in combined_text
            for keyword in ["mistake", "avoid", "never", "don't", "worst"]
        ):
            return "mistakes_to_avoid"

        if any(
            keyword in combined_text
            for keyword in ["trend", "2024", "2025", "current", "latest"]
        ):
            return "trend_analysis"

        return "general"

    def _calculate_fashion_content_relevance(self, text: str) -> float:
        # Estimate how fashion-focused the article is using keyword density.
        if not text:
            return 0.0

        text_lower = text.lower()
        words = text_lower.split()

        if len(words) < 100:
            return 0.0

        fashion_keyword_count = sum(
            1 for word in words if word in self.fashion_keywords
        )

        relevance_score = min(1.0, fashion_keyword_count / (len(words) / 100))

        return round(relevance_score, 3)

    def _normalize_date_to_iso_format(
        self, date_value: Optional[Any]
    ) -> Optional[str]:
        # Normalize extracted dates to ISO strings.
        if isinstance(date_value, datetime):
            return date_value.isoformat()
        if isinstance(date_value, str):
            cleaned_date = date_value.strip()
            return cleaned_date or None
        return None


# Rule extraction lives in src/rules_extractor.py.


if __name__ == "__main__":
    import requests

    test_url = "https://putthison.com/how-to-do-business-casual-without-looking-like-a/"

    print(f"Testing enhanced extractor on: {test_url}\n")

    try:
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()
        html = response.text

        extractor = EnhancedContentExtractor()
        article = extractor.extract_article(html, test_url)

        print("=" * 80)
        print("EXTRACTED ARTICLE DATA")
        print("=" * 80)
        print(f"Title: {article.get('title')}")
        print(f"Author: {article.get('author')}")
        print(f"Date: {article.get('publish_date')}")
        print(f"Content Type: {article.get('content_type')}")
        print(f"Word Count: {article.get('word_count')}")
        print(f"Fashion Relevance: {article.get('fashion_relevance')}")
        print(f"Paragraphs: {len(article.get('paragraphs', []))}")
        print(f"Headings: {len(article.get('headings', []))}")
        print(f"Lists: {len(article.get('lists', []))}")
        print(f"Sections: {len(article.get('sections', []))}")

        # Rule extraction has been moved to rules_extractor.py
        print("\nNote: Rule extraction now handled by src/rules_extractor.py")
        print("Use RulesExtractor class for extracting fashion rules from articles")

    except Exception as error:
        print(f"ERROR: Test failed: {error}")
