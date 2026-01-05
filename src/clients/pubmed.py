import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from Bio import Entrez

# Ensure we load .env once, from project root if possible
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)  # falls back silently if it doesn't exist


class PubMedClient:
    """
    Enhanced PubMed client using NCBI Entrez.

    - fetch_research(query, max_results) → rich metadata for graph + RAG
    - Includes: title, abstract, journal, date, authors, MeSH terms, keywords
    """

    def __init__(self, email: Optional[str] = None):
        # Use explicit email if passed, else from .env, else dummy
        self.email = email or os.getenv("PUBMED_EMAIL") or "your.email@example.com"
        Entrez.email = self.email  # required by NCBI

    def _parse_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single PubMed article into structured metadata.
        """
        citation = article.get("MedlineCitation", {})
        article_data = citation.get("Article", {})

        pmid = str(citation.get("PMID", ""))

        # Title
        raw_title = article_data.get("ArticleTitle", "")
        title = str(raw_title) if raw_title else "No Title"

        # Journal + year
        journal_data = article_data.get("Journal", {}) or {}
        journal = (
            journal_data.get("Title")
            or journal_data.get("ISOAbbreviation")
            or ""
        )

        year: Optional[str] = None
        pub_date = journal_data.get("JournalIssue", {}).get("PubDate", {}) or {}
        # Try Year, then MedlineDate as a fallback
        if pub_date.get("Year"):
            year = str(pub_date["Year"])
        elif pub_date.get("MedlineDate"):
            year = str(pub_date["MedlineDate"])

        # Authors (keep it simple: "Last Initials")
        authors: List[str] = []
        for a in article_data.get("AuthorList", []) or []:
            last = a.get("LastName")
            initials = a.get("Initials")
            if last and initials:
                authors.append(f"{last} {initials}")
            elif last:
                authors.append(last)

        # Abstract + labeled sections
        abstract_obj = article_data.get("Abstract", {}) or {}
        abstract_elems = abstract_obj.get("AbstractText", []) or []

        abstract_sections: Dict[str, str] = {}
        abstract_paragraphs: List[str] = []

        for elem in abstract_elems:
            # elem can be a plain string or a StringElement with .attributes
            text = str(elem).strip()
            if not text:
                continue

            label = None
            if hasattr(elem, "attributes"):
                label = elem.attributes.get("Label") or elem.attributes.get("NlmCategory")

            if label:
                key = str(label).upper()
                abstract_sections[key] = (abstract_sections.get(key, "") + " " + text).strip()
                # fold label into the "flat" abstract as well
                abstract_paragraphs.append(f"{label}: {text}")
            else:
                abstract_paragraphs.append(text)

        abstract = " ".join(abstract_paragraphs) if abstract_paragraphs else "No Abstract"

        # MeSH terms
        mesh_terms: List[str] = []
        for mh in citation.get("MeshHeadingList", []) or []:
            descriptor = mh.get("DescriptorName")
            if descriptor:
                mesh_terms.append(str(descriptor))

        # Keywords
        keywords: List[str] = []
        for kw_list in article_data.get("KeywordList", []) or []:
            for kw in kw_list:
                keywords.append(str(kw))

        # PubMed URL
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        return {
            "id": pmid,
            "title": title,
            "abstract": abstract,
            "abstract_sections": abstract_sections,  # e.g. {"BACKGROUND": "...", "RESULTS": "..."}
            "journal": journal,
            "year": year,
            "date": year,  # Graph expects 'date' field
            "mesh_terms": mesh_terms,
            "keywords": keywords,
            "authors": authors,
            "url": url,
            "type": "Paper",  # used by graph coloring, etc.
        }

    def fetch_research(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search PubMed and return rich paper metadata for a given topic.

        This is used by:
          - Streamlit graph builder
          - Knowledge graph engine
          - Any future research-side RAG pipeline
        """
        try:
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="date",  # Get most recent first
            )
            search_record = Entrez.read(search_handle)
            ids = search_record.get("IdList", [])

            if not ids:
                return []

            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=",".join(ids),
                rettype="xml",
                retmode="xml",
            )
            fetch_record = Entrez.read(fetch_handle)
            articles = fetch_record.get("PubmedArticle", []) or []

            papers: List[Dict[str, Any]] = []
            for art in articles:
                try:
                    papers.append(self._parse_article(art))
                except Exception as parse_err:
                    print(f"PubMed parse error for one article: {parse_err}")
                    continue

            return papers

        except Exception as e:
            print(f"PubMed Error in fetch_research: {e}")
            return []
