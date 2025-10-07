#!/usr/bin/env python3
"""
Documentation Structure Discovery Tool
Discovers all documentation sections from a site before fetching
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
from typing import Set, List, Dict
import re

class DocStructureDiscoverer:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.visited = set()
        self.doc_structure = {}

    def discover_structure(self, url: str, depth: int = 0, max_depth: int = 3) -> Dict:
        """Discover documentation structure by analyzing navigation and links"""

        if url in self.visited or depth > max_depth:
            return {}

        self.visited.add(url)

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            structure = {
                'url': url,
                'title': soup.find('title').text if soup.find('title') else 'No Title',
                'sections': {}
            }

            # Look for navigation elements (common patterns)
            nav_selectors = [
                'nav',
                '.navigation',
                '.sidebar',
                '.toc',
                '.menu',
                '[class*="nav"]',
                '[class*="sidebar"]',
                '[class*="menu"]',
                '.left-nav',
                '.docs-nav'
            ]

            links_found = set()

            for selector in nav_selectors:
                nav_elements = soup.select(selector)
                for nav in nav_elements:
                    # Find all links in navigation
                    for link in nav.find_all('a', href=True):
                        href = link['href']
                        if not href.startswith(('http://', 'https://', 'mailto:', '#', 'javascript:')):
                            href = urljoin(url, href)

                        # Only include links from same domain
                        if urlparse(href).netloc == urlparse(self.base_url).netloc:
                            links_found.add((href, link.get_text(strip=True)))

            # Also look for main content area links that look like documentation
            content_areas = soup.select('main, .content, .main-content, article')
            for area in content_areas:
                for link in area.find_all('a', href=True):
                    text = link.get_text(strip=True)
                    href = link['href']

                    # Check if this looks like a documentation link
                    if any(keyword in text.lower() or keyword in href.lower()
                           for keyword in ['api', 'guide', 'tutorial', 'reference', 'getting started',
                                         'authentication', 'account', 'user', 'service']):
                        if not href.startswith(('http://', 'https://', 'mailto:', '#', 'javascript:')):
                            href = urljoin(url, href)

                        if urlparse(href).netloc == urlparse(self.base_url).netloc:
                            links_found.add((href, text))

            # Organize links by path structure
            for link_url, link_text in links_found:
                if link_url != url and link_text:  # Avoid self-references
                    # Extract section from URL path
                    path = urlparse(link_url).path
                    parts = [p for p in path.split('/') if p]

                    if len(parts) > 0:
                        section_key = parts[-2] if len(parts) > 1 else parts[-1]
                        section_key = section_key.replace('.html', '').replace('-', ' ').title()

                        if section_key not in structure['sections']:
                            structure['sections'][section_key] = []

                        structure['sections'][section_key].append({
                            'title': link_text,
                            'url': link_url,
                            'path': path
                        })

            return structure

        except Exception as e:
            print(f"Error discovering {url}: {e}")
            return {}

    def discover_all_sections(self, start_urls: List[str]) -> Dict:
        """Discover all documentation sections from multiple starting points"""

        all_sections = {}

        for url in start_urls:
            print(f"\nDiscovering structure from: {url}")
            structure = self.discover_structure(url)

            # Merge with existing sections
            for section, links in structure.get('sections', {}).items():
                if section not in all_sections:
                    all_sections[section] = []

                # Add unique links
                existing_urls = {link['url'] for link in all_sections[section]}
                for link in links:
                    if link['url'] not in existing_urls:
                        all_sections[section].append(link)

        return all_sections

    def generate_fetch_commands(self, sections: Dict, output_base: str = "acronis_docs") -> List[str]:
        """Generate fetch commands for each documentation section"""

        commands = []

        # Group by major sections
        major_sections = {}

        for section, links in sections.items():
            # Group related sections
            if any(keyword in section.lower() for keyword in ['account', 'user', 'tenant', 'service']):
                group = 'account_management'
            elif any(keyword in section.lower() for keyword in ['auth', 'login', 'token']):
                group = 'authentication'
            elif any(keyword in section.lower() for keyword in ['api', 'library', 'reference']):
                group = 'api_library'
            elif any(keyword in section.lower() for keyword in ['tutorial', 'guide', 'getting started']):
                group = 'tutorials'
            elif any(keyword in section.lower() for keyword in ['error', 'status', 'response']):
                group = 'errors_and_status'
            else:
                group = 'other'

            if group not in major_sections:
                major_sections[group] = []

            major_sections[group].extend(links)

        # Generate commands for each major section
        for group, links in major_sections.items():
            if links:
                # Get unique base URLs for this group
                urls = list(set(link['url'] for link in links[:5]))  # Limit to top 5 URLs per group

                cmd = f"python api_docs_fetcher.py {' '.join(urls)} --output {output_base}/{group} --depth 5 --delay 1.0"
                commands.append({
                    'group': group,
                    'command': cmd,
                    'urls': urls
                })

        return commands

def main():
    # Acronis documentation starting points
    start_urls = [
        "https://developer.acronis.com/doc/outbound/",
        "https://developer.acronis.com/doc/outbound/apis/",
        "https://developer.acronis.com/doc/outbound/apis/api-library/",
        "https://developer.acronis.com/doc/outbound/apis/authentication/",
        "https://developer.acronis.com/doc/outbound/apis/api-library/account/"
    ]

    print("Discovering Acronis Documentation Structure...")
    print("=" * 60)

    discoverer = DocStructureDiscoverer("https://developer.acronis.com")
    sections = discoverer.discover_all_sections(start_urls)

    print(f"\nFound {len(sections)} documentation sections:")
    print("-" * 60)

    for section, links in sorted(sections.items()):
        print(f"\n{section}:")
        for link in links[:3]:  # Show first 3 links per section
            print(f"  - {link['title']}")
            print(f"    {link['url']}")
        if len(links) > 3:
            print(f"  ... and {len(links) - 3} more")

    # Save structure to JSON
    with open('acronis_docs_structure.json', 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2)
    print(f"\nSaved documentation structure to acronis_docs_structure.json")

    # Generate fetch commands
    commands = discoverer.generate_fetch_commands(sections)

    print("\n" + "=" * 60)
    print("FETCH COMMANDS BY SECTION:")
    print("=" * 60)

    with open('fetch_commands.txt', 'w', encoding='utf-8') as f:
        for cmd_info in commands:
            print(f"\n# {cmd_info['group'].upper().replace('_', ' ')}")
            print(cmd_info['command'])
            f.write(f"# {cmd_info['group'].upper().replace('_', ' ')}\n")
            f.write(cmd_info['command'] + '\n\n')

    print("\nFetch commands saved to fetch_commands.txt")

    # Create a batch script
    with open('fetch_all_docs.bat', 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo Fetching Acronis Documentation in Sections\n')
        f.write('echo ==========================================\n\n')

        for cmd_info in commands:
            f.write(f'echo Fetching {cmd_info["group"]}...\n')
            f.write(cmd_info['command'] + '\n')
            f.write('echo.\n\n')

        f.write('echo All documentation fetched!\n')
        f.write('pause\n')

    print("Batch script saved to fetch_all_docs.bat")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"- Found {len(sections)} documentation sections")
    print(f"- Generated {len(commands)} fetch commands")
    print(f"- Total unique pages discovered: {len(discoverer.visited)}")
    print("\nYou can now:")
    print("1. Run individual commands from fetch_commands.txt")
    print("2. Run fetch_all_docs.bat to fetch everything")
    print("3. Review acronis_docs_structure.json for the full structure")

if __name__ == "__main__":
    main()