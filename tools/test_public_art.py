#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys,tempfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_public_art import validate

def png_bytes():return b"\x89PNG\r\n\x1a\n"+b"\0"*32
def manifest(d,assets=[]):
 (d/"public-manifest.json").write_text(json.dumps({"schema_version":1,"repository_purpose":"PLAYER_SAFE_PUBLIC_NOTION_ART","assets":assets},indent=2)+"\n")
def base():
 d=Path(tempfile.mkdtemp());(d/"assets").mkdir()
 (d/"README.md").write_text("# TOTFR Art Public\nPLAYER_SAFE artwork for Notion. See public-manifest.json.\n")
 manifest(d);return d
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
reject("malformed manifest",lambda d:(d/"public-manifest.json").write_text("{"))
def wrong_hash(d):
 p=d/"assets/x.png";p.write_bytes(png_bytes());manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":"0"*64,"bytes":p.stat().st_size}])
reject("hash mismatch",wrong_hash)
def wrong_class(d):
 p=d/"assets/x.png";p.write_bytes(png_bytes());h=hashlib.sha256(p.read_bytes()).hexdigest();manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"DM_HOLD","sha256":h,"bytes":p.stat().st_size}])
reject("non-player-safe classification",wrong_class)
def wrong_sig(d):
 p=d/"assets/x.png";p.write_bytes(b"not png");h=hashlib.sha256(p.read_bytes()).hexdigest();manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size}])
reject("fake image signature",wrong_sig)
def duplicate(d):
 p=d/"assets/x.png";p.write_bytes(png_bytes());h=hashlib.sha256(p.read_bytes()).hexdigest();a={"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size};manifest(d,[a,a])
reject("duplicate manifest path",duplicate)
reject("manifest missing asset",lambda d:manifest(d,[{"path":"assets/missing.png","public_id":"m","classification":"PLAYER_SAFE","sha256":"0"*64,"bytes":1}]))
d=base();p=d/"assets/x.png";p.write_bytes(png_bytes());h=hashlib.sha256(p.read_bytes()).hexdigest();manifest(d,[{"path":"assets/x.png","public_id":"x","classification":"PLAYER_SAFE","sha256":h,"bytes":p.stat().st_size}]);assert not validate(d);shutil.rmtree(d)
print("TOTFR PUBLIC ART HOSTILE TESTS PASSED: rejected=10 clean_baselines=2")
print("END-OF-FILE SENTINEL: TOTFR-PUBLIC-ART-TESTS-2026-09-05-V1")
