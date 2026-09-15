# OpenSim Confluence Documentation Sitemap & Scraper Solution

Automated, hardened sitemap generator and weekly synchronization pipeline for the active **OpenSim Documentation Space** hosted on Atlassian Confluence Cloud:
`https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim/`

This repository generates and maintains a comprehensive, production-ready XML sitemap (`opensim_sitemap.xml`) and plain text URL list (`opensim_urls.txt`) optimized for ingestion by **Onyx** (formerly Danswer) and other AI search / RAG platforms.

---

## Indexed Content Overview

The sitemap indexes **601** verified, high-value technical URLs:

- **538 Active Documentation Pages**:
  - OpenSim Overview & Getting Started
  - Core Modeling & Simulation Concepts
  - Tutorials & Workshops (Scaling, Inverse Kinematics, Inverse Dynamics, Static Optimization, RRA, CMC, Moco)
  - Developer Guides & API Architecture
  - Troubleshooting, FAQs, and Best Practices
- **63 Technical Full-Text PDF Files**:
  - Published research papers and validation studies
  - Workshop guides, tutorial worksheets, and lab templates
  - Technical manuals and conference presentations
- **Excluded Legacy Archives**: Excludes historical, deprecated spaces (`OpenSim33`, `OpenSim24`) to keep search results focused exclusively on the latest maintained documentation.

---

## Onyx Web Connector Configuration

In your Onyx Admin Console (**Connectors** → **Web**):

| Field | Configuration |
| :--- | :--- |
| **Connector Name** | `OpenSim-Documentation` |
| **Base URL** | `https://raw.githubusercontent.com/Oht8wooWi8yait9n/opensim/main/opensim_sitemap.xml` |
| **Scrape Method** | `sitemap` |

Click **Create Connector** to begin indexing the full OpenSim documentation library into Onyx.

---

## Repository Files

- [`opensim_sitemap.xml`](opensim_sitemap.xml): Standard XML sitemap conforming to the [sitemaps.org](https://www.sitemaps.org/protocol.html) protocol with accurate `<lastmod>`, `<changefreq>`, and `<priority>`.
- [`opensim_urls.txt`](opensim_urls.txt): Clean, newline-delimited list of all 601 URLs for direct inspection, curl scripts, or bulk ingestion.
- [`generate_opensim_sitemap.py`](generate_opensim_sitemap.py): The Python crawler script utilizing Atlassian Confluence Cloud's REST APIs.
- [`.github/workflows/update-sitemap.yml`](.github/workflows/update-sitemap.yml): GitHub Actions workflow for weekly automated synchronization.

---

## Architecture & Features

1. **High-Performance REST API Crawling**:
   - Instead of fragile HTML web scraping, the crawler directly queries Atlassian Confluence Cloud's REST endpoints (`/wiki/rest/api/content` and `/wiki/rest/api/content/search`).
   - Completes a full space crawl in **~6 to 8 seconds**.
2. **Accurate Modification Timestamps**:
   - Expands `history.lastUpdated` to extract the true publication/edit date for each page and attachment, populating `<lastmod>` accurately.
3. **Smart Idempotency & Zero-Diff Preservation**:
   - The generator parses existing files and compares URL sets before touching disk. If no new pages or attachments have changed, the file is not modified, preserving git history and disk timestamps.
4. **Safety Threshold Guards**:
   - Validates that at least 450 URLs are discovered before updating sitemaps, protecting against upstream API outages or empty writes.
5. **Automated Weekly Maintenance**:
   - Scheduled via GitHub Actions to run every Sunday at 00:00 UTC, with manual on-demand triggers available via `workflow_dispatch`.
