from collections import Counter

import pandas as pd
import plotly.express as px

from birdlab.config import UNKNOWN


def summarize(records: list[dict]) -> dict:
    scores = [r["confidence"] for r in records]
    species = {(r["scientific_name"] or r["model_id"] + ":" + r["predicted_species"]) for r in records if r["predicted_species"] != "background"}
    return {"images": sum(r["analysis_type"] == "image" for r in records), "audio": sum(r["analysis_type"] == "audio" for r in records), "unique_species": len(species), "average_confidence": sum(scores) / len(scores) if scores else None, "max_record": max(records, key=lambda r: r["confidence"]) if records else None, "min_record": min(records, key=lambda r: r["confidence"]) if records else None, "species_counts": dict(Counter(r["predicted_species"] for r in records)), "dates": dict(sorted(Counter(r["analysis_date"][:10] for r in records).items()))}


def quality_metrics(evaluations: list[dict]) -> list[dict]:
    groups: dict[tuple, dict] = {}
    latest: dict[tuple, dict] = {}
    for index, row in enumerate(evaluations):
        identity = (row["model_id"], row["model_revision"], row["experiment"], row.get("file_hash") or f"row:{index}")
        latest[identity] = row
    for row in latest.values():
        key = (row["model_id"], row["model_revision"], row["experiment"])
        group = groups.setdefault(key, {"model_id": key[0], "revision": key[1], "experiment": key[2], "count": 0, "correct": 0, "top3_correct": 0})
        group["count"] += 1
        group["correct"] += row["top1_correct"]
        group["top3_correct"] += row["top3_correct"]
    for group in groups.values():
        group["incorrect"] = group["count"] - group["correct"]
        group["top1_accuracy"] = group["correct"] / group["count"]
        group["top3_accuracy"] = group["top3_correct"] / group["count"]
    return list(groups.values())


def filter_gallery(records: list[dict], family: str = "", habitat: str = "", diet: str = "") -> list[dict]:
    return [r for r in records if r["analysis_type"] == "image" and all(not value or ((r.get("bird") or {}).get(key) or UNKNOWN) == value for key, value in (("family", family), ("habitat", habitat), ("diet", diet)))]


def build_charts(records: list[dict]) -> dict:
    if not records:
        return {}
    summary = summarize(records)
    species = pd.DataFrame(list(summary["species_counts"].items()), columns=["Вид / клас", "Кількість"]).sort_values("Кількість", ascending=False)
    dates = pd.DataFrame(list(summary["dates"].items()), columns=["Дата UTC", "Кількість"])
    types = pd.DataFrame([{"Тип": "Фото", "Кількість": summary["images"]}, {"Тип": "Аудіо", "Кількість": summary["audio"]}])
    charts = {"Розподіл видів / класів": px.pie(species, names="Вид / клас", values="Кількість", hole=0.5), "TOP-10 результатів": px.bar(species.head(10), x="Кількість", y="Вид / клас", orientation="h"), "Розподіл confidence": px.histogram(pd.DataFrame({"Confidence, %": [r["confidence"] * 100 for r in records]}), x="Confidence, %", nbins=10), "Аналізи за датами": px.bar(dates, x="Дата UTC", y="Кількість"), "Типи аналізу": px.pie(types, names="Тип", values="Кількість", hole=0.5)}
    for chart in charts.values():
        chart.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10), colorway=["#71D59A", "#3DAE95", "#A4BE80", "#649EA0", "#D3C187"])
    charts["Розподіл confidence"].update_yaxes(title_text="Кількість")
    charts["Аналізи за датами"].update_xaxes(type="category")
    return charts
