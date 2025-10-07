#!/usr/bin/env python3
"""
Universal Documentation Link Extractor
Extracts all documentation links from any website
Supports both static and JavaScript-rendered sites
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import time
from datetime import datetime
from pathlib import Path

# Playwright imports - optional, will fallback to requests if not available
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Note: Playwright not available. Install with 'pip install playwright' for JS-rendered sites.")

def fetch_page_content(url, use_playwright=False):
    """Fetch page content using either requests or Playwright"""

    if use_playwright and PLAYWRIGHT_AVAILABLE:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Use 'load' instead of 'networkidle' for faster loading
                page.goto(url, wait_until='load', timeout=60000)
                # Wait for dynamic content to load
                page.wait_for_timeout(3000)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            print(f"  Playwright error: {e}, falling back to requests")
            use_playwright = False

    if not use_playwright:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.text

def extract_all_links(base_url, max_pages=50, use_playwright=False):
    """Extract all documentation-related links from a website"""

    visited = set()
    to_visit = [base_url]
    all_links = set()

    base_domain = urlparse(base_url).netloc

    print(f"Extracting links from: {base_url}")
    print(f"Domain: {base_domain}")
    print(f"Mode: {'Playwright (JS-rendered)' if use_playwright else 'Requests (static HTML)'}")
    print("-" * 50)

    page_count = 0

    while to_visit and page_count < max_pages:
        current_url = to_visit.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)
        page_count += 1

        try:
            print(f"[{page_count}] Scanning: {current_url}")

            # Fetch page content
            html_content = fetch_page_content(current_url, use_playwright)
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all links on this page
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Convert relative URLs to absolute
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(current_url, href)

                # Only keep links from the same domain
                if urlparse(href).netloc == base_domain:
                    # Clean up the URL (remove fragments, query params for cleaner list)
                    clean_url = href.split('#')[0].split('?')[0]
                    all_links.add(clean_url)

                    # Add to visit queue if it looks like documentation
                    if (clean_url not in visited and
                        clean_url not in to_visit and
                        any(keyword in clean_url.lower() for keyword in ['doc', 'api', 'guide', 'tutorial'])):
                        to_visit.append(clean_url)

            time.sleep(0.5 if not use_playwright else 1.0)  # Be more respectful with Playwright

        except Exception as e:
            print(f"Error scanning {current_url}: {e}")
            continue

    return sorted(all_links)

def save_links(links, base_url, log_dir):
    """Save links to file and create fetch commands in timestamped log directory"""

    domain = urlparse(base_url).netloc.replace('.', '_')

    # Save all links
    output_file = log_dir / "extracted_links.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# All documentation links from {base_url}\n")
        f.write(f"# Total links found: {len(links)}\n\n")

        for link in links:
            f.write(link + '\n')

    # Create fetch command for all links
    fetch_file = log_dir / "fetch_commands.txt"
    with open(fetch_file, 'w', encoding='utf-8') as f:
        # Split into chunks of 10 URLs to avoid command line length limits
        chunk_size = 10
        chunks = [links[i:i + chunk_size] for i in range(0, len(links), chunk_size)]

        f.write(f"# Fetch commands for {base_url}\n")
        f.write(f"# Total commands: {len(chunks)}\n\n")

        for i, chunk in enumerate(chunks, 1):
            cmd = f"python api_docs_fetcher.py {' '.join(chunk)} --output {domain}_docs/batch_{i:02d} --depth 3 --delay 1.0"
            f.write(f"# Batch {i}\n")
            f.write(cmd + '\n\n')

    print(f"\nSaved {len(links)} links to: {output_file}")
    print(f"Saved fetch commands to: {fetch_file}")

    return fetch_file

def main():
    parser = argparse.ArgumentParser(description='Extract all documentation links from a website')
    parser.add_argument('url', help='Base URL to start extraction from')
    parser.add_argument('--max-pages', type=int, default=50, help='Maximum pages to scan (default: 50)')
    parser.add_argument('--use-playwright', action='store_true',
                       help='Use Playwright for JavaScript-rendered sites (slower but more complete)')

    args = parser.parse_args()

    # Check if Playwright is requested but not available
    if args.use_playwright and not PLAYWRIGHT_AVAILABLE:
        print("Error: Playwright requested but not installed.")
        print("Install with: pip install playwright && playwright install chromium")
        return

    # Create timestamped log directory
    domain = urlparse(args.url).netloc.replace('.', '_').split('_')[0]  # Get main domain part
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_dir = Path("logs") / f"{domain}_{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Extract all links
    links = extract_all_links(args.url, args.max_pages, use_playwright=args.use_playwright)

    # Save results
    save_links(links, args.url, log_dir)

    print(f"\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Pages scanned: {min(args.max_pages, len(links))}")
    print(f"Total unique links found: {len(links)}")
    print(f"Log directory: {log_dir}")
    print(f"  - extracted_links.txt")
    print(f"  - fetch_commands.txt")
    print("\nNext step: Run fetch_all_extracted_links.py to download all documentation!")

if __name__ == "__main__":
    main()