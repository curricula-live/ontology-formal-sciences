"""Audit pinned documents and report newer GitHub revisions without altering releases."""
import json
import os
from urllib.request import Request,urlopen
from pipeline.common import ROOT, registry, write
from pipeline.cli import audit


def main():
    report = {}
    for id, source in registry().items():
        if not source.get("sha256"):
            report[id] = {"status":source["status"], "reason":source.get("blocker")}
            continue
        entry = report[id] = {}
        try:
            entry.update(audit(source))
            entry["status"] = "verified"
            url = source["url"]
            if "raw.githubusercontent.com/" in url or "codeload.github.com/" in url:
                repo = "/".join(url.split("/")[3:5])
                headers = {"Accept":"application/vnd.github+json"}
                if os.environ.get("GITHUB_TOKEN"):
                    headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
                with urlopen(Request("https://api.github.com/repos/"+repo+"/commits/HEAD",headers=headers),timeout=30) as r:
                    entry["latest_repository_commit"]=json.load(r)["sha"]
                entry["revision_available"] = entry["latest_repository_commit"] != source["revision"]
        except Exception as exc:
            entry.update(status="needs-review",reason=str(exc))
    write(ROOT/".cache/upstream-audit.json",report)
    return int(any(r["status"]=="needs-review" for r in report.values()))


if __name__=="__main__":
    raise SystemExit(main())
