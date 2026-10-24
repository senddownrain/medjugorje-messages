"""Read-only thematic snapshot reconciliation using source anchors, not calendar guesses."""
from email import policy
from email.parser import BytesParser
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlparse
import zipfile

from bs4 import BeautifulSoup
from scripts.audit_source_snapshots import extract_original, read_heading_date, sha256

REFERENCE_COMMENT = "https://github.com/senddownrain/medjugorje-messages/pull/17#issuecomment-6368385769"
SOURCE_MEMBERS = {
    "en/annual": "sources/Annual Medjugorje Messages - list - Medjugorje WebSite.mht",
    "hr/annual": "sources/Godišnje poruke iz Međugorja - list - Medjugorje WebSite.mht",
    "en/special": "sources/Other Medjugorje Messages - list - Medjugorje WebSite.mht",
    "hr/special": "sources/Posebne poruke - list - Medjugorje WebSite.mht",
}
# Receipt hashes in the owner's cited independent check, not inferred message metadata.
SOURCE_SHA256 = {
    "en/annual": "ba64633f63b488a7b71d105f3f43c640341d48b9fc81c405402b4a3ea4193b6c",
    "hr/annual": "4419c0cf70f2d3a032dc4151f667c71813ba42a91b4e5ce20282bc4e5007de8b",
    "en/special": "da96fdf164c5022d4ee5491c0083b953703f539d5d6bf5ff0cb2682acf1ab5be",
    "hr/special": "b74376a82e210b163a5241c8bec8f29e51a111da494d2850457534afdec6517d",
}
SERIES_CANDIDATES = {
    "annual.ivanka": "ivanka_annual", "annual.jakov": "jakov_annual", "annual.mirjana": "mirjana_annual",
    "special.ivan": "ivan_special", "special.marija": "marija_special", "special.mirjana": "mirjana_second_day",
}


def inspect_category_links(raw, origin, group_anchors):
    mime = BytesParser(policy=policy.default).parsebytes(raw)
    part = next(p for p in mime.walk() if p.get_content_type() == "text/html"
                and p.get("Content-Location", "").rstrip("/") == origin.rstrip("/"))
    soup = BeautifulSoup(part.get_payload(decode=True), "html.parser")
    page = urlparse(origin)
    pagination, group_urls, uncovered = set(), set(), set()
    for tag in soup.select("a[href], link[href]"):
        target = urlparse(urljoin(origin, tag["href"]))
        same_category = target.hostname == page.hostname and target.path.rstrip("/") == page.path.rstrip("/")
        numbered_page = target.hostname == page.hostname and re.fullmatch(
            re.escape(page.path.rstrip("/")) + r"/(?:page/)?\d+/?", target.path)
        query = {k.lower() for k in parse_qs(target.query)}
        if "next" in tag.get("rel", []) or numbered_page or (same_category and query.intersection({"page", "start", "offset"})):
            pagination.add(urljoin(origin, tag["href"]))
        group_match = re.fullmatch(re.escape(page.path.rstrip("/")) + r"\.([a-z]+)/?", target.path)
        if target.hostname == page.hostname and group_match:
            group_urls.add(urljoin(origin, tag["href"]))
            if page.path.rstrip("/").split("/")[-1] + "." + group_match[1] not in group_anchors:
                uncovered.add(urljoin(origin, tag["href"]))
    return {"explicit_pagination_links": sorted(pagination), "group_view_urls": sorted(group_urls),
            "group_view_urls_without_inline_group": sorted(uncovered)}


def verify_thematic_zip(path, data_folder):
    path, data_folder = Path(path), Path(data_folder)
    root = Path(__file__).resolve().parents[1]
    artifact = str(path.resolve().relative_to(root)) if path.resolve().is_relative_to(root) else path.name
    index = json.loads((data_folder / "index.json").read_text(encoding="utf-8"))["messages"]
    by_id = {r["id"]: r for r in index}
    report = {"status": "VERIFIED_SOURCE_SNAPSHOT_COVERAGE", "reference_comment": REFERENCE_COMMENT,
              "artifact": artifact, "archive_sha256": sha256(path.read_bytes()), "archive_bytes": path.stat().st_size,
              "source_pages": {}, "entries": [], "violations": [],
              "scope": "Полнота четырёх предоставленных тематических снимков относительно EN/HR /all; не полнота живого сайта."}
    memberships = {}
    with zipfile.ZipFile(path) as archive:
        supplied = json.loads(archive.read("thematic_report.json"))
        for key, member in SOURCE_MEMBERS.items():
            lang, category = key.split("/")
            raw = archive.read(member)
            records, positions, origin = extract_original(raw, lang, category)
            targets = json.loads((data_folder / f"{lang}.json").read_text(encoding="utf-8"))["messages"]
            language_map = {r["id"]: r for r in targets}
            expected = {r["id"] for r in targets if r["type"] == category}
            ids = {r["id"] for r in records}
            groups = {}
            recipient_differences = []
            def violation(reason, **details):
                report["violations"].append({"page": key, "reason": reason, **details})
            for row in records:
                mid = row["id"]
                group = positions[mid]["thematic_group"]
                anchor = group["anchor"]
                groups.setdefault(anchor, {**group, "ids": [], "series_candidate": SERIES_CANDIDATES.get(anchor)})["ids"].append(mid)
                expected_group_path = f"/{lang}/messages/{anchor}"
                if (anchor not in SERIES_CANDIDATES or urlparse(group["url"]).path.rstrip("/") != expected_group_path
                        or urlparse(group["url"]).hostname not in ("www.medjugorje.ws", "medjugorje.ws")):
                    violation("unrecognized_source_group", id=mid, group=group)
                target = language_map.get(mid)
                if target is None:
                    violation("source-missing", id=mid, source_url=row["source_url"])
                else:
                    fields = [f for f in row if f != "source_position" and target.get(f) != row[f]]
                    if fields:
                        violation("thematic_all_record_difference", id=mid, fields=fields)
                root_row = by_id.get(mid)
                if root_row is None or root_row["type"] != category or row["type"] != category or root_row["date"] != row["date"]:
                    violation("thematic_index_date_or_type_mismatch", id=mid)
                if read_heading_date(row["title"], lang) != row["date"]:
                    violation("heading_checkbox_date_mismatch", id=mid)
                if positions[mid]["unclassified_source_blocks"]:
                    violation("unclassified_source_blocks", id=mid, blocks=positions[mid]["unclassified_source_blocks"])
                if root_row and root_row.get("visionary") != anchor.split(".", 1)[1]:
                    recipient_differences.append({"id": mid, "index_visionary": root_row.get("visionary"),
                                                 "source_group_recipient": anchor.split(".", 1)[1]})
                evidence = {"page": key, "content_location": origin, "zip_member": member, "source_sha256": sha256(raw),
                            "heading_position": row["source_position"], **group}
                memberships.setdefault(mid, []).append(evidence)
                report["entries"].append({"page": key, "id": mid, "date": row["date"], "type": row["type"],
                    "source_id": row["source_id"], "source_url": row["source_url"], "title": row["title"],
                    "text_sha256": row["text_sha256"], "segments_count": len(row["segments"]),
                    "source_group": group, "heading_position": row["source_position"]})
            missing, extra = sorted(expected - ids), sorted(ids - expected)
            if missing or extra:
                violation("category_set_difference", absent=missing, unexpected=extra)
            navigation = inspect_category_links(raw, origin, set(groups))
            if navigation["explicit_pagination_links"] or navigation["group_view_urls_without_inline_group"]:
                violation("unresolved_source_navigation", **navigation)
            group_counts = {a.split(".", 1)[1]: len(g["ids"]) for a, g in groups.items()}
            claim = supplied["source_pages"][key]
            reference_matches = (sha256(raw) == SOURCE_SHA256[key] == claim["mhtml_sha256"]
                and len(raw) == claim["mhtml_size"] and len(records) == claim["message_count"]
                and group_counts == claim["groups"] and len(expected) == claim["json_expected_count"])
            if not reference_matches:
                violation("independent_reference_does_not_match")
            report["source_pages"][key] = {"zip_member": member, "mhtml_sha256": sha256(raw), "mhtml_size": len(raw),
                "content_location": origin, "message_count": len(records), "json_expected_count": len(expected),
                "source_ids": sorted(ids), "groups": groups, "group_counts": group_counts,
                "absent_from_category": missing, "unexpected_from_category": extra,
                "source_group_vs_index_recipient_differences": recipient_differences,
                "reference_comment_and_supplied_report_match": reference_matches, **navigation}
    cross = {}
    for category in ("annual", "special"):
        en = set(report["source_pages"][f"en/{category}"]["source_ids"])
        hr = set(report["source_pages"][f"hr/{category}"]["source_ids"])
        cross[category] = {"common": len(en & hr), "en_only": sorted(en - hr), "hr_only": sorted(hr - en)}
    special_en_groups = report["source_pages"]["en/special"]["groups"]
    cross["special"]["en_only_by_group"] = {a: sorted(set(g["ids"]) & set(cross["special"]["en_only"])) for a, g in special_en_groups.items()}
    report["cross_language"] = cross
    thematic_ids = set(memberships)
    outside = [r for r in index if r["type"] in ("annual", "special") and r["id"] not in thematic_ids]
    report["union_ids_outside_both_languages"] = [{"id": r["id"], "date": r["date"], "type": r["type"],
        "reason": "not_in_provided_EN_HR_categories_not_a_proven_import_loss",
        "languages_present": [l for l, m in r["translations"].items() if m["present"]],
        "original_sources": {l: {f: m[f] for f in ("source_id", "source_url", "text_sha256")} for l, m in r["translations"].items() if m["present"]}}
        for r in outside]
    report["total_thematic_entries"] = len(report["entries"])
    report["distinct_thematic_ids"] = len(thematic_ids)
    report["violation_count"] = len(report["violations"])
    if report["violations"]:
        report["status"] = "THEMATIC_SOURCE_REVIEW_REQUIRED"
    return report, memberships


def attach_thematic_evidence(audit, path, data_folder):
    thematic, memberships = verify_thematic_zip(path, data_folder)
    audit["thematic"] = thematic
    valid_all = (audit["sources"]["status"] == "SEVEN_ALL_SNAPSHOTS_MATCH_JSON_PENDING_CATEGORY_REVIEW"
                 and audit["sources"]["proposals_confirmed_in_original_all"] == len(audit["proposals"]))
    if not valid_all or thematic["violations"] or audit["violations"]:
        audit["summary"]["status"] = "SOURCE_REVIEW_REQUIRED"
        return audit
    audit["summary"].update(status="VERIFIED_SOURCE_SNAPSHOT_COVERAGE", editorial_status="PENDING_EDITORIAL_ATTRIBUTION",
                            thematic_entries_compared=thematic["total_thematic_entries"])
    audit["sources"].update(status="VERIFIED_SOURCE_SNAPSHOT_COVERAGE", all_snapshot_status="VERIFIED_SEVEN_ALL_SNAPSHOTS",
                           editorial_status="PENDING_EDITORIAL_ATTRIBUTION", missing_required=[],
                           thematic_report="thematic.json", thematic_archive_sha256=thematic["archive_sha256"])
    audit["summary"]["source_snapshot_status"] = audit["sources"]["status"]
    for proposal in audit["proposals"]:
        proposal["review_status"] = "PENDING_EDITORIAL_ATTRIBUTION"
        proposal["source_group_evidence"] = memberships.get(proposal["id"], [])
    for row in audit["inventory"]:
        if row["id"] in memberships:
            row["source_group_evidence"] = memberships[row["id"]]
            row["series_review_status"] = "source_group_verified_pending_editorial_model"
        elif row["type"] in ("annual", "special"):
            row["series_review_status"] = "not_in_provided_EN_HR_thematic_snapshots"
    return audit
