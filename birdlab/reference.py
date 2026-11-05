from copy import deepcopy

import requests
import streamlit as st

from birdlab.taxonomy import resolve_label


@st.cache_data(ttl=86400, show_spinner=False, max_entries=256)
def bird_reference(label: str, kind: str, online: bool = False) -> dict:
    local = resolve_label(label, kind)
    if not local:
        return {"reference_status": "Немає перевіреного зіставлення цього класу з науковою назвою.", "sources": []}
    bird = deepcopy(local)
    bird["reference_status"] = "Локальні перевірені джерела"
    if online:
        try:
            response = requests.get("https://api.gbif.org/v1/species/match", params={"name": bird["scientific_name"], "strict": "true", "kingdom": "Animalia"}, headers={"User-Agent": "AIBirdLab/1.0"}, timeout=(3, 7))
            response.raise_for_status()
            match = response.json()
            if match.get("matchType") == "EXACT" and match.get("canonicalName", "").casefold() == bird["scientific_name"].casefold() and match.get("rank") == "SPECIES":
                bird["family"] = match.get("family") or bird.get("family", "")
                bird["reference_status"] = "Локальний довідник; таксономію перевірено через GBIF"
            else:
                bird["reference_status"] = "GBIF не підтвердив точний вид; використано локальні джерела"
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            bird["reference_status"] = "Зовнішній API недоступний; використано локальні джерела"
    return bird
