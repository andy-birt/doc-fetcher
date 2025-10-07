#!/usr/bin/env python3
"""
Fetch Documentation from All Extracted Links
Processes each link from extracted_links.txt individually
"""

import subprocess
import time
import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import os

def read_extracted_links(file_path="extracted_links.txt"):
    """Read all URLs from the extracted links file"""

    links = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    links.append(line)

        print(f"Found {len(links)} links to process")
        return links

    except FileNotFoundError:
        print(f"Error: {file_path} not found. Run extract_all_links.py first.")
        return []

def run_doc_fetcher(url, output_base, delay=1.0, use_playwright=False):
    """Run the doc fetcher on a single URL"""

    # Create safe filename from URL - works with any domain
    parsed = urlparse(url)

    # Get just the path part, removing the domain
    url_part = parsed.path + (('_' + parsed.query) if parsed.query else '')

    # Clean up to make filesystem-safe
    url_part = url_part.strip('/')
    url_part = url_part.replace('/', '_').replace('.html', '').replace('.htm', '')
    url_part = url_part.replace('?', '_').replace('&', '_').replace('=', '_')
    url_part = url_part.replace('-', '_').replace('.', '_')

    # Limit filename length
    if len(url_part) > 50:
        url_part = url_part[:50]

    # Ensure we have a valid name
    if not url_part or url_part == '_':
        url_part = f"page_{hash(url) % 100000}"

    output_dir = f"{output_base}/{url_part}"

    # Get the scripts directory
    script_dir = Path(__file__).parent
    api_fetcher = script_dir / 'api_docs_fetcher.py'

    cmd = [
        'python', str(api_fetcher),
        url,
        '--output', output_dir,
        '--depth', '2',  # Keep depth low for individual processing
        '--delay', str(delay)
    ]

    # Add Playwright flag if enabled
    if use_playwright:
        cmd.append('--use-playwright')

    try:
        print(f"Processing: {url}")
        print(f"Output: {output_dir}")

        result = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              timeout=120)  # 2 minute timeout per URL

        if result.returncode == 0:
            print(f"  SUCCESS: {url}")
            return True, None
        else:
            error_msg = result.stderr or result.stdout
            print(f"  FAILED: {url} - {error_msg}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {url}")
        return False, "Timeout"
    except Exception as e:
        print(f"  ERROR: {url} - {e}")
        return False, str(e)

def main():
    """Process all extracted links"""

    parser = argparse.ArgumentParser(description='Fetch all extracted documentation links')
    parser.add_argument('--log-dir', help='Log directory containing extracted_links.txt (auto-detects latest if not specified)')
    parser.add_argument('--output', help='Output directory name (default: auto-generated from domain)')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests (seconds)')
    parser.add_argument('--use-playwright', action='store_true',
                       help='Use Playwright for JavaScript-rendered sites (slower but more complete)')
    args = parser.parse_args()

    # Find the log directory
    if args.log_dir:
        log_dir = Path(args.log_dir)
    else:
        # Auto-detect the latest log directory
        logs_path = Path("logs")
        if not logs_path.exists():
            print("Error: No logs directory found. Run extract_all_links.py first.")
            return
        log_dirs = sorted(logs_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        if not log_dirs:
            print("Error: No log directories found. Run extract_all_links.py first.")
            return
        log_dir = log_dirs[0]
        print(f"Using latest log directory: {log_dir}")

    # Read all links
    links_file = log_dir / "extracted_links.txt"
    links = read_extracted_links(str(links_file))

    if not links:
        print("No links to process. Exiting.")
        return

    # Auto-detect domain from first link to create output folder name
    if args.output:
        output_base = args.output
    else:
        # Extract domain from first link
        first_url = links[0]
        parsed = urlparse(first_url)
        domain = parsed.netloc

        # Create a clean folder name from domain
        # e.g., "developer.acronis.com" -> "acronis_docs"
        # e.g., "docs.stripe.com" -> "stripe_docs"
        # e.g., "aws.amazon.com" -> "aws_docs"
        if 'acronis' in domain:
            output_base = 'acronis_docs'
        elif 'stripe' in domain:
            output_base = 'stripe_docs'
        elif 'aws' in domain or 'amazon' in domain:
            output_base = 'aws_docs'
        else:
            # Generic: take the main part of the domain
            parts = domain.split('.')
            # Remove common prefixes like 'docs', 'developer', 'api'
            main_parts = [p for p in parts if p not in ['docs', 'doc', 'developer', 'dev', 'api', 'www', 'com', 'org', 'net', 'io']]
            if main_parts:
                output_base = main_parts[0] + '_docs'
            else:
                output_base = parts[0] + '_docs' if parts else 'documentation'

        # Ensure output is in api_docs directory
        output_base = f"api_docs/{output_base}"

    print(f"\nStarting to process {len(links)} documentation links...")
    print(f"Output directory: {output_base}/")
    print("=" * 60)

    # Track progress
    successful = []
    failed = []

    # Process each link
    for i, url in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] Processing: {url}")

        success, error = run_doc_fetcher(url, output_base, delay=args.delay, use_playwright=args.use_playwright)

        if success:
            successful.append(url)
        else:
            failed.append((url, error))

        # Progress update every 10 links
        if i % 10 == 0:
            print(f"\n--- Progress: {i}/{len(links)} completed ---")
            print(f"Successful: {len(successful)}, Failed: {len(failed)}")

        # Small delay between processing
        time.sleep(0.5)

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total links processed: {len(links)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Success rate: {len(successful)/len(links)*100:.1f}%")

    # Save results to log directory
    results_file = log_dir / "fetch_results.txt"
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("Documentation Fetch Results\n")
        f.write("=" * 30 + "\n\n")
        f.write(f"Total processed: {len(links)}\n")
        f.write(f"Successful: {len(successful)}\n")
        f.write(f"Failed: {len(failed)}\n\n")

        if successful:
            f.write("SUCCESSFUL LINKS:\n")
            f.write("-" * 20 + "\n")
            for url in successful:
                f.write(f"{url}\n")
            f.write("\n")

        if failed:
            f.write("FAILED LINKS:\n")
            f.write("-" * 20 + "\n")
            for url, error in failed:
                f.write(f"{url} - {error}\n")

    print(f"\nResults saved to {results_file}")
    print(f"Documentation saved to: {output_base}/")

    if failed:
        print(f"\nNote: {len(failed)} links failed. Check fetch_results.txt for details.")

if __name__ == "__main__":
    main()