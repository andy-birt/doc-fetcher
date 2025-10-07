# API Documentation Fetcher

A powerful tool that automatically discovers and downloads complete API documentation from any website, converting it to clean, organized markdown files.

## 🚀 Features

- **JavaScript Support** - Works with both static HTML and JavaScript-rendered sites using Playwright
- **API-Focused** - Optimized for API documentation sites
- **Automatic Discovery** - Finds all API documentation pages automatically
- **Smart Organization** - Creates logical folder structure with timestamped logs
- **Clean Markdown Output** - Converts HTML to readable markdown
- **Respectful Crawling** - Built-in delays and rate limiting
- **Batch Processing** - Handles hundreds of pages efficiently
- **Error Recovery** - Continues even if some pages fail
- **Progress Tracking** - Real-time progress updates and success rates
- **Historical Logs** - Each run is saved with timestamps for future reference

## 📦 Installation

### For Your Team (Recommended - with venv)

1. Clone this repository:
```bash
git clone https://github.com/yourusername/doc-fetcher.git
cd doc-fetcher
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

### Quick Install (without venv)

```bash
pip install requests beautifulsoup4 PyYAML playwright
playwright install chromium
```

## 📁 Project Structure

```
doc-fetcher/
├── scripts/              # All Python scripts
│   ├── extract_all_links.py
│   ├── fetch_all_extracted_links.py
│   └── api_docs_fetcher.py
├── configs/              # Configuration files
│   └── config_template.yaml
├── logs/                 # Timestamped logs for each run
│   └── xero_2025-10-03_16-05/
│       ├── extracted_links.txt
│       ├── fetch_commands.txt
│       └── fetch_results.txt
├── api_docs/            # All generated documentation
│   ├── xero_docs/
│   ├── acronis_docs/
│   └── stripe_docs/
└── README.md
```

## 🎯 Quick Start

### Using the CLI (Recommended)

```bash
# Step 1: Extract documentation links
python doc-fetcher.py extract https://developer.xero.com/documentation/ --playwright --max-pages 50

# Step 2: Fetch all documentation
python doc-fetcher.py fetch --playwright
```

### Using Scripts Directly

#### Step 1: Discover All API Documentation Links
```bash
python scripts/extract_all_links.py https://developer.xero.com/documentation/ --max-pages 50 --use-playwright
```

This will:
- Crawl the API documentation site using Playwright (for JavaScript-rendered sites)
- Discover all API documentation pages (up to 50 pages of crawling)
- Save all discovered URLs to `logs/xero_YYYY-MM-DD_HH-MM/extracted_links.txt`
- Create a timestamped log directory for this run

#### Step 2: Fetch All API Documentation
```bash
python scripts/fetch_all_extracted_links.py --use-playwright
```

This will:
- Auto-detect the latest log directory and read extracted links
- Auto-detect the domain and create output folder in `api_docs/` (e.g., `api_docs/xero_docs`)
- Download each API documentation page using Playwright
- Convert to clean markdown with extracted API endpoints and code examples
- Organize into a logical folder structure
- Save results to the log directory

## 📖 Detailed Usage

### Extract Links Tool

```bash
python extract_all_links.py <URL> [options]
```

**Options:**
- `--max-pages N` - Maximum pages to scan (default: 50)
- `--output FILE` - Output file for links (default: extracted_links.txt)

**Example:**
```bash
python extract_all_links.py https://stripe.com/docs/api --max-pages 100
```

### Fetch All API Documentation Tool

```bash
python fetch_all_extracted_links.py [options]
```

**Options:**
- `--output DIR` - Output directory name (default: auto-generated from domain)
- `--links-file FILE` - Input file with links (default: extracted_links.txt)
- `--delay SECONDS` - Delay between requests (default: 1.5)

**Examples:**
```bash
# Use auto-detected folder name (e.g., stripe_docs)
python fetch_all_extracted_links.py

# Specify custom output folder
python fetch_all_extracted_links.py --output my_stripe_docs

# Use different delay
python fetch_all_extracted_links.py --delay 2.0
```

### API Documentation Fetcher

For fetching specific API documentation pages or sections:

```bash
python api_docs_fetcher.py <URL> [URL2 URL3...] [options]
```

**Options:**
- `--output DIR` - Output directory (default: api_docs)
- `--depth N` - Maximum crawl depth (default: 2)
- `--delay SECONDS` - Delay between requests (default: 0.5)
- `--include PATTERN` - Include URL patterns (can specify multiple)
- `--exclude PATTERN` - Exclude URL patterns (can specify multiple)
- `--no-examples` - Skip code examples extraction
- `--no-endpoints` - Skip API endpoints extraction
- `--config FILE` - Use configuration file (YAML)

**Example:**
```bash
python api_docs_fetcher.py https://api.example.com/docs \
    --output example_docs \
    --depth 3 \
    --delay 1.0 \
    --include ".*\/api\/.*" ".*\/reference\/.*"
```

## 🌐 Real-World Examples

### Stripe API Documentation
```bash
# Step 1: Discover all Stripe API docs
python extract_all_links.py https://stripe.com/docs/api --max-pages 100

# Step 2: Fetch everything (creates stripe_docs/)
python fetch_all_extracted_links.py
```

### AWS Documentation
```bash
# Step 1: Discover AWS EC2 docs
python extract_all_links.py https://docs.aws.amazon.com/ec2/ --max-pages 50

# Step 2: Fetch everything (creates aws_docs/)
python fetch_all_extracted_links.py
```

### OpenAI API Documentation
```bash
# Step 1: Discover OpenAI docs
python extract_all_links.py https://platform.openai.com/docs --max-pages 50

# Step 2: Fetch with custom name
python fetch_all_extracted_links.py --output openai_api_docs
```

### GitHub REST API
```bash
# Step 1: Discover GitHub API docs
python extract_all_links.py https://docs.github.com/en/rest --max-pages 75

# Step 2: Fetch everything (creates github_docs/)
python fetch_all_extracted_links.py
```

## 📁 Output Structure

After fetching, your documentation will be organized like this:

```
stripe_docs/                    # Auto-named based on domain
├── api_charges/               # Each URL path becomes a folder
│   ├── developer_stripe_com_00_Charges.md
│   ├── developer_stripe_com_01_Create_Charge.md
│   ├── developer_stripe_com_02_Retrieve_Charge.md
│   └── README.md              # Index for this section
├── api_customers/
│   ├── developer_stripe_com_00_Customers.md
│   ├── developer_stripe_com_01_Create_Customer.md
│   └── README.md
├── api_payments/
│   └── ...
└── README.md                  # Main index file
```

## ⚙️ Configuration Files

For complex scenarios, you can use YAML configuration files:

```yaml
# config.yaml
base_urls:
  - "https://api.example.com/docs"
  - "https://docs.example.com/reference"

output_dir: "example_complete_docs"
max_depth: 3
delay_seconds: 1.0

include_patterns:
  - ".*\/api\/.*"
  - ".*\/reference\/.*"

exclude_patterns:
  - ".*\/blog\/.*"
  - ".*\.pdf$"

extract_code_examples: true
extract_api_endpoints: true
create_index: true
```

Use with:
```bash
python api_docs_fetcher.py --config config.yaml
```

## 🎯 Auto-Detection Features

The fetcher automatically detects and handles:

1. **Domain-Based Folder Naming:**
   - `developer.acronis.com` → `acronis_docs/`
   - `docs.stripe.com` → `stripe_docs/`
   - `aws.amazon.com` → `aws_docs/`
   - `platform.openai.com` → `openai_docs/`
   - Other domains → extracts main part (e.g., `example.com` → `example_docs/`)

2. **URL Path Conversion:**
   - `/api/v1/users` → `api_v1_users/`
   - `/reference/authentication.html` → `reference_authentication/`
   - Removes extensions, converts special characters to underscores

3. **Content Extraction:**
   - Identifies and extracts API endpoints
   - Preserves code examples with syntax highlighting
   - Maintains document structure and hierarchy
   - Cleans up navigation and ads

## 📊 Performance & Results

Based on real-world API documentation fetching:

- **Acronis API Documentation**: 595 pages fetched, 100% success rate
- **Processing Speed**: ~10-15 pages per minute (with respectful delays)
- **Output Size**: Clean markdown, typically 50-70% smaller than original HTML
- **API Extraction**: Automatic detection of endpoints, parameters, and code examples
- **Organization**: Automatic creation of logical folder structure based on API paths

## 🔧 Troubleshooting

### Common Issues

**No links discovered:**
- Increase `--max-pages` to scan more deeply
- Check if the site uses JavaScript rendering (not supported)
- Verify the starting URL is correct

**403 Forbidden errors:**
- Some sites require authentication
- Try adding custom headers in configuration
- Check robots.txt compliance

**Timeout errors:**
- Increase delay between requests
- Reduce crawl depth
- Some sites have rate limiting

**Empty output:**
- Site might use client-side rendering
- Check if content requires login
- Verify URL patterns in include/exclude

## 🚨 Best Practices

1. **Be Respectful:**
   - Use appropriate delays (1-2 seconds recommended)
   - Check robots.txt before crawling
   - Don't overwhelm servers with parallel requests

2. **Optimize Discovery:**
   - Start with smaller `--max-pages` to test
   - Use specific starting URLs for sections you need
   - Exclude non-documentation patterns (blog, changelog, etc.)

3. **Handle Large Sites:**
   - Process in batches if needed
   - Use configuration files for complex setups
   - Monitor progress and adjust delays if needed

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- JavaScript rendering support
- Parallel processing with rate limiting
- Better content extraction algorithms
- Authentication handling
- PDF and other format support

## 📝 License

MIT License - Use freely for documentation archival and reference purposes.

## ⚠️ Disclaimer

Always respect API documentation website terms of service and robots.txt. This tool is intended for:
- Creating offline API documentation references
- Backing up API documentation for development
- Integration development and testing
- Research and development purposes
- Personal use and archival

Do not use for:
- Violating website terms of service
- Overwhelming API documentation servers with requests
- Redistributing copyrighted API documentation
- Commercial scraping without permission

## 🆘 Support

For issues or questions:
- Check the troubleshooting section above
- Review the examples for your use case
- Ensure all dependencies are installed
- Verify network connectivity and permissions

---

**Built with Python** | **Powered by BeautifulSoup & Requests**