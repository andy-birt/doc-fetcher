#!/usr/bin/env python3
"""
API Documentation Fetcher
A flexible tool for extracting and organizing API documentation from various sources
Supports both static and JavaScript-rendered sites
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Set, Optional
import yaml
import argparse
from dataclasses import dataclass
from pathlib import Path

# Playwright imports - optional, will fallback to requests if not available
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

@dataclass
class FetcherConfig:
    """Configuration for the documentation fetcher"""
    base_urls: List[str]
    output_dir: str
    max_depth: int = 2
    delay_seconds: float = 0.5
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    custom_headers: Dict[str, str] = None
    follow_external_links: bool = False
    extract_code_examples: bool = True
    extract_api_endpoints: bool = True
    create_index: bool = True
    use_playwright: bool = False

class APIDocsFetcher:
    """API documentation fetcher that works with various documentation sites"""
    
    def __init__(self, config: FetcherConfig):
        self.config = config
        self.session = requests.Session()
        
        # Set default headers
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if config.custom_headers:
            default_headers.update(config.custom_headers)
        
        self.session.headers.update(default_headers)
        
        self.visited_urls: Set[str] = set()
        self.failed_urls: List[str] = []
        self.successful_pages: List[Dict] = []
        
        # Common API documentation patterns
        self.endpoint_patterns = [
            r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s\n\)]+)',
            r'(/api/[^\s\n\)\>]+)',
            r'(https?://[^/\s]+/api/[^\s\n\)\>]+)',
            r'(\{[^}]*\}[^\s]*)',  # Template variables
        ]
        
        # Common documentation section patterns
        self.section_patterns = [
            'authentication',
            'authorization', 
            'endpoints',
            'parameters',
            'responses',
            'examples',
            'errors',
            'rate.?limiting',
            'getting.?started',
            'quick.?start'
        ]

    def should_fetch_url(self, url: str) -> bool:
        """Determine if a URL should be fetched based on patterns"""
        
        if url in self.visited_urls:
            return False
        
        # Check if external links are allowed
        if not self.config.follow_external_links:
            base_domains = [urlparse(base_url).netloc for base_url in self.config.base_urls]
            if urlparse(url).netloc not in base_domains:
                return False
        
        # Check include patterns
        if self.config.include_patterns:
            if not any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.include_patterns):
                return False
        
        # Check exclude patterns
        if self.config.exclude_patterns:
            if any(re.search(pattern, url, re.IGNORECASE) for pattern in self.config.exclude_patterns):
                return False
        
        return True

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a single page"""

        if not self.should_fetch_url(url):
            return None

        try:
            print(f"Fetching: {url}")

            # Use Playwright if enabled
            if self.config.use_playwright and PLAYWRIGHT_AVAILABLE:
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        # Use 'load' instead of 'networkidle' for faster loading
                        page.goto(url, wait_until='load', timeout=60000)
                        # Wait for dynamic content to load
                        page.wait_for_timeout(3000)
                        html_content = page.content()
                        browser.close()

                        self.visited_urls.add(url)
                        time.sleep(self.config.delay_seconds)
                        return BeautifulSoup(html_content, 'html.parser')
                except Exception as e:
                    print(f"Playwright error for {url}: {e}, falling back to requests")

            # Use requests (default or fallback)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.visited_urls.add(url)

            # Rate limiting
            time.sleep(self.config.delay_seconds)

            return BeautifulSoup(response.content, 'html.parser')

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            self.failed_urls.append(url)
            return None

    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title using various strategies"""
        
        # Try different title sources in order of preference
        title_selectors = [
            'h1',
            'title', 
            '.page-title',
            '.doc-title',
            '.api-title',
            '[role="heading"][aria-level="1"]'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) < 200:  # Reasonable title length
                    return title
        
        return "Untitled"

    def extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract the main content area from the page"""
        
        # Common content selectors (in order of preference)
        content_selectors = [
            'main',
            '[role="main"]',
            '.main-content',
            '.content',
            '.documentation',
            '.api-docs',
            '.doc-content',
            'article',
            '.markdown-body',  # GitHub style
            '.rst-content',    # Read the Docs style
            'body'  # Fallback
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                return content
        
        return soup

    def extract_sections(self, content: BeautifulSoup) -> List[Dict]:
        """Extract structured sections from content"""
        
        sections = []
        current_section = None
        
        # Find all headings and content
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'pre', 'table', 'ul', 'ol']):
            
            if element.name and element.name.startswith('h'):
                # New section
                if current_section and current_section.get('content'):
                    sections.append(current_section)
                
                current_section = {
                    'level': int(element.name[1]),
                    'title': element.get_text().strip(),
                    'content': []
                }
            
            elif current_section is not None:
                # Add content to current section
                text = element.get_text().strip()
                if text and len(text) > 10:  # Skip very short snippets
                    current_section['content'].append(text)
        
        # Don't forget the last section
        if current_section and current_section.get('content'):
            sections.append(current_section)
        
        return sections

    def extract_api_endpoints(self, content: BeautifulSoup) -> List[Dict]:
        """Extract API endpoints from the content"""
        
        if not self.config.extract_api_endpoints:
            return []
        
        endpoints = []
        text_content = content.get_text()
        
        # Extract using patterns
        for pattern in self.endpoint_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) >= 2:
                        endpoints.append({
                            'method': match[0].upper() if match[0].upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] else 'GET',
                            'path': match[1],
                            'type': 'endpoint'
                        })
                    else:
                        endpoints.append({
                            'method': 'GET',
                            'path': match[0],
                            'type': 'endpoint'
                        })
                else:
                    endpoints.append({
                        'method': 'GET',
                        'path': match,
                        'type': 'endpoint'
                    })
        
        # Extract from tables (common in API docs)
        for table in content.find_all('table'):
            headers = [th.get_text().strip().lower() for th in table.find_all('th')]
            
            if any(keyword in ' '.join(headers) for keyword in ['endpoint', 'method', 'path', 'url']):
                for row in table.find_all('tr')[1:]:  # Skip header
                    cells = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                    if len(cells) >= 2:
                        endpoints.append({
                            'type': 'table_endpoint',
                            'data': cells
                        })
        
        # Remove duplicates
        unique_endpoints = []
        seen = set()
        for endpoint in endpoints:
            key = f"{endpoint.get('method', 'GET')}:{endpoint.get('path', '')}"
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(endpoint)
        
        return unique_endpoints

    def extract_code_examples(self, content: BeautifulSoup) -> List[Dict]:
        """Extract code examples from the content"""
        
        if not self.config.extract_code_examples:
            return []
        
        examples = []
        
        # Find code blocks
        for code_block in content.find_all(['pre', 'code']):
            code_text = code_block.get_text().strip()
            
            if len(code_text) < 20:  # Skip very short snippets
                continue
            
            # Determine language
            language = 'text'
            
            # Check class attributes for language hints
            class_attr = code_block.get('class', [])
            for cls in class_attr:
                if any(lang in cls.lower() for lang in ['python', 'javascript', 'bash', 'curl', 'json', 'xml']):
                    language = cls.lower()
                    break
            
            # Language detection from content patterns
            if language == 'text':
                if re.search(r'^(curl|wget)', code_text.strip(), re.MULTILINE):
                    language = 'bash'
                elif re.search(r'^(import|def|class)', code_text.strip(), re.MULTILINE):
                    language = 'python'
                elif re.search(r'^(\{|\[)', code_text.strip()):
                    language = 'json'
                elif re.search(r'<[^>]+>', code_text):
                    language = 'xml'
            
            examples.append({
                'language': language,
                'code': code_text,
                'length': len(code_text)
            })
        
        return examples

    def find_navigation_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find relevant navigation links"""
        
        links = []
        
        # Common navigation selectors
        nav_selectors = [
            'nav a',
            '.navigation a',
            '.nav a', 
            '.sidebar a',
            '.toc a',
            '.menu a',
            'ul.nav a',
            '[role="navigation"] a'
        ]
        
        for selector in nav_selectors:
            for link in soup.select(selector):
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.should_fetch_url(full_url):
                        links.append(full_url)
        
        return list(set(links))  # Remove duplicates

    def extract_page_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract all relevant content from a page"""
        
        if not soup:
            return {}
        
        title = self.extract_title(soup)
        main_content = self.extract_main_content(soup)
        
        content = {
            'url': url,
            'title': title,
            'sections': self.extract_sections(main_content),
            'api_endpoints': self.extract_api_endpoints(main_content),
            'code_examples': self.extract_code_examples(main_content),
            'navigation_links': self.find_navigation_links(soup, url)
        }
        
        return content

    def convert_to_markdown(self, content: Dict, api_name: str = None) -> str:
        """Convert extracted content to markdown"""
        
        md_lines = []
        
        # Title
        title = content.get('title', 'API Documentation')
        if api_name:
            title = f"{api_name} - {title}"
        
        md_lines.extend([
            f"# {title}",
            "",
            f"**Source:** {content['url']}",
            ""
        ])
        
        # Sections
        for section in content.get('sections', []):
            heading_level = min(section['level'] + 1, 6)  # Cap at h6
            heading_marker = '#' * heading_level
            
            md_lines.extend([
                f"{heading_marker} {section['title']}",
                ""
            ])
            
            for content_item in section['content'][:3]:  # Limit content per section
                md_lines.extend([
                    content_item,
                    ""
                ])
        
        # API Endpoints
        if content.get('api_endpoints'):
            md_lines.extend([
                "## API Endpoints",
                ""
            ])
            
            for endpoint in content['api_endpoints'][:10]:  # Limit endpoints
                if endpoint.get('type') == 'table_endpoint':
                    md_lines.extend([
                        f"- **Table Data:** {' | '.join(endpoint.get('data', []))}",
                    ])
                else:
                    method = endpoint.get('method', 'GET')
                    path = endpoint.get('path', '')
                    md_lines.extend([
                        f"- **{method}** `{path}`",
                    ])
            
            md_lines.append("")
        
        # Code Examples
        if content.get('code_examples'):
            md_lines.extend([
                "## Code Examples",
                ""
            ])
            
            for i, example in enumerate(content['code_examples'][:5]):  # Limit examples
                lang = example.get('language', 'text')
                code = example['code']
                
                # Truncate very long examples
                if len(code) > 1000:
                    code = code[:1000] + "\n... (truncated)"
                
                md_lines.extend([
                    f"### Example {i+1} ({lang})",
                    "",
                    f"```{lang}",
                    code,
                    "```",
                    ""
                ])
        
        return '\n'.join(md_lines)

    def crawl_documentation(self) -> Dict[str, str]:
        """Crawl all documentation and return file mapping"""
        
        # Create output directory
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        created_files = {}
        
        # Process each base URL
        for base_url in self.config.base_urls:
            print(f"\n=== Processing: {base_url} ===")
            
            # Extract API name from URL for file naming
            parsed_url = urlparse(base_url)
            api_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
            
            # Crawl this URL and its linked pages
            pages_to_process = [base_url]
            processed_count = 0
            
            while pages_to_process and processed_count < 20:  # Limit total pages
                url = pages_to_process.pop(0)
                
                if url in self.visited_urls:
                    continue
                
                soup = self.fetch_page(url)
                if not soup:
                    continue
                
                # Extract content
                page_content = self.extract_page_content(soup, url)
                if not page_content:
                    continue
                
                self.successful_pages.append(page_content)
                
                # Create filename
                title = page_content.get('title', 'untitled')
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                filename = f"{api_name}_{processed_count:02d}_{safe_title}.md"
                
                # Convert to markdown
                markdown_content = self.convert_to_markdown(page_content, api_name)
                
                # Save file
                file_path = output_path / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                created_files[filename] = str(file_path)
                print(f"  Created: {filename}")
                
                # Add linked pages for further crawling (if depth allows)
                if processed_count < self.config.max_depth:
                    for link in page_content.get('navigation_links', [])[:5]:  # Limit links per page
                        if link not in pages_to_process and link not in self.visited_urls:
                            pages_to_process.append(link)
                
                processed_count += 1
        
        # Create index file
        if self.config.create_index:
            self.create_index_file(output_path, created_files)
        
        return created_files

    def create_index_file(self, output_path: Path, created_files: Dict[str, str]):
        """Create an index file"""
        
        index_content = [
            "# API Documentation Index",
            "",
            f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Source URLs:**"
        ]
        
        for url in self.config.base_urls:
            index_content.append(f"- {url}")
        
        index_content.extend([
            "",
            "## Documentation Files",
            ""
        ])
        
        for filename in sorted(created_files.keys()):
            title = filename.replace('.md', '').replace('_', ' ').title()
            index_content.append(f"- [{title}](./{filename})")
        
        index_content.extend([
            "",
            "## Summary",
            "",
            f"- Total files: {len(created_files)}",
            f"- Successfully processed: {len(self.successful_pages)}",
            f"- Failed URLs: {len(self.failed_urls)}",
            ""
        ])
        
        if self.failed_urls:
            index_content.extend([
                "### Failed URLs:",
                ""
            ])
            for url in self.failed_urls:
                index_content.append(f"- {url}")
        
        # Write index
        index_path = output_path / "README.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(index_content))
        
        print(f"Created index: {index_path}")

def load_config_from_file(config_file: str) -> FetcherConfig:
    """Load configuration from YAML or JSON file"""
    
    with open(config_file, 'r') as f:
        if config_file.endswith('.yaml') or config_file.endswith('.yml'):
            config_data = yaml.safe_load(f)
        else:
            config_data = json.load(f)
    
    return FetcherConfig(**config_data)

def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(description='API Documentation Fetcher')
    parser.add_argument('urls', nargs='+', help='Base URLs to fetch documentation from')
    parser.add_argument('-o', '--output', default='api_docs', help='Output directory')
    parser.add_argument('-d', '--depth', type=int, default=2, help='Maximum crawl depth')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')
    parser.add_argument('--config', help='Configuration file (YAML or JSON)')
    parser.add_argument('--include', nargs='*', help='URL patterns to include')
    parser.add_argument('--exclude', nargs='*', help='URL patterns to exclude')
    parser.add_argument('--no-examples', action='store_true', help='Skip code examples extraction')
    parser.add_argument('--no-endpoints', action='store_true', help='Skip API endpoints extraction')
    parser.add_argument('--use-playwright', action='store_true',
                       help='Use Playwright for JavaScript-rendered sites (slower but more complete)')

    args = parser.parse_args()
    
    # Load config from file if provided
    if args.config:
        config = load_config_from_file(args.config)
    else:
        # Create config from arguments
        config = FetcherConfig(
            base_urls=args.urls,
            output_dir=args.output,
            max_depth=args.depth,
            delay_seconds=args.delay,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
            extract_code_examples=not args.no_examples,
            extract_api_endpoints=not args.no_endpoints,
            use_playwright=args.use_playwright
        )
    
    print("API Documentation Fetcher")
    print("================================")
    print(f"URLs: {config.base_urls}")
    print(f"Output: {config.output_dir}")
    print(f"Max depth: {config.max_depth}")
    
    # Create and run fetcher
    fetcher = APIDocsFetcher(config)
    
    try:
        created_files = fetcher.crawl_documentation()
        
        print(f"\nDocumentation fetch complete!")
        print(f"Output directory: {config.output_dir}")
        print(f"Total files created: {len(created_files)}")
        print(f"Successful pages: {len(fetcher.successful_pages)}")
        print(f"Failed URLs: {len(fetcher.failed_urls)}")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
