from typing import List, Dict, Optional, Any
from collections import Counter
import pandas as pd
import requests
import re
import pandas as pd
from typing import List
import time
import random


# Configuration
YEARS_OF_INTEREST = set(range(2017, 2024)) 

def find_best_author_match(author_name: str) -> Optional[Dict[str, Any]]:
    base_url = "https://api.openalex.org"
    r = safe_request(f"{base_url}/authors?filter=display_name.search:{author_name}")
    if r.status_code != 200:
        return None

    results = r.json().get("results", [])
    if not results:
        return None
    target = author_name.lower().strip()

    for res in results:
        if res["display_name"].lower().strip() == target:
            return res

    for res in results:
        alt_names = [n.lower().strip() for n in res.get("alternate_names", []) if isinstance(n, str)]
        if target in alt_names:
            return res

    return results[0]

    
# for people didnt found we find using frist and last name manually
def fallback_author_search(author_name: str) -> Optional[Dict[str, Any]]:
    first, *rest = author_name.split()
    last = rest[-1] if rest else ""
    if not last:
        return None
    query = f"{first} {last}" if first else last
    return find_best_author_match(query)


# Return clean list of author names from a string
def parse_authors(author_string: str) -> List[str]:
    if not author_string:
        return []
    parts = re.split(r"\s+and\s+|,\s*", author_string)
    names = [re.sub(r"\s+", " ", p).strip(" .") for p in parts]
    return [n for n in names if n and len(n) > 1]

#add delay
def safe_request(url, max_retries=5):
    for _ in range(max_retries):
        r = requests.get(url)
        if r.status_code == 200:
            return r
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", random.uniform(30, 60)))
            time.sleep(wait)
            continue
        if 500 <= r.status_code < 600:
            wait = random.uniform(5, 10)
            time.sleep(wait)
            continue
        break
    return r


# OpenAlex data collection

def collect_papers_one_row_per_paper(author_name: str) -> List[Dict[str, Any]]:
    base_url = "https://api.openalex.org"
    rows = []

    # Find author by name
    r = safe_request(f"{base_url}/authors?search={author_name}")
    if r.status_code != 200:
        print(f"Error searching for {author_name}: {r.status_code}")
        return rows

    data = r.json()
    if not data.get("results"):
        print(f"No author found for {author_name}")
        return rows

    author_info = find_best_author_match(author_name)
    if not author_info:
        # try fallback
        author_info = fallback_author_search(author_name)
        if not author_info:
            print(f"No author found for {author_name}")
            return rows

    author_id = author_info["id"]
    display_name = author_info["display_name"]
    print(f"Found OpenAlex author for {author_name}: {display_name}")

    # get all works
    works_url = f"{base_url}/works?filter=author.id:{author_id}&per-page=200"
    #this only gives journal article
    cursor = "*"
    all_works = []

    while True:
        url = f"{works_url}&cursor={cursor}"
        r = safe_request(url)
        if r.status_code != 200:
            print(f"Error fetching works for {author_name}: {r.status_code}")
            break

        data = r.json()
        works = data.get("results", [])
        meta = data.get("meta", {})

        if not works:
            break

        all_works.extend(works)
        print(f"Fetched {len(all_works)} / {meta.get('count', '?')} works so far for {display_name}")

        # check if there’s a next page
        cursor = meta.get("next_cursor")
        if not cursor:
            print(f"Completed fetching all {len(all_works)} works for {display_name}")
            break
        
        time.sleep(random.uniform(2.5, 3.5))

        
        
    unique_works = {}
    for w in all_works:
        doi = w.get("doi") or w.get("id")
        if doi not in unique_works:
            unique_works[doi] = w
    all_works = list(unique_works.values())
        
    #get career stage estimate
    pub_years = [w.get("publication_year") for w in all_works if w.get("publication_year")]
    if not pub_years:
        #print(f"No publication pub_years found for {display_name}")
        return []

    first_year = min(pub_years)
    last_year = max(pub_years)
    career_length = last_year - first_year + 1

    if career_length <= 5:
        career_stage = "Early-career"
    elif career_length <= 15:
        career_stage = "Mid-career"
    else:
        career_stage = "Senior"
    print(f"{display_name}: first year {first_year}, last year {last_year}, stage {career_stage}")

        
    for w in all_works:
        year = w.get("publication_year")
        if year not in YEARS_OF_INTEREST:
            continue

        title = w.get("title")
        if title and re.search(r"(list of contributors|editorial board|erratum|acknowledgement|treatment)", title, re.IGNORECASE):
            continue
        cited_by_count = w.get("cited_by_count")
        authorships = w.get("authorships", [])

        # Extract all authors
        authors = [a["author"]["display_name"] for a in authorships if a.get("author")]
        total_authors_listed = len(authors)

        # Coauthors 
        coauthors = []
        for a in authors:
            if a is not None and (a.lower() != display_name.lower()):
                coauthors += [a]

        coauthor_count = len(coauthors)

        # Count coauthors by country 
        countries = []
        for a in authorships:
            institutions = a.get("institutions", [])
            country = institutions[0].get("country_code") if institutions else None
            if country:
                countries.append(country)
        coauthor_countries_counts = dict(Counter(countries))

        rows.append({
            "author_name": display_name,
            "career_stage": career_stage,
            "paper_title": title,
            "paper_year": year,
            "times_cited": cited_by_count,
            "total_authors_listed": total_authors_listed,
            "coauthors": ", ".join(coauthors),
            "coauthor_count": coauthor_count,
            "coauthor_countries_counts": coauthor_countries_counts
        })

    return rows

#remove all titles
def clean_author_name(name: str) -> str:
    if not isinstance(name, str):
        return ""

    name = re.sub(
        r",?\s*\b("
        r"MD|PhD|RN|MS|MPH|FACS|MBA|DO|PA|NP|BSN|MSN|DDS|DMD|Dr|CCNS|CNS|FCCM|"
        r"FAAN|CRNA|CNM|DNP|ANP|FNP|PCCN|CEN|CPN|BCPS|CCR[MN]-?K?|FASA|FCCP|CNSC|"
        r"CPPS|CHCQM|MBBS|BA|BS|MA|MS|MPH|BCPS|PharmD"
        r")\.?\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    # Remove leftover commas, spaces
    name = re.sub(r"[, ]{2,}", " ", name)
    return name.strip(" ,")



def collect_for_authors_one_row(author_names: List[str]) -> pd.DataFrame:
    all_rows = []
    for raw_name in author_names:
        name = clean_author_name(raw_name)
        all_rows.extend(collect_papers_one_row_per_paper(name))
    cols = [
        "author_name", "career_stage", "paper_title", "paper_year", "times_cited",
        "total_authors_listed", "coauthors", "coauthor_count", "coauthor_countries_counts"
    ]
    return pd.DataFrame(all_rows, columns=cols)

#def collect_for_authors_from_csv(csv_path: str, author_column: str) -> pd.DataFrame:
 #   df_authors = pd.read_csv(csv_path)
    # drop NA and convert to list
  #  author_names = df_authors[author_column].dropna().tolist()
    # use your existing function
   # return collect_for_authors_one_row(author_names)
   


#randonmly select 88 people from the full participants list
def collect_random_sample_from_csv(csv_path: str, author_column: str, sample_size: int = 88) -> pd.DataFrame:
    df_authors = pd.read_csv(csv_path)
    author_names = df_authors[author_column].dropna().unique().tolist()

    if len(author_names) < sample_size:
        print(f"Only {len(author_names)} authors available — taking all.")
        sample_size = len(author_names)

    sampled_authors = random.sample(author_names, sample_size)
    print(f"Selected {len(sampled_authors)} authors at random.")
    return collect_for_authors_one_row(sampled_authors)

#df = collect_random_sample_from_csv("Full Participant List.csv", "full_name", sample_size=88)
#df.to_csv("openalex_sample_authors.csv", index=False)
#print("Saved results to openalex_sample_88_authors.csv")


def collect_from_csv(csv_path: str, author_column: str) -> pd.DataFrame:
    df_authors = pd.read_csv(csv_path)
    author_names = df_authors[author_column].dropna().unique().tolist()
    return collect_for_authors_one_row(author_names)

#df = collect_from_csv("combined.csv", "author_name")
#df.to_csv("combined_new.csv", index=False)
#print("Saved results to combined_new.csv")

df = collect_from_csv("missing.csv", "Full Name")
df.to_csv("missing.csv", index=False)
print("Saved results to newmissing.csv")