# Web Crawler

This is a web crawler tool built using Devstral's Crawl4AI library. It allows you to crawl websites, extract URLs, and optionally download media content.

## Features

- Crawls a given URL and extracts all linked pages
- Optionally performs deep crawling to follow all links on the website
- Can download images and files found during the crawl
- Saves results in markdown format with cleaned HTML content
- Provides detailed information about found images

## Installation

1. Clone this repository:
> git clone https://github.com/yourusername/web-crawler.git cd web-crawler


2. Create a virtual environment and install dependencies:
> python3 -m venv .venv
>
> source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
>
> pip install -r requirements.txt
>
> playwright install

## Usage
To run the crawler, simply execute the script with desired parameters:

python src/crawler.py "https://example.com" --deepcrawl --accept-downloads

## Parameters
* url: The URL to start crawling from (required)
* --deepcrawl: Perform a deep crawl following all links (optional|boolean)
* --accept-downloads: Download found images and files during the crawl (optional|boolean)

## Results
The crawler saves its results in the results directory, with one markdown file per crawled website containing the cleaned HTML content. If deep crawling is enabled, it also provides information about downloaded media.

## Configuration
You can configure various aspects of the crawler by modifying the parameters in the start_crawler function or by creating a configuration file.