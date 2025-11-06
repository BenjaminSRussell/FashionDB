from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import Optional


def normalize_url(
    url: str, strip_query_parameters: bool = True, strip_fragment_identifier: bool = True
) -> str:
    # Normalize URLs to a canonical https form.
    if not url:
        return ""

    parsed_url = urlparse(url.strip())

    scheme = "https"

    netloc = parsed_url.netloc.lower()

    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed_url.path.lower()
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    if strip_query_parameters:
        query = ""
    else:
        if parsed_url.query:
            params = parse_qs(parsed_url.query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query = urlencode(sorted_params, doseq=True)
        else:
            query = ""

    fragment = "" if strip_fragment_identifier else parsed_url.fragment

    normalized_url = urlunparse((scheme, netloc, path, "", query, fragment))

    return normalized_url


def are_urls_duplicates(url1: str, url2: str) -> bool:
    # Compare two URLs after normalization.
    return normalize_url(url1) == normalize_url(url2)


def extract_domain_from_url(url: str) -> Optional[str]:
    # Return the bare domain (without port) for a URL.
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        if ":" in domain:
            domain = domain.split(":")[0]

        if domain.startswith("www."):
            domain = domain[4:]

        return domain if domain else None
    except Exception:
        return None


def is_url_an_article(url: str, custom_exclude_patterns: list = None) -> bool:
    # Heuristic filter that flags obvious non-article URLs.
    if not url:
        return False

    default_exclusion_patterns = [
        "/tag/",
        "/tags/",
        "/category/",
        "/categories/",
        "/author/",
        "/search",
        "/page/",
        "/archives/",
        "/feed/",
        "/rss/",
        "/sitemap",
        "/product/",
        "/shop/",
        "/cart/",
        "/checkout/",
        "/account/",
        "/login/",
        "/register/",
        "/contact/",
        "/about/",
    ]

    custom_exclude_patterns = custom_exclude_patterns or []
    all_exclusion_patterns = default_exclusion_patterns + custom_exclude_patterns

    url_lower = url.lower()
    for pattern in all_exclusion_patterns:
        if pattern in url_lower:
            return False

    return True


if __name__ == "__main__":
    test_urls = [
        "http://example.com/article/",
        "https://example.com/article",
        "https://www.example.com/article/?utm_source=google",
        "https://example.com:443/article#section",
        "HTTPS://EXAMPLE.COM/Article/",
    ]

    print("URL Normalization Tests")
    print("=" * 80)

    for url in test_urls:
        normalized = normalize_url(url)
        print(f"Original:   {url}")
        print(f"Normalized: {normalized}")
        print()

    print("\nDuplicate Detection Tests")
    print("=" * 80)

    url_pairs = [
        ("http://example.com/page/", "https://example.com/page"),
        ("https://example.com/page?foo=bar", "https://example.com/page"),
        ("https://example.com/page", "https://example.com/other"),
    ]

    for url1, url2 in url_pairs:
        is_duplicate = are_urls_duplicates(url1, url2)
        print(f"{url1}")
        print(f"{url2}")
        print(f"Duplicate: {is_duplicate}\n")
