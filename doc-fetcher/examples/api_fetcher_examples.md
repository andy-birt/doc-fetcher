# API Documentation Fetcher Configuration Examples

## config_template.yaml
```yaml
# Basic configuration
base_urls:
  - "https://api.example.com/docs"
  - "https://docs.example.com/api"

output_dir: "example_api_docs"
max_depth: 2
delay_seconds: 0.5

# Optional: URL filtering
include_patterns:
  - ".*\/api\/.*"
  - ".*\/docs\/.*"
  - ".*authentication.*"

exclude_patterns:
  - ".*\/blog\/.*"
  - ".*\/changelog\/.*"
  - ".*\.pdf$"

# Optional: Custom headers
custom_headers:
  "Authorization": "Bearer your-token-here"
  "Accept": "text/html,application/json"

# Feature flags
follow_external_links: false
extract_code_examples: true
extract_api_endpoints: true
create_index: true
```

## Popular API Documentation Examples

### Stripe API
```yaml
base_urls:
  - "https://stripe.com/docs/api"
output_dir: "stripe_docs"
include_patterns:
  - ".*stripe\.com/docs.*"
exclude_patterns:
  - ".*\/changelog.*"
```

### Twilio API
```yaml
base_urls:
  - "https://www.twilio.com/docs/usage/api"
  - "https://www.twilio.com/docs/messaging"
output_dir: "twilio_docs"
max_depth: 3
```

### SendGrid API
```yaml
base_urls:
  - "https://sendgrid.com/docs/api-reference/"
output_dir: "sendgrid_docs"
include_patterns:
  - ".*sendgrid\.com/docs.*"
```

### GitHub API
```yaml
base_urls:
  - "https://docs.github.com/en/rest"
output_dir: "github_api_docs"
max_depth: 2
include_patterns:
  - ".*docs\.github\.com/en/rest.*"
```

### Salesforce API
```yaml
base_urls:
  - "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/"
output_dir: "salesforce_docs"
delay_seconds: 1.0  # Be respectful with Salesforce
```

### Shopify API
```yaml
base_urls:
  - "https://shopify.dev/docs/api/admin-rest"
  - "https://shopify.dev/docs/api/admin-graphql"
output_dir: "shopify_docs"
```

### HubSpot API
```yaml
base_urls:
  - "https://developers.hubspot.com/docs/api/overview"
output_dir: "hubspot_docs"
include_patterns:
  - ".*developers\.hubspot\.com/docs.*"
```

### Zoom API
```yaml
base_urls:
  - "https://marketplace.zoom.us/docs/api-reference/zoom-api"
output_dir: "zoom_docs"
```

### Slack API
```yaml
base_urls:
  - "https://api.slack.com/methods"
  - "https://api.slack.com/authentication"
output_dir: "slack_docs"
```

### Discord API
```yaml
base_urls:
  - "https://discord.com/developers/docs"
output_dir: "discord_docs"
```

## Usage Examples

### Command Line Usage

```bash
# Simple usage - just provide URLs
python api_docs_fetcher.py https://api.example.com/docs

# With options
python api_docs_fetcher.py \
    https://api.example.com/docs \
    https://docs.example.com/api \
    --output my_api_docs \
    --depth 3 \
    --delay 1.0

# With filtering
python api_docs_fetcher.py \
    https://docs.example.com \
    --include ".*\/api\/.*" ".*authentication.*" \
    --exclude ".*\/blog\/.*" ".*\.pdf$" \
    --output filtered_docs

# Using a config file
python api_docs_fetcher.py --config stripe_config.yaml

# Skip certain extractions for faster processing
python api_docs_fetcher.py \
    https://api.example.com/docs \
    --no-examples \
    --no-endpoints
```

### Programmatic Usage

```python
from api_docs_fetcher import APIDocsFetcher, FetcherConfig

# Create configuration
config = FetcherConfig(
    base_urls=["https://api.example.com/docs"],
    output_dir="example_docs",
    max_depth=2,
    delay_seconds=0.5,
    include_patterns=[".*\/api\/.*"],
    extract_code_examples=True,
    extract_api_endpoints=True
)

# Run fetcher
fetcher = APIDocsFetcher(config)
created_files = fetcher.crawl_documentation()

print(f"Created {len(created_files)} documentation files")
```

## Integration with Your Workflow

### For Prismatic Integrations

Create configs for APIs you frequently integrate:

```yaml
# prismatic_targets.yaml
base_urls:
  - "https://api.target-system.com/docs"
output_dir: "target_system_docs"
include_patterns:
  - ".*\/api\/.*"
  - ".*authentication.*"
  - ".*customers.*"
  - ".*webhook.*"
max_depth: 2
extract_api_endpoints: true
extract_code_examples: true
```

Then use in your story analysis:

```bash
# Fetch docs for the API you're integrating with
python api_docs_fetcher.py --config prismatic_targets.yaml

# Now you have clean markdown files to reference while working on stories
```

### Integration with AI Tools

The generated markdown files work perfectly with AI tools:

1. **Upload to Claude conversations** for story analysis
2. **Reference in prompts** for field mapping help
3. **Use as context** when building Prismatic components

### Automation Scripts

You can create automation around this:

```bash
#!/bin/bash
# fetch_integration_docs.sh

APIs=(
    "stripe:https://stripe.com/docs/api"
    "salesforce:https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/"
    "hubspot:https://developers.hubspot.com/docs/api/overview"
)

for api_info in "${APIs[@]}"; do
    IFS=':' read -r name url <<< "$api_info"
    echo "Fetching docs for $name..."
    python api_docs_fetcher.py "$url" --output "${name}_docs"
done
```

This gives you a powerful, reusable tool for any API documentation you need to work with!
