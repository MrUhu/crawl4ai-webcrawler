import os
import asyncio
import argparse
import re
from crawl4ai import *

# Maximum length for filenames on most filesystems (e.g., NTFS, ext4)
MAX_FILENAME_LENGTH = 255

async def start_crawler(url: str, deepcrawl: bool = False, accept_downloads: bool = False) -> dict:
    """
    Starts the web crawler on the given URL.

    Args:
        url (str): The URL to start crawling from.
        deepcrawl (bool): Whether to perform a deep crawl or not. This will follow all links and scrape the whole website including linked sites if True.
        accept_downloads (bool): Whether to download found images and files during the crawl.
    Returns:
        dict: A dictionary containing all URLs that were crawled and media info if deepcrawl is enabled.
    """
    # Results path
    results_path = os.path.join('./results', sanitize_directory_name(url))
    downloads_path=os.path.join(results_path,'downloads')

    # Set up the results directory if it doesn't exist
    if not os.path.exists(results_path):
        os.makedirs(results_path)

    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)

    browser_config = BrowserConfig(
        accept_downloads=accept_downloads,
        downloads_path=downloads_path  # Make sure to set a valid path
    )

    # TODO: Configure Downloads Configuration when accept_downloads is set
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=None if not deepcrawl else BFSDeepCrawlStrategy(
            max_depth=3,  # Maximum depth for the crawl
            include_external=False  # Whether to include external links in the crawl
        ),
        scraping_strategy=None if not deepcrawl else LXMLWebScrapingStrategy(),
        verbose=True,            # Detailed logging
        cache_mode=CacheMode.ENABLED,  # Use normal read/write cache
        exclude_external_links=True  # Whether to exclude external links during the crawl
    )

    async with AsyncWebCrawler(
        config=browser_config,
        verbose=True,
        headless=True,
        user_agent_mode="random",
        user_agent_generator_config={
            "device_type": "mobile",
            "os_type": "android"
        },
        ) as crawler:
        results = await crawler.arun(
            url=url,
            config=run_config,
            bypass_cache=True,
            magic=True,
            cache_mode=CacheMode.BYPASS,
            remove_overlay_elements=True,
            wait_for_images = True,
            screenshot=True,
        )
        print(f"Crawled {len(results)} pages in total")

        for result in results:
            if result.success:
                print(f"URL: {result.url}")
                print(f"Depth: {result.metadata.get('depth', 0)}")

                # Create a filename based on the URL (sanitize the URL for filename)
                filename = sanitize_filename(result.url)
                file_path = os.path.join(results_path, filename)

                images_info = result.media.get("images", [])
                print(f"Found {len(images_info)} images in total.")
                for i, img in enumerate(images_info[:5]):  # Inspect just the first 5
                    print(f"[Image {i}] URL: {img['src']}")

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result.markdown)  # Write Markdown content to the file
            else:
                print(f"Failed to crawl {result.url}")
        
        return {
            "urls": result.urls if hasattr(result, 'urls') else [],  # Return all crawled URLs
            "media": result.media if deepcrawl and hasattr(result, 'media') else {}  # Return media info if deepcrawl is enabled
        }

def sanitize_filename(url):
    # Replace schemes and replace slashes with underscores to create a basic filename
    filename = url.replace('https://', '').replace('http://', '').replace('/', '_') + '.md'

    if len(filename) <= MAX_FILENAME_LENGTH:
        return filename

    # Try to decode the URL components
    from urllib.parse import unquote
    try:
        decoded_url = unquote(url)
        decoded_filename = decoded_url.replace('https://', '').replace('http://', '').replace('/', '_') + '.md'

        if len(decoded_filename) <= MAX_FILENAME_LENGTH:
            return decoded_filename
    except Exception as e:
        print(f"Failed to decode URL: {e}")

    # If filename is still too long, truncate it
    truncated_filename = filename[:MAX_FILENAME_LENGTH - 10] + '_truncated.md'

    return truncated_filename

def sanitize_directory_name(url: str) -> str:
    """
    Sanitizes the given URL to make it suitable for use as a directory name.

    Args:
        url (str): The input URL.

    Returns:
        str: A sanitized version of the URL domain suitable for use as a directory name.
    """
    # Extract the domain from the URL
    try:
        domain = re.search(r'(?P<name>[a-zA-Z0-9.-]+)', url.split('//')[-1]).group("name")
    except AttributeError:
        raise ValueError("Invalid URL format")

    # Remove any illegal characters for directory names and replace with underscores
    sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', domain)

    return sanitized_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Crawler Script")
    parser.add_argument("url", type=str, help="The URL to start crawling from")
    parser.add_argument("--deepcrawl", action='store_true', help="Perform a deep crawl (default: False)")
    parser.add_argument("--accept_downloads", action='store_true', help="Accept and download images and files during the crawl (default: False)")

    args = parser.parse_args()
    urls_media = asyncio.run(start_crawler(args.url, deepcrawl=args.deepcrawl, accept_downloads=args.accept_downloads))
    #print(f"Crawled {len(urls_media['urls'])} URLs")  # Print the number of crawled URLs
