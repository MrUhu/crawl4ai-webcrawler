import os
import asyncio
import argparse
import re
from crawl4ai import *
import requests
from urllib.parse import urlparse
from base64 import b64decode

# Maximum length for filenames on most filesystems (e.g., NTFS, ext4)
MAX_FILENAME_LENGTH = 255


async def start_crawler(
    url: str, depth: int, deepcrawl: bool = False, accept_downloads: bool = False, save_pdf: bool = False, save_screenshot: bool = False
) -> dict:
    """
    Starts the web crawler on the given URL.

    Args:
        url (str): The URL to start crawling from.
        depth (int): Depth of the crawl if deepcrawl is activated (default: 3)
        deepcrawl (bool): Whether to perform a deep crawl or not. This will follow all links and scrape the whole website including linked sites if True.
        accept_downloads (bool): Whether to download found images and files during the crawl.
        save_pdf (bool): Whether to save the crawled content as PDF files.
        save_screenshot (bool): Whether to capture screenshots of the crawled pages.

    Returns:
        dict: A dictionary containing all URLs that were crawled and media info if deepcrawl is enabled.
    """
    # Results path
    results_path = os.path.join("./results", sanitize_directory_name(url))
    downloads_path = os.path.join(results_path, "downloads")
    html_path = os.path.join(results_path, "html")
    md_path = os.path.join(results_path, "md")

    # Set up the results directory if it doesn't exist
    if not os.path.exists(results_path):
        os.makedirs(results_path)
    
    if not os.path.exists(html_path):
        os.makedirs(html_path)

    if not os.path.exists(md_path):
        os.makedirs(md_path)

    if not os.path.exists(downloads_path):
        os.makedirs(downloads_path)

    browser_config = BrowserConfig(
        accept_downloads=accept_downloads,
        downloads_path=downloads_path,  # Make sure to set a valid path
    )

    excluded_domains = []
    # Read excluded domains from file
    try:
        with open("excluded_domains.txt", "r") as f:
            excluded_domains = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        # Create the file with default content if it doesn't exist
        with open("excluded_domains.txt", "w") as f:
            f.write("")
        excluded_domains = []

    # Create a chain of filters
    filter_chain = FilterChain(
        [
            # Only crawl specific domains
            DomainFilter(blocked_domains=excluded_domains)
        ]
    )

    run_config = CrawlerRunConfig(
        deep_crawl_strategy=None
        if not deepcrawl
        else BFSDeepCrawlStrategy(
            max_depth=depth,  # Maximum depth for the crawl
            include_external=False,  # Whether to include external links in the crawl
            filter_chain=filter_chain,
        ),
        scraping_strategy=None if not deepcrawl else LXMLWebScrapingStrategy(),
        #verbose=True,  # Detailed logging
        exclude_external_links=True,  # Whether to exclude external links during the crawl
        exclude_social_media_links=True,
        #check_robots_txt=True,
        magic=True, # Might be too invasive at points
        simulate_user=True,
        remove_overlay_elements=True,
        wait_for_images=True,
        cache_mode=CacheMode.BYPASS if save_pdf or save_screenshot else CacheMode.ENABLED,
        pdf=save_pdf,
        screenshot=save_screenshot
    )

    async with AsyncWebCrawler(
        config=browser_config,
        verbose=True,
        headless=True,
        user_agent_mode="random",
        user_agent_generator_config={"device_type": "mobile", "os_type": "android"},
    ) as crawler:
        results = await crawler.arun(
            url=url,
            config=run_config,
        )

        print(f"Crawled {len(results)} pages in total")

        for result in results:
            if not result.success and result.status_code == 403:
                print(f"Error: {result.error_message}")
            elif result.success:
                print(f"URL: {result.url}")
                print(f"Depth: {result.metadata.get('depth', 0)}")

                # Create a filename based on the URL (sanitize the URL for filename)
                filename = sanitize_filename(result.url)

                try:
                    if result.markdown:
                        file_path = os.path.join(results_path, "md", filename + ".md")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(result.markdown)  # Write Markdown content to the file
                    if result.cleaned_html:
                        file_path = os.path.join(results_path, "html", filename + ".html")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(result.cleaned_html)  # Write cleaned html content to the file
                    if result.screenshot:
                        file_path = os.path.join(results_path, filename + ".png")
                        with open(file_path, "wb") as f:
                            f.write(b64decode(result.screenshot)) # Save created screenshot of website
                    if result.pdf:
                        file_path = os.path.join(results_path, filename + ".pdf")
                        with open(file_path, "wb") as f:
                            f.write(result.pdf) # Save created pdf of website
                except Exception as e:
                    # Write error to error.txt
                    error_file = os.path.join("./results", "error.txt")
                    with open(error_file, "a", encoding="utf-8") as err_f:
                        err_f.write(
                            f"Error writing {filename} with {file_path}: {str(e)}\n"
                        )

                images_info = result.media.get("images", [])
                print(f"Found {len(images_info)} images in total.")

                # Create images directory
                images_dir = os.path.join(results_path, "images")
                os.makedirs(images_dir, exist_ok=True)

                for i, img in enumerate(images_info[:5]):  # Inspect just the first 5
                    print(f"[Image {i}] URL: {img['src']}")

                    # Download image if not already downloaded
                    filename = sanitize_filename(img["src"], is_image=True)
                    save_path = os.path.join(images_dir, filename)

                    if not os.path.exists(save_path):
                        # TODO: img["src"] is only a truncated url that needs to be concatenated with the base url
                        success = download_image(img["src"], save_path)
                        if success:
                            print(f"Downloaded image {i} to {save_path}")
                        else:
                            print(f"Failed to download image {i}")
                    else:
                        print(f"Image {i} already exists at {save_path}")
            else:
                print(f"Failed to crawl {result.url}")

        return {
            "urls": result.urls
            if hasattr(result, "urls")
            else [],  # Return all crawled URLs
            "media": result.media
            if deepcrawl and hasattr(result, "media")
            else {},  # Return media info if deepcrawl is enabled
        }


def download_image(url, save_path):
    """
    Download an image from a given URL and save it to disk.

    Args:
        url (str): The URL of the image to download
        save_path (str): The local path where the image should be saved

    Returns:
        bool: True if download was successful, False otherwise

    Raises:
        requests.RequestException: If there's an issue with the HTTP request
        ValueError: If the URL is invalid or the save path is invalid
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError("Invalid URL provided")

        # Send GET request to download image
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses

        # Create directory if it doesn't exist
        os.makedirs(
            os.path.dirname(save_path) if os.path.dirname(save_path) else ".",
            exist_ok=True,
        )

        # Save image to file
        with open(save_path, "wb") as f:
            f.write(response.content)

        return True

    except requests.RequestException as e:
        print(f"Error downloading image: {e}")
        return False
    except ValueError as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def sanitize_filename(url: str, is_image: bool = False) -> str:
    """
    Sanitizes a URL to create a valid filename for Linux and Windows.

    Args:
        url (str): The URL to be sanitized.
        is_image (bool): Whether the filename is for an image (default: False).
    Returns:
        str: A sanitized filename based on the URL.
    """
    # Remove scheme and replace slashes with underscores
    filename = re.sub(r"https?://", "", url).replace("/", "_").replace("?", "_")

    # Replace other invalid characters for filenames
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    if len(filename) <= MAX_FILENAME_LENGTH:
        # Extract extension from URL if available
        parsed_url = urlparse(url)
        ext = os.path.splitext(parsed_url.path)[1]
        if ext:
            return f"{filename}{ext}"
        else:
            return f"{filename}"
    else:
        # If filename is still too long, truncate it
        truncated_filename = f"{filename[: MAX_FILENAME_LENGTH - 10]}_truncated"
        
        # Extract extension from URL if available
        parsed_url = urlparse(url)
        ext = os.path.splitext(parsed_url.path)[1]
        if ext:
            return f"{truncated_filename}{ext}"
        else:
            return f"{truncated_filename}"


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
        domain = re.search(r"(?P<name>[a-zA-Z0-9.-]+)", url.split("//")[-1]).group(
            "name"
        )
    except AttributeError:
        raise ValueError("Invalid URL format")

    # Remove any illegal characters for directory names and replace with underscores
    sanitized_name = re.sub(r"[^a-zA-Z0-9]", "_", domain)

    return sanitized_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Crawler Script")
    parser.add_argument("url", type=str, help="The URL to start crawling from")
    parser.add_argument(
        "--deepcrawl", action="store_true", help="Perform a deep crawl (default: False)"
    )
    parser.add_argument(
        "--depth", type=int, default=3, help="Depth of the crawl (default: 3)"
    )
    parser.add_argument(
        "--accept_downloads",
        action="store_true",
        help="Accept and download files during the crawl (default: False)",
    )
    parser.add_argument(
        "--save_pdf",
        action="store_true",
        help="Save pages as PDF (default: False)",
    )
    parser.add_argument(
        "--save_screenshot",
        action="store_true",
        help="Take screenshots of pages (default: False)",
    )

    args = parser.parse_args()
    urls_media = asyncio.run(
        start_crawler(
            args.url,
            deepcrawl=args.deepcrawl,
            depth=args.depth,
            accept_downloads=args.accept_downloads,
            save_pdf=args.save_pdf,
            save_screenshot=args.save_screenshot,
        )
    )
    # print(f"Crawled {len(urls_media['urls'])} URLs")  # Print the number of crawled URLs
