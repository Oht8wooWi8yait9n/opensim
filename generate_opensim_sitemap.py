#!/usr/bin/env python3
"""
OpenSim Confluence Documentation Sitemap & URL Generator
Crawls the active OpenSim Documentation space on Atlassian Confluence Cloud:
https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/

Discovers all active documentation pages and technical PDF attachments (tutorials,
workshops, papers, and user guides), extracting genuine last-modified dates and
generating an Onyx-optimized XML sitemap conforming to sitemaps.org.
"""

from datetime import datetime, timezone
import os
import re
import sys
import time
from urllib.parse import quote, urljoin
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import requests

BASE_URL = "https://opensimconfluence.atlassian.net"
SPACE_KEY = "OpenSim"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,*/*;q=0.8",
}

MINIMUM_EXPECTED_URLS = 450
PAGE_LIMIT = 100
ATTACHMENT_LIMIT = 50


def fetch_all_pages(session: requests.Session) -> list[dict]:
    """Fetch all active documentation pages from OpenSim space via REST API."""
    print("[*] Fetching active documentation pages from OpenSim space...")
    pages = []
    url = (
        f"{BASE_URL}/wiki/rest/api/content"
        f"?spaceKey={SPACE_KEY}&type=page&status=current"
        f"&limit={PAGE_LIMIT}&expand=history.lastUpdated"
    )

    while url:
        data = None
        for attempt in range(1, 4):
            try:
                resp = session.get(url, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    break
            except Exception as e:
                if attempt == 3:
                    print(f"[!] Error fetching pages: {e}")
                    raise
                time.sleep(1.5 * attempt)
        if not data:
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            webui = item.get("_links", {}).get("webui", "")
            if not webui:
                continue
            canonical_url = f"{BASE_URL}/wiki{webui}"
            lastmod = item.get("history", {}).get("lastUpdated", {}).get("when", "")[:10]
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", lastmod):
                lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            is_overview = "overview" in webui.lower()
            priority = "1.0" if is_overview else "0.8"
            changefreq = "weekly" if is_overview else "monthly"

            pages.append({
                "url": canonical_url,
                "title": item.get("title", ""),
                "lastmod": lastmod,
                "changefreq": changefreq,
                "priority": priority,
                "type": "PAGE",
            })

        print(f"    - Collected {len(results)} pages (total: {len(pages)})")

        next_link = data.get("_links", {}).get("next")
        if next_link:
            url = f"{BASE_URL}/wiki{next_link}" if not next_link.startswith("http") else next_link
        else:
            url = None

    return pages


def fetch_pdf_attachments(session: requests.Session) -> list[dict]:
    """Fetch technical PDF attachments (tutorials, guides, publications) in OpenSim space."""
    print("[*] Searching for technical PDF attachments in OpenSim space...")
    attachments = []
    cql = f'space={SPACE_KEY} and type=attachment and title~".pdf"'
    url = (
        f"{BASE_URL}/wiki/rest/api/content/search"
        f"?cql={quote(cql)}&limit={ATTACHMENT_LIMIT}"
        f"&expand=history.lastUpdated,container"
    )

    while url:
        data = None
        for attempt in range(1, 4):
            try:
                resp = session.get(url, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    break
            except Exception as e:
                if attempt == 3:
                    print(f"[!] Error fetching attachments: {e}")
                    break
                time.sleep(1.5 * attempt)
        if not data:
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            title = item.get("title", "")
            container_id = item.get("container", {}).get("id")
            if not container_id:
                continue

            # Standard permanent download URL for Confluence attachments
            dl_url = f"{BASE_URL}/wiki/download/attachments/{container_id}/{quote(title)}"
            lastmod = item.get("history", {}).get("lastUpdated", {}).get("when", "")[:10]
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", lastmod):
                lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            attachments.append({
                "url": dl_url,
                "title": title,
                "lastmod": lastmod,
                "changefreq": "monthly",
                "priority": "0.8",
                "type": "PDF",
            })

        print(f"    - Collected {len(results)} PDF attachments (total: {len(attachments)})")

        next_link = data.get("_links", {}).get("next")
        if next_link:
            url = f"{BASE_URL}/wiki{next_link}" if not next_link.startswith("http") else next_link
        else:
            url = None

    return attachments


def write_sitemap_xml(items: list[dict], output_path: str):
    """Write standard XML sitemap, preserving existing file if URLs are identical."""
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for item in items:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{escape(item['url'])}</loc>")
        xml_lines.append(f"    <lastmod>{item['lastmod']}</lastmod>")
        xml_lines.append(f"    <changefreq>{item['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{item['priority']}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")
    new_content = "\n".join(xml_lines) + "\n"

    # Smart comparison
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        old_urls = set(re.findall(r"<loc>(.*?)</loc>", old_content))
        new_urls = {escape(item["url"]) for item in items}
        if old_urls == new_urls:
            print(f"[+] XML Sitemap unchanged: {output_path} ({len(items)} URLs)")
            return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[+] Wrote XML Sitemap: {output_path} ({len(items)} URLs)")


def write_urls_txt(items: list[dict], output_path: str):
    """Write plain text URL list, preserving existing file if URLs are identical."""
    new_content = "\n".join(item["url"] for item in items) + "\n"

    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        if old_content.strip() == new_content.strip():
            print(f"[+] Plain text URL list unchanged: {output_path} ({len(items)} URLs)")
            return

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[+] Wrote plain text URL list: {output_path} ({len(items)} URLs)")


def main():
    print("=" * 70)
    print(" OpenSim Confluence Documentation Sitemap Generator")
    print(" Space: OpenSim (Active & Maintained Documentation)")
    print(f" Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    start_time = time.time()
    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Fetch Documentation Pages
    pages = fetch_all_pages(session)

    # 2. Fetch PDF Attachments
    attachments = fetch_pdf_attachments(session)

    # Combine and deduplicate by URL
    seen_urls = set()
    all_items = []

    # Sort pages: overview first, then alphabetically
    sorted_pages = sorted(pages, key=lambda p: (0 if "overview" in p["url"] else 1, p["url"]))
    sorted_pdfs = sorted(attachments, key=lambda a: a["url"])

    for item in sorted_pages + sorted_pdfs:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            all_items.append(item)

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"[+] Crawl Completed in {elapsed:.2f}s:")
    print(f"    - Documentation Pages:   {len(pages)}")
    print(f"    - Technical PDF Files:   {len(attachments)}")
    print(f"    - Total Unique Content:  {len(all_items)} URLs")
    print("=" * 70)

    # Safety validation
    if len(all_items) < MINIMUM_EXPECTED_URLS:
        print(
            f"[!] ERROR: Harvested {len(all_items)} URLs, below safety threshold "
            f"({MINIMUM_EXPECTED_URLS}). Aborting file update to prevent corruption."
        )
        sys.exit(1)

    # Write output files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sitemap_path = os.path.join(script_dir, "opensim_sitemap.xml")
    urls_txt_path = os.path.join(script_dir, "opensim_urls.txt")

    write_sitemap_xml(all_items, sitemap_path)
    write_urls_txt(all_items, urls_txt_path)

    print("\n[✓] All OpenSim sitemap operations completed successfully.")


if __name__ == "__main__":
    main()
