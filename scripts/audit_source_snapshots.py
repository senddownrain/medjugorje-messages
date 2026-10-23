"""Independent, offline verification of the seven original saved /all pages.

This reader uses complete div.messages containers and walks text nodes directly.
It does not call the importer's MIME selection, parse_page or block_text helpers.
It verifies a saved snapshot, not completeness of the live site or its series.
"""
from collections import Counter, defaultdict
from datetime import date
from email import policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import zipfile

from bs4 import BeautifulSoup, Comment, NavigableString

LANGUAGES = ("ru", "be", "uk", "hr", "en", "sk", "lv")
MONTHS = {
    "ru": "январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь",
    "be": "студзень люты сакавік красавік май чэрвень ліпень жнівень верасень кастрычнік лістапад снежань",
    "uk": "січень лютий березень квітень травень червень липень серпень вересень жовтень листопад грудень",
    "hr": "siječanj veljača ožujak travanj svibanj lipanj srpanj kolovoz rujan listopad studeni prosinac",
    "en": "january february march april may june july august september october november december",
    "sk": "január február marec apríl máj jún júl august september október november december",
    "lv": "janvāris februāris marts aprīlis maijs jūnijs jūlijs augusts septembris oktobris novembris decembris",
}


def read_heading_date(title, language):
    """Check literal dates in known source heading formats, never infer a date."""
    months = {name: n for n, name in enumerate(MONTHS[language].split(), 1)}
    month = "(?P<month>" + "|".join(re.escape(name) for name in months) + ")"
    if language == "en":
        pattern = month + r"\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\b"
    elif language == "lv":
        pattern = r"(?P<year>\d{4})\.g\.\s*(?P<day>\d{1,2})\.\s*" + month + r"\b"
    else:
        pattern = r"(?P<day>\d{1,2})\.?\s+" + month + r",?\s+(?P<year>\d{4})\b"
    match = re.search(pattern, title, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return date(int(match["year"]), months[match["month"].lower()], int(match["day"])).isoformat()
    except ValueError:
        return None


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def source_text(node):
    """Render source characters, omitting only quote markers and non-content tags."""
    def walk(item):
        if isinstance(item, Comment):
            return ""
        if isinstance(item, NavigableString):
            return str(item)
        if item.name in ("script", "style", "noscript"):
            return ""
        if item.name == "span" and {"bq", "eq"}.intersection(item.get("class", [])):
            return ""
        if item.name == "br":
            return "\n"
        return "".join(walk(child) for child in item.children)
    value = walk(node).replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = "\n".join(line.strip() for line in value.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def extract_original(raw, language, category="all"):
    """Return records and exact MIME/DOM provenance, including thematic anchors."""
    if category not in ("all", "annual", "special"):
        raise ValueError("Unsupported source category")
    mime = BytesParser(policy=policy.default).parsebytes(raw)
    expected = f"https://www.medjugorje.ws/{language}/messages/{category}"
    parts = [p for p in mime.walk() if not p.is_multipart()
             and p.get_content_type() == "text/html"
             and p.get("Content-Location", "").rstrip("/") == expected]
    if len(parts) != 1:
        raise ValueError("Expected exactly one original HTML part at the requested location")
    part = parts[0]
    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8")
    soup = BeautifulSoup(html, "html.parser")
    wrappers = soup.select("div.messages")
    if not wrappers or len(wrappers) != len(soup.select("h2.poselstvi-datum")):
        raise ValueError("Message containers and headings do not agree")
    records, provenance = [], {}
    section = None
    group, seen_groups = None, set()
    for position, wrapper in enumerate(wrappers):
        headings = wrapper.select("h2.poselstvi-datum")
        dates = wrapper.select('.mm-head input[type="checkbox"]')
        if len(headings) != 1 or len(dates) != 1:
            raise ValueError("Expected one dated heading in each message container")
        anchors = [a["name"] for a in wrapper.select("a[name]") if a["name"].startswith(category + ".")]
        if category != "all":
            if anchors:
                labels = wrapper.select("div.nadpis h2 a[href]")
                if len(anchors) != 1 or len(labels) != 1 or anchors[0] in seen_groups:
                    raise ValueError("Ambiguous or repeated thematic group anchor")
                seen_groups.add(anchors[0])
                group = {"anchor": anchors[0], "label": labels[0].get_text(" ", strip=True), "url": labels[0]["href"]}
            if group is None:
                raise ValueError("Thematic message has no preceding source group anchor")
        for year_link in wrapper.select("h2 a.nadpis[href]"):
            if re.fullmatch(rf"/{language}/messages/\d{{4}}/?", urlparse(year_link["href"]).path):
                section = {"title": year_link.get_text(" ", strip=True), "url": year_link["href"]}
        heading = headings[0]
        link = heading.select_one("a[href]")
        if link is None:
            raise ValueError("Missing original message link")
        parsed_url = urlparse(link["href"])
        match = re.fullmatch(rf"/{language}/messages/(\d{{6}}[mwsa])/?", parsed_url.path)
        if parsed_url.hostname not in ("www.medjugorje.ws", "medjugorje.ws") or not match:
            raise ValueError("Invalid original message URL")
        day = dates[0]["value"].split("_", 1)[0]
        date.fromisoformat(day)
        slug = match[1]
        key = date.fromisoformat(day).strftime("%y%m%d") + slug[-1]
        segments, navigation, unclassified = [], [], []
        reflection_label = {"en": "Reflection of message", "hr": "Razmišljanje iz poruke", "sk": "Komentár k posolstvu"}.get(language)
        for child in wrapper.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                if str(child).strip():
                    unclassified.append({"tag": "#text", "text_sha256": sha256(str(child).encode())})
                continue
            classes = child.get("class", [])
            if "poselstvi-mary" in classes or "poselstvi" in classes:
                value = source_text(child)
                if value:
                    segments.append({"kind": "message" if "poselstvi-mary" in classes else "context", "text": value})
            elif ({"mm-head", "mmm-footer"}.intersection(classes)
                  or (category != "all" and anchors and "nadpis" in classes)
                  or child.name in ("h1", "h2", "h3", "h4", "h5", "h6")):
                continue
            elif source_text(child):
                links = child.find_all("a", href=True)
                label = child.get_text(" ", strip=True)
                if child.name == "p" and label == reflection_label and len(links) == 1 and links[0]["href"] == link["href"]:
                    navigation.append({"label": label, "url": links[0]["href"]})
                else:
                    unclassified.append({"tag": child.name, "classes": classes,
                                         "text_sha256": sha256(source_text(child).encode()), "excerpt": source_text(child)[:200]})
        text = "\n\n".join(s["text"] for s in segments if s["kind"] == "message")
        if key in provenance:
            raise ValueError("Duplicate original canonical ID; manual review required")
        records.append({"id": key, "date": day, "source_id": slug,
                        "type": {"m": "monthly", "w": "weekly", "s": "special", "a": "annual"}[slug[-1]],
                        "title": heading.get_text(" ", strip=True), "source_url": link["href"],
                        "text": text, "segments": segments, "text_sha256": sha256(text.encode()),
                        "source_position": position})
        provenance[key] = {"heading_position": position, "heading_selector": "div.messages h2.poselstvi-datum",
                           "source_year_section": section, "non_message_navigation": navigation,
                           "unclassified_source_blocks": unclassified}
        if category != "all":
            provenance[key]["thematic_group"] = group
    return records, provenance, part["Content-Location"]


def verify_source_zip(path, data_folder):
    path, data_folder = Path(path), Path(data_folder)
    project_root = Path(__file__).resolve().parents[1]
    artifact = str(path.resolve().relative_to(project_root)) if path.resolve().is_relative_to(project_root) else path.name
    report = {"status": "SEVEN_ALL_SNAPSHOTS_MATCH_JSON_PENDING_CATEGORY_REVIEW",
              "artifact": artifact, "archive_sha256": sha256(path.read_bytes()), "archive_bytes": path.stat().st_size,
              "sources": [], "missing_required": ["en/annual", "en/special", "hr/annual", "hr/special"],
              "scope": "Сверка семи сохранённых /all, без утверждения полноты сайта или тематических серий."}
    originals = {}
    with zipfile.ZipFile(path) as archive:
        supplied = json.loads(archive.read("audit/source_manifest.json"))
        for lang in LANGUAGES:
            member = f"original_sources/{lang}_all.mht"
            raw = archive.read(member)
            extracted, positions, location = extract_original(raw, lang)
            targets = json.loads((data_folder / f"{lang}.json").read_text(encoding="utf-8"))["messages"]
            by_id = {r["id"]: r for r in targets}
            source_ids = {r["id"] for r in extracted}
            issues, urls = [], defaultdict(list)
            heading_date_issues = []
            for source in extracted:
                key = source["id"]
                heading_date = read_heading_date(source["title"], lang)
                if heading_date != source["date"]:
                    heading_date_issues.append({"id": key, "title": source["title"], "checkbox_date": source["date"],
                        "heading_date": heading_date, "reason": "heading_date_not_parsed" if heading_date is None else "heading_checkbox_date_mismatch"})
                urls[source["source_url"]].append(key)
                current = by_id.get(key)
                if current is None:
                    issues.append({"reason": "source-missing", "id": key, "source_url": source["source_url"]})
                else:
                    fields = [f for f in source if source[f] != current.get(f)]
                    if fields:
                        issues.append({"reason": "saved_source_record_difference", "id": key, "fields": fields})
                originals[lang, key] = {"record": source, "snapshot": {
                    "artifact": artifact, "archive_sha256": report["archive_sha256"], "zip_member": member,
                    "source_sha256": sha256(raw), "content_location": location, **positions[key]}}
            previous_claim = supplied[lang]
            claim_matches = (sha256(raw) == previous_claim["source_file_sha256"]
                             and len(raw) == previous_claim["bytes"]
                             and len(extracted) == previous_claim["extracted_records"])
            report["sources"].append({"language": lang, "category": "all", "zip_member": member,
                "source_sha256": sha256(raw), "source_bytes": len(raw), "content_location": location,
                "status": "COMPARED_INDEPENDENTLY", "source_records": len(extracted), "json_records": len(targets),
                "source_ids": sorted(source_ids), "issues": issues,
                "heading_dates_checked": len(extracted), "heading_date_issues": heading_date_issues,
                "non_message_navigation_count": sum(len(p["non_message_navigation"]) for p in positions.values()),
                "unclassified_source_blocks": [{"id": key, **block} for key, p in positions.items() for block in p["unclassified_source_blocks"]],
                "json_ids_not_in_saved_source": sorted(set(by_id) - source_ids),
                "source_type_counts": dict(sorted(Counter(r["type"] for r in extracted).items())),
                "first_date": min(r["date"] for r in extracted), "last_date": max(r["date"] for r in extracted),
                "source_without_message_text_ids": sorted(r["id"] for r in extracted if not r["text"]),
                "duplicate_source_urls": [{"source_url": url, "ids": ids} for url, ids in urls.items() if len(ids) > 1],
                "source_url_date_mismatches": [{"id": r["id"], "source_id": r["source_id"], "date": r["date"]}
                    for r in extracted if r["id"] != r["source_id"]],
                "supplied_manifest_sha_and_size_and_count_match": claim_matches})
    report["source_records_compared"] = sum(s["source_records"] for s in report["sources"])
    report["heading_date_issue_count"] = sum(len(s["heading_date_issues"]) for s in report["sources"])
    report["non_message_navigation_count"] = sum(s["non_message_navigation_count"] for s in report["sources"])
    report["unclassified_source_block_count"] = sum(len(s["unclassified_source_blocks"]) for s in report["sources"])
    report["source_missing_count"] = sum(i["reason"] == "source-missing" for s in report["sources"] for i in s["issues"])
    report["record_difference_count"] = sum(i["reason"] == "saved_source_record_difference" for s in report["sources"] for i in s["issues"])
    report["json_records_absent_from_saved_sources"] = sum(len(s["json_ids_not_in_saved_source"]) for s in report["sources"])
    if any(s["issues"] or s["json_ids_not_in_saved_source"] or not s["supplied_manifest_sha_and_size_and_count_match"] for s in report["sources"]):
        report["status"] = "SAVED_SOURCE_DIFFERENCES_REQUIRE_REVIEW"
    elif report["unclassified_source_block_count"]:
        report["status"] = "SOURCE_BLOCKS_REQUIRE_REVIEW"
    return report, originals


def attach_source_evidence(audit, path, data_folder):
    source_report, originals = verify_source_zip(path, data_folder)
    audit["sources"] = source_report
    for gap in audit["translation_not_present"]:
        gap["saved_all_snapshot_present"] = (gap["language"], gap["id"]) in originals
        gap["meaning"] = ("Нет записи в JSON, но она есть в предоставленном /all; возможный пропуск импорта."
                          if gap["saved_all_snapshot_present"] else
                          "Нет записи в JSON и в предоставленном /all; наличие в других источниках не установлено.")
    confirmed = 0
    for proposal in audit["proposals"]:
        matches = []
        for evidence in proposal["evidence"]:
            original = originals.get((evidence["language"], proposal["id"]))
            if original is None:
                matches.append(False)
                continue
            row = original["record"]
            values = [row["title"]] if evidence["field"] == "title" else [
                s["text"] for s in row["segments"] if s["kind"] == evidence["field"]]
            matched = (evidence["quote"] in values and evidence["source_url"] == row["source_url"]
                       and proposal["date"] == row["date"])
            matches.append(matched)
            if matched:
                evidence["original_snapshot"] = {**original["snapshot"], "quote_sha256": sha256(evidence["quote"].encode())}
        if matches and all(matches):
            confirmed += 1
            proposal["confidence"] = "explicit_saved_source_evidence"
            proposal["review_status"] = "original_all_snapshot_confirmed_pending_category_and_editorial_review"
    source_report["proposals_confirmed_in_original_all"] = confirmed
    audit["summary"]["source_snapshot_status"] = source_report["status"]
    audit["summary"]["source_records_compared"] = source_report["source_records_compared"]
    return audit
