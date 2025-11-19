from flask import Flask, request, jsonify, render_template
import re
import json
import asyncio
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def extract_pubmed_metadata(pmid):
    """Extract metadata for a PMID using INDRA's pubmed client.

    Returns a dictionary with keys: title, doi, abstract, first_author, pmid, year, homepage (if found), description
    """
    try:
        from indra.literature.pubmed_client import get_metadata_for_ids
    except Exception as e:
        return {"error": f"INDRA import error: {e}"}

    try:
        # Request abstracts from INDRA so we can search the full abstract text for URLs
        raw = get_metadata_for_ids([str(pmid)], get_abstracts=True, detailed_authors=False)
    except Exception as e:
        return {"error": f"PubMed fetch error: {e}"}

    if not raw:
        return {"error": "No metadata returned from PubMed"}

    # raw is usually a dict keyed by pmid
    item = None
    if isinstance(raw, dict):
        item = raw.get(str(pmid)) or list(raw.values())[0]
    else:
        item = raw

    title = item.get("title") or ""
    doi = item.get("doi") or item.get("elocationid") or ""
    abstract = item.get("abstract") or ""

    # first author
    first_author = ""
    authors = item.get("authors") or item.get("author_list") or []
    if authors:
        if isinstance(authors[0], dict):
            first_author = authors[0].get("name") or authors[0].get("fullname") or ""
        else:
            first_author = str(authors[0])

    # year
    year = None
    if item.get("year"):
        try:
            year = int(item.get("year"))
        except Exception:
            year = None
    else:
        pubdate = item.get("pubdate") or ""
        m = re.search(r"(19|20)\d{2}", pubdate)
        if m:
            year = int(m.group(0))

    # find any URLs in the abstract; capture until whitespace or closing bracket
    raw_urls = re.findall(r"https?://[^\s\)\]]+", abstract)
    # clean trailing punctuation
    urls = [re.sub(r"[\.,;:]+$", "", u) for u in raw_urls]
    homepage = urls[0] if urls else ""

    # keywords: prefer INDRA-provided keywords when present
    keywords = []
    if isinstance(item, dict):
        kw = item.get('keywords') or item.get('mesh_terms') or item.get('keyword') or item.get('subject')
        if kw:
            if isinstance(kw, (list, tuple)):
                keywords = [str(x).strip() for x in kw if x]
            else:
                keywords = [k.strip() for k in str(kw).split(',') if k.strip()]

    return {
        "title": title,
        "doi": doi,
        "abstract": abstract,
        "first_author": first_author,
        "pmid": str(pmid),
        "year": year,
        "homepage": homepage,
        "keywords": keywords,
    }


async def extract_database_info(homepage_url):
    """Use browser_use Agent to extract database information from homepage."""
    from browser_use import Agent

    agent = Agent(
        task=rf"""Visit {homepage_url} and extract ONLY the following 8 lines,
in THIS EXACT ORDER. Each field must be on its own line and use the exact
label shown followed by a colon and the single value. If a value is unknown
or not present, return the label followed by an empty value. Return NOTHING
else (no explanations, no JSON, no headers/footers).

EXACT LINES (order matters):
Name: 
Description: 
Homepage: 
Example: 
Pattern: 
URI_Format: 
Contact_Name: 
Contact_Email: 

Example output (exact format):
Name: tsRNADisease
Description: Identifiers correspond to tRNA-halves and tRNA-derived fragments in the tsRNADisease database.
Homepage: http://www.compgenelab.info/tsRNADisease
Example: TRD00001
Pattern: ^TRD\d{5}$
URI_Format: http://www.compgenelab.info/tsRNADisease/detail.php?entry_ID=$1
Contact_Name: Zhen Yang
Contact_Email: zhenyang@fudan.edu.cn
""",
        llm_model="gpt-4o",
    )

    result = await agent.run()
    final = result.final_result() if hasattr(result, 'final_result') else str(result)

    # Replace escaped newlines with actual newlines
    text = (final or "").replace('\\n', '\n')

    # Parse line by line
    extracted = {
        'name': '', 'description': '', 'homepage': '', 'example': '',
        'pattern': '', 'uri_format': '', 'contact_name': '', 'contact_email': ''
    }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        m = re.match(r"^\s*([^:]+)\s*:\s*(.*)$", ln)
        if not m:
            continue
        raw_label = m.group(1).strip()
        val = m.group(2).strip()
        
        # Normalize label for matching
        label_norm = re.sub(r"[_\-\s]+", "_", raw_label).lower()
        
        if label_norm == 'name':
            extracted['name'] = val
        elif label_norm == 'description':
            extracted['description'] = val
        elif label_norm == 'homepage':
            extracted['homepage'] = val
        elif label_norm == 'example':
            extracted['example'] = val
        elif label_norm == 'pattern':
            # Unescape regex patterns (e.g., \\d becomes \d)
            extracted['pattern'] = val.replace('\\\\', '\\')
        elif 'uri' in label_norm and 'format' in label_norm:
            extracted['uri_format'] = val
        elif label_norm == 'contact_name':
            extracted['contact_name'] = val
        elif label_norm == 'contact_email':
            extracted['contact_email'] = val

    # If contact_email is still empty, try to find any email in the text
    if not extracted['contact_email']:
        m = re.search(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', text)
        if m:
            extracted['contact_email'] = m.group(1)

    # Use homepage_url as fallback
    if not extracted['homepage']:
        extracted['homepage'] = homepage_url

    return {
        "name": extracted['name'],
        "description": extracted['description'],
        "homepage": extracted['homepage'],
        "example": extracted['example'],
        "pattern": extracted['pattern'],
        "uri_format": extracted['uri_format'],
        "contact": {
            "email": extracted['contact_email'],
            "name": extracted['contact_name'],
            "orcid": ""
        }
    }


def _keywords_from_text(text, max_k=3):
    """Extract keywords from text as a fallback."""
    if not text:
        return []
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text).lower()
    words = text.split()
    stop = set(["the","and","for","with","that","this","from","are","was","were","using","use","data","database","resource","repository"])
    candidates = [w for w in words if len(w) > 5 and w not in stop]
    seen = []
    for w in candidates:
        if w not in seen:
            seen.append(w)
        if len(seen) >= max_k:
            break
    return seen


def format_bioregistry_json(pubmed, db):
    """Format the final Bioregistry JSON output."""
    # Get name from db data
    name = (db.get("name") if db else "").strip()
    
    # If no name, derive from homepage
    if not name:
        homepage = (db.get("homepage") if db else "") or pubmed.get("homepage", "")
        m = re.search(r"https?://(?:www\.)?([^/\.]+)", homepage)
        name = m.group(1) if m else "database"
    
    # Remove version suffixes from name
    name = re.sub(r"(?i)\s*(?:v|version)\s*\d+(?:\.\d+)*$", "", name).strip()
    
    # Create clean database key (alphanumeric only, lowercase)
    db_key = re.sub(r"[^0-9a-zA-Z]+", "", name).lower() or "database_key"

    # Extract contact info from db
    contact = {"email": "", "name": "", "orcid": ""}
    if db and db.get("contact"):
        contact_raw = db.get("contact")
        if isinstance(contact_raw, dict):
            contact["email"] = contact_raw.get("email", "")
            contact["name"] = contact_raw.get("name", "")
            contact["orcid"] = contact_raw.get("orcid", "")

    # Get other fields from db
    description = (db.get("description") if db else "")
    example = (db.get("example") if db else "")
    homepage = (db.get("homepage") if db else "") or pubmed.get("homepage", "")
    pattern = (db.get("pattern") if db else "")
    uri_format = (db.get("uri_format") if db else "")
    
    # Get keywords from INDRA or fallback to abstract extraction
    keywords = []
    if pubmed and pubmed.get('keywords'):
        keywords = pubmed.get('keywords')
    else:
        keywords = _keywords_from_text(pubmed.get("abstract", "") if pubmed else "")

    # Build publications list
    publications = []
    if pubmed:
        pub = {
            "doi": pubmed.get("doi") or "",
            "pubmed": pubmed.get("pmid") or "",
            "title": pubmed.get("title") or "",
            "year": pubmed.get("year") or None,
        }
        publications.append(pub)

    out = {
        db_key: {
            "contact": contact,
            "contributor": {"email": "", "github": "", "name": "", "orcid": ""},
            "description": description,
            "example": example,
            "homepage": homepage,
            "keywords": keywords,
            "name": name,
            "pattern": pattern,
            "publications": publications,
            "uri_format": uri_format,
        }
    }

    return out


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json() or {}
    pmid = (data.get('pmid') or '').strip()
    if not pmid or not re.fullmatch(r"\d+", pmid):
        return jsonify({"status": "error", "message": "Invalid PMID. Provide numeric PMID like 12345678."}), 400

    try:
        # Step 1: Extract PubMed metadata
        pubmed = extract_pubmed_metadata(pmid)
        if pubmed.get('error'):
            return jsonify({"status": "error", "message": pubmed.get('error')}), 500

        # Step 2: Find homepage URL in abstract
        abstract_text = pubmed.get('abstract') or ''
        raw_urls = re.findall(r"https?://[^\s\)\]]+", abstract_text)
        urls = [re.sub(r"[\.,;:]+$", "", u) for u in raw_urls]
        
        if not urls:
            # No URL to scrape — return error with publication-only data
            bioreg_partial = format_bioregistry_json(pubmed, None)
            return jsonify({
                "status": "error",
                "message": "No homepage URL found in the PubMed abstract; cannot run browser-use scraping.",
                "data": bioreg_partial
            }), 400

        homepage_url = urls[0]

        # Step 3: Extract database info using browser-use
        db_data = None
        try:
            db_data = asyncio.run(extract_database_info(homepage_url))
        except Exception as e:
            logging.exception('Database scraping failed')
            bioreg_partial = format_bioregistry_json(pubmed, None)
            return jsonify({
                "status": "error",
                "message": f"Database scraping failed: {e}",
                "data": bioreg_partial
            }), 500

        # Step 4: Format final Bioregistry JSON
        bioreg = format_bioregistry_json(pubmed, db_data)
        return jsonify({"status": "success", "data": bioreg})

    except Exception as e:
        logging.exception('Unexpected error')
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
