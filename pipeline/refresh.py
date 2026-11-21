"""Prepare one source revision for review in a disposable checkout."""
import argparse
import gzip
import json
import os
import shutil
import tempfile
from pathlib import Path
from urllib.request import Request,urlopen
from pipeline.common import ROOT,read,write,checksum,registry
from pipeline.parse import ingest
from pipeline.curate import authored
from pipeline.align import candidates
from pipeline.publish import build


def latest_url(source):
    url=source["url"]
    if source["id"]=="qudt":
        with urlopen("https://api.github.com/repos/qudt/qudt-public-repo/releases/latest",timeout=30) as response:
            release=json.load(response)
        assets=[a for a in release["assets"] if a["name"].startswith("qudt-public-repo-") and a["name"].endswith(".zip")]
        if len(assets)!=1:
            raise ValueError("Ambiguous QUDT release asset")
        return assets[0]["browser_download_url"],release["tag_name"]
    if not any(host in url for host in ("raw.githubusercontent.com/","codeload.github.com/")):
        return url,source["revision"]
    repo="/".join(url.split("/")[3:5])
    headers={"Accept":"application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    req=Request("https://api.github.com/repos/"+repo+"/commits/HEAD",headers=headers)
    with urlopen(req,timeout=30) as r:
        revision=json.load(r)["sha"]
    if source["revision"] not in url:
        raise ValueError("No revision segment in pinned URL")
    return url.replace(source["revision"],revision),revision


def prepare(id):
    source=registry()[id]
    if not source.get("sha256"):
        raise ValueError("Source lacks an approved acquisition recipe")
    url,revision=latest_url(source)
    folder=ROOT/"sources"/id
    original=folder/"original"
    original.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=original) as tmp:
        path=Path(tmp)/"snapshot"
        with urlopen(url,timeout=180) as response,path.open("wb") as file:
            shutil.copyfileobj(response,file)
        digest=checksum(path)
        if digest==source["sha256"]:
            return {"status":"unchanged","source":id}
        revised=dict(source,url=url,revision=revision,sha256=digest,bytes=path.stat().st_size,status="staged")
        if id=="wikidata":
            from rdflib import Graph,URIRef
            g=Graph().parse(path,format="turtle")
            versions=set(g.objects(None,URIRef("http://schema.org/version")))
            if len(versions)!=1:
                raise ValueError("Ambiguous Wikidata document revision")
            revised["revision"]=str(versions.pop())
        # The original changes only inside this update checkout. Prior source
        # manifests and released bytes remain accessible through Git and mirrors.
        os.replace(path,original/"snapshot")
        report=ingest(revised,offline=True)
        if (original/"snapshot.gz").exists():
            with (original/"snapshot").open("rb") as inp, (path).open("wb") as out:
                with gzip.GzipFile(filename="",fileobj=out,mode="wb",mtime=0) as compressed:
                    shutil.copyfileobj(inp,compressed)
            os.replace(path,original/"snapshot.gz")
    write(folder/"source.yaml",revised)
    write(folder/"ingestion.json",report)
    suggestions=candidates(revised,authored()[0],offline=True)
    from pipeline.normalize.index import normalize
    norm=normalize(revised,True)
    write(folder/"normalization.json",dict(label_keys=norm["label_keys"],source=id,sha256=digest,
          candidates=len(suggestions),pending=sum(r["state"]=="pending" for r in suggestions)))
    affected=[d["id"] for state in ("approved","rejected") for d in read(ROOT/"reviews"/state/"mappings.json") if d["source"]==id]
    if (ROOT / "reviews/approved/batches" / f"{id}.json").exists():
        affected.append("batch/" + id)
    if (ROOT / "reviews/relations" / f"{id}.json").exists():
        affected.append("relations/" + id)
    if not affected:
        build()
    return dict(status="review-required",source=id,old=source["sha256"],new=digest,
                candidate_count=len(suggestions),decisions_requiring_review=affected)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source",choices=sorted(registry()))
    args=parser.parse_args()
    print(json.dumps(prepare(args.source),indent=2))
