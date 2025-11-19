# Bioregistry Curation Automation

Minimal Flask application to extract PubMed metadata for a PMID, scrape a database homepage using `browser-use`, and produce an editable Bioregistry-style JSON output.

Requirements
- Python 3.8+
- see `requirements.txt` for Python dependencies

Quick setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
# then open http://127.0.0.1:5000
```

Notes
- The backend uses INDRA to fetch PubMed metadata (`pip install indra`).
- The database scraping uses `browser-use` via an async Agent (the exact provided scraping function is used).
- The frontend is a simple single-page app (`templates/index.html`) with vanilla JS in `static/script.js`.

Security & Usage
- This is a minimal demo. Be cautious when running automated web agents against external sites; ensure you respect robots.txt and the site's terms of service.
# Bioregistry Curation Automation

An automated pipeline for streamlining the Bioregistry curation process by extracting metadata from PubMed articles and database websites, generating standardized JSON output for registry entries.

## Overview

This tool automates the manual steps of Bioregistry curation by:
1. Extracting metadata from PubMed publications
2. Following database URLs to scrape additional information
3. Generating properly formatted JSON entries
4. Providing an interactive interface for curator review and editing

## Workflow

### 1. Input
Users provide a PubMed URL or PMID through a web interface.

### 2. PubMed Metadata Extraction
The pipeline automatically extracts:
- Author name
- PMID
- Article title
- DOI
- Database description
- Database URL
- Year publicated

### 3. Database Scraping
Using browser automation (browser-use), the tool:
- Navigates to the identified database URL
- Extracts structural information including:
  - Prefix patterns
  - ID patterns/regex
  - Example identifiers
  - Additional metadata fields
  - uri format

### 4. JSON Generation
Outputs a properly formatted JSON file following Bioregistry schema specifications.

### 5. Curator Review
Provides an editable interface where curators can:
- Review extracted information
- Correct any misidentified fields
- Add missing metadata
- Validate before final submission

## Technology Stack

- **Frontend**: Web interface for input and editing
- **INDRA API**: PubMed Metadata extraction (https://indra.readthedocs.io/en/latest/modules/literature/index.html#module-indra.literature.pubmed_client)
- **Browser Automation**: browser-use for dynamic content scraping
- **Output Format**: JSON (Bioregistry schema compliant)

## Goals

- Reduce manual curation time by automating repetitive extraction tasks
- Minimize human error in metadata transcription
- Standardize the curation workflow
- Maintain curator oversight through review interface


## Development Status

This project is currently in active development as part of the Bioregistry curation efforts at the Gyori Lab for Computational Biomedicine.

## Contributing

This is a personal project for automating Bioregistry curation workflows. If you're interested in contributing or have suggestions, please open an issue.

## Related Projects

- [Bioregistry](https://github.com/biopragmatics/bioregistry) - The main Bioregistry project
- [Bioregistry Documentation](https://bioregistry.io/)

## Author

Oscar Kangho Ji - Bioregistry Curator, Gyori Lab for Computational Biomedicine, Northeastern University
