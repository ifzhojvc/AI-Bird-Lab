import argparse
import csv
import hashlib
import html
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "AIBirdLab/1.0 (educational local project; source and license preservation)"
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(total=4, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504], respect_retry_after_header=True)))
LAST_REQUEST = 0.0
IMAGE_BIRDS = [
    ("Cardinal", "Northern cardinal", "Cardinalis cardinalis"),
    ("Blue Jay", "Blue jay", "Cyanocitta cristata"),
    ("American Goldfinch", "American goldfinch", "Spinus tristis"),
    ("European Goldfinch", "European goldfinch", "Carduelis carduelis"),
    ("Indigo Bunting", "Indigo bunting", "Passerina cyanea"),
    ("Painted Bunting", "Painted bunting", "Passerina ciris"),
    ("Red winged Blackbird", "Red-winged blackbird", "Agelaius phoeniceus"),
    ("Mallard", "Mallard", "Anas platyrhynchos"),
    ("House Sparrow", "House sparrow", "Passer domesticus"),
    ("Barn Swallow", "Barn swallow", "Hirundo rustica"),
    ("Baltimore Oriole", "Baltimore oriole", "Icterus galbula"),
    ("Cedar Waxwing", "Cedar waxwing", "Bombycilla cedrorum"),
    ("Pileated Woodpecker", "Pileated woodpecker", "Dryocopus pileatus"),
    ("Brown Pelican", "Brown pelican", "Pelecanus occidentalis"),
    ("White breasted Kingfisher", "White-throated kingfisher", "Halcyon smyrnensis"),
]
AUDIO_BIRDS = [
    ("Asian_openbill_stork", "Asian openbill", "Anastomus oscitans"),
    ("Blue-tailed_bee-eater", "Blue-tailed bee-eater", "Merops philippinus"),
    ("Rosy_starling", "Rosy starling", "Pastor roseus"),
    ("Indian_spot-billed_duck", "Indian spot-billed duck", "Anas poecilorhyncha"),
    ("Fulvous_whistling_duck", "Fulvous whistling duck", "Dendrocygna bicolor"),
    ("Spotted_owlet", "Spotted owlet", "Athene brama"),
    ("Northern_pintail", "Northern pintail", "Anas acuta"),
    ("Painted_stork", "Painted stork", "Mycteria leucocephala"),
    ("Northern_shoveler", "Northern shoveler", "Spatula clypeata"),
    ("Little_egret", "Little egret", "Egretta garzetta"),
    ("White-throated_kingfisher", "White-throated kingfisher", "Halcyon smyrnensis"),
    ("Common_kingfisher", "Common kingfisher", "Alcedo atthis"),
    ("Spot-billed_pelican", "Spot-billed pelican", "Pelecanus philippensis"),
    ("Indian_pond_heron", "Indian pond heron", "Ardeola grayii"),
    ("Glossy_ibis", "Glossy ibis", "Plegadis falcinellus"),
    ("Great_egret", "Great egret", "Ardea alba"),
    ("Garganey", "Garganey", "Spatula querquedula"),
    ("Grey_Heron", "Grey heron", "Ardea cinerea"),
    ("Eurasian_spoonbill", "Eurasian spoonbill", "Platalea leucorodia"),
]


def get_json(url: str, params: dict | None = None) -> dict:
    global LAST_REQUEST
    time.sleep(max(0, 1.6 - (time.monotonic() - LAST_REQUEST)))
    LAST_REQUEST = time.monotonic()
    response = SESSION.get(url, params=params, timeout=(10, 40))
    response.raise_for_status()
    return response.json()


def wiki_page(title: str, language: str = "en") -> dict:
    data = get_json(f"https://{language}.wikipedia.org/w/api.php", {"action": "query", "format": "json", "titles": title, "prop": "pageimages|pageprops|extracts", "piprop": "original", "exintro": 1, "explaintext": 1, "exchars": 1600, "redirects": 1})
    return next(iter(data["query"]["pages"].values()))


def plain(value: str) -> str:
    return html.unescape(re.sub("<[^>]+>", "", value)).strip()


def bird_data(label: str, title: str, expected: str, kind: str) -> tuple[dict, dict]:
    page = wiki_page(title)
    qid = page["pageprops"]["wikibase_item"]
    entity = get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")["entities"][qid]
    scientific = {claim["mainsnak"].get("datavalue", {}).get("value") for claim in entity.get("claims", {}).get("P225", []) if claim["mainsnak"].get("snaktype") == "value"}
    if expected not in scientific:
        raise ValueError(f"Наукову назву не підтверджено: {title}: {scientific} != {expected}")
    bird = {"scientific_name": expected, "wikidata_id": qid, "english_name": title, "ukrainian_name": entity.get("labels", {}).get("uk", {}).get("value", ""), "image_labels": [], "audio_labels": [], "family": "", "habitat": "", "range": "", "diet": "", "size": "", "facts": "", "conservation_status": "", "sources": [f"https://en.wikipedia.org/wiki/{quote(page['title'].replace(' ', '_'))}", f"https://www.wikidata.org/wiki/{qid}"], "source_excerpt_en": page.get("extract", "")}
    bird[f"{kind}_labels"] = [label]
    try:
        match = get_json("https://api.gbif.org/v1/species/match", {"name": expected, "strict": "true", "kingdom": "Animalia"})
        if match.get("canonicalName", "").casefold() == expected.casefold() and match.get("matchType") == "EXACT" and match.get("rank") == "SPECIES":
            bird["family"] = match.get("family", "")
            bird["gbif_id"] = match.get("acceptedUsageKey", match.get("usageKey"))
            bird["sources"].append(f"https://www.gbif.org/species/{bird['gbif_id']}")
    except (requests.RequestException, ValueError):
        pass
    uk_title = entity.get("sitelinks", {}).get("ukwiki", {}).get("title")
    if bird["ukrainian_name"] == expected:
        bird["ukrainian_name"] = uk_title or ""
    if uk_title:
        try:
            uk_page = wiki_page(uk_title, "uk")
            bird["facts"] = uk_page.get("extract", "")
            bird["sources"].append(f"https://uk.wikipedia.org/wiki/{quote(uk_title.replace(' ', '_'))}")
        except (requests.RequestException, ValueError, KeyError):
            pass
    return bird, page


def download_image(page: dict, stem: str) -> dict:
    image_name = page.get("pageprops", {}).get("page_image_free")
    if not image_name:
        image_name = unquote(urlparse(page["original"]["source"]).path.rsplit("/", 1)[-1])
    data = get_json("https://commons.wikimedia.org/w/api.php", {"action": "query", "format": "json", "titles": "File:" + image_name, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1000})
    info = next(iter(data["query"]["pages"].values()))["imageinfo"][0]
    meta = info["extmetadata"]
    license_name = plain(meta.get("LicenseShortName", {}).get("value", ""))
    if not any(term in license_name.lower() for term in ("cc by", "cc0", "public domain", "pdm")):
        raise ValueError(f"Непідтверджена відкрита ліцензія: {license_name}")
    url = info.get("thumburl", info["url"])
    response = SESSION.get(url, timeout=(10, 90))
    response.raise_for_status()
    content = response.content
    with Image.open(io.BytesIO(content)) as image:
        extension = ".jpg" if image.format == "JPEG" else ".png" if image.format == "PNG" else None
        if not extension:
            raise ValueError("Непідтримуваний формат тестового фото")
        image.verify()
    filename = stem + extension
    (ROOT / "sample_images" / filename).write_bytes(content)
    return {"file_name": filename, "source_url": info["descriptionurl"], "download_url": url, "license": license_name, "license_url": meta.get("LicenseUrl", {}).get("value", ""), "author": plain(meta.get("Artist", {}).get("value", "")), "sha256": hashlib.sha256(content).hexdigest(), "label_verified": "true"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Завантаження відкритих фото та перевіреної таксономії")
    parser.add_argument("--skip-audio-catalog", action="store_true")
    args = parser.parse_args()
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "sample_images").mkdir(exist_ok=True)
    catalog_path = ROOT / "data" / "birds.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    manifest_path = ROOT / "sample_manifest.csv"
    rows = list(csv.DictReader(manifest_path.open(encoding="utf-8-sig", newline=""))) if manifest_path.exists() else []
    by_label = {row["model_label"]: row for row in rows}
    failures = []
    for index, (label, title, expected) in enumerate(IMAGE_BIRDS):
        try:
            existing = by_label.get(label)
            if existing and expected in catalog and (ROOT / "sample_images" / existing["file_name"]).exists():
                print(index + 1, label, "вже завантажено", flush=True)
                continue
            bird, page = bird_data(label, title, expected, "image")
            previous = catalog.get(expected, {})
            bird["audio_labels"] = previous.get("audio_labels", [])
            catalog[expected] = bird
            row = by_label.get(label)
            if not row or not (ROOT / "sample_images" / row["file_name"]).exists():
                row = download_image(page, f"{index + 1:02d}_{expected.replace(' ', '_')}")
                row.update({"original_species": title, "model_label": label, "scientific_name": expected, "wikidata_id": bird["wikidata_id"], "label_source": bird["sources"][0]})
                by_label[label] = row
            print(index + 1, label, row["license"], row["file_name"], flush=True)
        except Exception as exc:
            failures.append({"label": label, "error": str(exc)})
            print("ПОМИЛКА", label, str(exc), flush=True)
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        if by_label:
            with manifest_path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(next(iter(by_label.values())).keys()))
                writer.writeheader()
                writer.writerows(by_label.values())
        time.sleep(0.1)
    if not args.skip_audio_catalog:
        for label, title, expected in AUDIO_BIRDS:
            try:
                if expected in catalog:
                    catalog[expected]["audio_labels"] = [label]
                else:
                    bird, _ = bird_data(label, title, expected, "audio")
                    catalog[expected] = bird
                print("Таксономія аудіо:", label, expected, flush=True)
            except Exception as exc:
                failures.append({"label": label, "error": str(exc)})
                print("ПОМИЛКА", label, str(exc), flush=True)
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    notes_path = ROOT / "data" / "field_notes.json"
    if notes_path.exists():
        for scientific, notes in json.loads(notes_path.read_text(encoding="utf-8")).items():
            if scientific in catalog:
                catalog[scientific].update(notes)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "verification" / "sample_download.json").write_text(json.dumps({"photos": len(by_label), "catalog_species": len(catalog), "failures": failures, "unresolved_audio_labels": ["White_Ibis", "Golden_oriole"], "reason": "Неоднозначні загальні назви; наукові назви не підтверджені автором моделі."}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
