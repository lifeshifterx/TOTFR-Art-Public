#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys,tempfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_public_art import validate,MAX_BYTES
WORKFLOW="""name: Validate Public Art
'on':
  pull_request:
permissions:
  contents: read
jobs:
  validate-public-art:
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97
"""
def png_bytes():return b"\x89PNG\r\n\x1a\n"+b"\0"*32
def manifest(d,assets=[],extra=None):
 x={"schema_version":1,"repository_purpose":"PLAYER_SAFE_PUBLIC_NOTION_ART","assets":assets}
 if extra:x.update(extra)
 (d/"public-manifest.json").write_text(json.dumps(x,indent=2)+"\n")
def base():
 d=Path(tempfile.mkdtemp());(d/"assets").mkdir();(d/"tools").mkdir();(d/".github/workflows").mkdir(parents=True)
 (d/"README.md").write_text("# TOTFR Art Public\nPLAYER_SAFE artwork for Notion. See public-manifest.json.\n")
 (d/".github/workflows/validate-public-art.yml").write_text(WORKFLOW)
 (d/"tools/validate_public_art.py").write_text("# test fixture\n");(d/"tools/test_public_art.py").write_text("# test fixture\n");manifest(d);return d
def good_asset(d,name="x.png",pid="x"):
 p=d/"assets"/name;p.write_bytes(png_bytes());h=hashlib.sha256(p.read_bytes()).hexdigest()
 return p,{"path":p.relative_to(d).as_posix(),"public_id":pid,"classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size,"approval_ref":"approval:0001"}
def reject(name,mut):
 d=base()
 try:
  mut(d);e=validate(d)
  if not e:raise SystemExit(f"FAILED TO REJECT: {name}")
  print("PASS reject:",name)
 finally:shutil.rmtree(d)
d=base();assert not validate(d);shutil.rmtree(d)
reject("unlisted image",lambda d:(d/"assets/x.png").write_bytes(png_bytes()))
reject("DM path",lambda d:(d/"assets/DM_HOLD.png").write_bytes(png_bytes()))
reject("archive",lambda d:(d/"assets.zip").write_bytes(b"x"))
reject("unexpected top-level control",lambda d:(d/"AGENTS.md").write_text("no"))
reject("extra workflow",lambda d:(d/".github/workflows/other.yml").write_text("name: bad"))
reject("extra tool",lambda d:(d/"tools/notes.txt").write_text("bad"))
reject("malformed manifest",lambda d:(d/"public-manifest.json").write_text("{"))
reject("hidden manifest metadata",lambda d:manifest(d,[],{"notes":"should not be public"}))
def wrong_hash(d):
 p,a=good_asset(d);a["sha256"]="0"*64;manifest(d,[a])
reject("hash mismatch",wrong_hash)
def wrong_class(d):
 p,a=good_asset(d);a["classification"]="DM_HOLD";manifest(d,[a])
reject("non-player-safe classification",wrong_class)
def missing_approval(d):
 p,a=good_asset(d);a["approval_ref"]="";manifest(d,[a])
reject("missing approval ref",missing_approval)
def wrong_sig(d):
 p=d/"assets/x.png";p.write_bytes(b"not png");h=hashlib.sha256(p.read_bytes()).hexdigest();manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size,"approval_ref":"approval:0001"}])
reject("fake image signature",wrong_sig)
def duplicate_path(d):
 p,a=good_asset(d);manifest(d,[a,a])
reject("duplicate manifest path",duplicate_path)
def duplicate_id(d):
 p,a=good_asset(d,"x.png","same");q,b=good_asset(d,"y.png","same");b["approval_ref"]="approval:0002";manifest(d,[a,b])
reject("duplicate public id",duplicate_id)
reject("manifest missing asset",lambda d:manifest(d,[{"path":"assets/missing.png","public_id":"m","classification":"PLAYER_SAFE","sha256":"0"*64,"bytes":1,"approval_ref":"approval:0001"}]))
def workflow_write(d):
 p=d/".github/workflows/validate-public-art.yml";p.write_text(WORKFLOW.replace("contents: read","contents: write"))
reject("workflow write permission",workflow_write)
def mutable_action(d):
 p=d/".github/workflows/validate-public-art.yml";p.write_text(WORKFLOW.replace("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1","actions/checkout@v7"))
reject("mutable action tag",mutable_action)
def oversized(d):
 p=d/"assets/x.png";p.write_bytes(b"\x89PNG\r\n\x1a\n"+b"\0"*(MAX_BYTES+1));h=hashlib.sha256(p.read_bytes()).hexdigest();manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size,"approval_ref":"approval:0001"}])
reject("oversized asset",oversized)
d=base();p,a=good_asset(d);manifest(d,[a]);assert not validate(d);shutil.rmtree(d)
print("TOTFR PUBLIC ART HOSTILE TESTS PASSED: rejected=18 clean_baselines=2")
print("END-OF-FILE SENTINEL: TOTFR-PUBLIC-ART-TESTS-2026-09-05-V2")
