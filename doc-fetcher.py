#!/usr/bin/env python3
"""
Doc-Fetcher CLI
Simple command-line interface for the API documentation fetcher
"""

import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python doc-fetcher.py extract <url> [--max-pages N] [--playwright]")
        print("  python doc-fetcher.py fetch [--playwright] [--delay N]")
        print("\nExamples:")
        print("  python doc-fetcher.py extract https://developer.xero.com/documentation/ --playwright")
        print("  python doc-fetcher.py fetch --playwright")
        sys.exit(1)

    command = sys.argv[1]
    scripts_dir = Path(__file__).parent / "scripts"

    if command == "extract":
        if len(sys.argv) < 3:
            print("Error: URL required for extract command")
            print("Usage: python doc-fetcher.py extract <url> [options]")
            sys.exit(1)

        script = scripts_dir / "extract_all_links.py"
        # Translate --playwright to --use-playwright for the underlying script
        script_args = [arg if arg != "--playwright" else "--use-playwright" for arg in sys.argv[2:]]
        args = ["python", str(script)] + script_args

    elif command == "fetch":
        script = scripts_dir / "fetch_all_extracted_links.py"
        # Translate --playwright to --use-playwright for the underlying script
        script_args = [arg if arg != "--playwright" else "--use-playwright" for arg in sys.argv[2:]]
        args = ["python", str(script)] + script_args

    else:
        print(f"Error: Unknown command '{command}'")
        print("Valid commands: extract, fetch")
        sys.exit(1)

    # Run the command with unbuffered output
    try:
        # Add -u flag for unbuffered output
        args[1:1] = ['-u']
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)

if __name__ == "__main__":
    main()
