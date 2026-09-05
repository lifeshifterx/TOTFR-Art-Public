#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,sys

ALLOWED_ROOT={"README.md","public-manifest.json",".github","tools","assets"}
IMG_EXT={".png",".jpg",".jpeg",".webp",".gif"}
FORBID=re.compile(r"(^|[\/_.-])(dm|dmhold|dm_hold|dm-only|dm_only|secret|unreleased|spoiler)([\/_.-]|$)",re.I)
ARCH={".zip",".7z",".rar",".tar",".gz",".tgz",".bz2"}

def _sha256(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()

def _sig_ok(p):
 b=p.read_bytes()[:16];e=p.suffix.lower()
 return ((e==".png" and b.startswith(b"\x89PNG\r\n\x1a\n")) or
         (e in {".jpg",".jpeg"} and b.startswith(b"\xff\xd8\xff")) or
         (e==".webp" and len(b)>=12 and b[:4]==b"RIFF" and b[8:12]==b"WEBP") or
         (e==".gif" and b.startswith((b"GIF87a",b"GIF89a"))))

def validate(root):
 root=Path(root).resolve(); err=[]; man=root/"public-manifest.json"
 def fail(x):err.append(x)
 for p in root.iterdir():
  if p.name==".git":continue
  if p.name not in ALLOWED_ROOT:fail(f"unexpected top-level path: {p.name}")
 for p in root.rglob("*"):
  if ".git" in p.parts or not p.is_file():continue
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():fail(f"symlink prohibited: {rel}")
  if p.suffix.lower() in ARCH or "_staging" in rel.lower() or "/staging/" in rel.lower():fail(f"archive/staging prohibited: {rel}")
  if FORBID.search(rel):fail(f"sensitive filename/path token prohibited: {rel}")
  if rel.startswith("assets/") and p.suffix.lower() not in IMG_EXT:fail(f"non-image file in assets/: {rel}")
 try:data=json.loads(man.read_text(encoding="utf-8"))
 except Exception as e:fail(f"manifest missing/invalid: {e}");data={}
 if data:
  if data.get("schema_version")!=1:fail("manifest schema_version must be 1")
  if data.get("repository_purpose")!="PLAYER_SAFE_PUBLIC_NOTION_ART":fail("manifest repository_purpose mismatch")
  assets=data.get("assets")
  if not isinstance(assets,list):fail("manifest assets must be a list");assets=[]
 else:assets=[]
 seen=set();listed=set()
 for i,a in enumerate(assets):
  if not isinstance(a,dict):fail(f"manifest row {i} not object");continue
  path=str(a.get("path",""))
  if not path.startswith("assets/") or path.startswith("assets//") or ".." in Path(path).parts:fail(f"invalid manifest path: {path}")
  if path in seen:fail(f"duplicate manifest path: {path}")
  seen.add(path);listed.add(path)
  if a.get("classification")!="PLAYER_SAFE":fail(f"non-player-safe classification: {path}")
  if FORBID.search(path) or FORBID.search(str(a.get("public_id",""))):fail(f"sensitive token in manifest entry: {path}")
  p=root/path
  if not p.exists() or not p.is_file():fail(f"manifest asset missing: {path}");continue
  if p.suffix.lower() not in IMG_EXT:fail(f"unsupported asset extension: {path}")
  if not _sig_ok(p):fail(f"image signature mismatch: {path}")
  if a.get("sha256")!=_sha256(p):fail(f"sha256 mismatch: {path}")
  if a.get("bytes")!=p.stat().st_size:fail(f"byte-size mismatch: {path}")
 actual=set();adir=root/"assets"
 if adir.exists():
  for p in adir.rglob("*"):
   if p.is_file():actual.add(p.relative_to(root).as_posix())
 for p in sorted(actual-listed):fail(f"unlisted public asset: {p}")
 for p in sorted(listed-actual):fail(f"manifest lists absent asset: {p}")
 r=root/"README.md"
 if not r.exists():fail("README.md missing")
 else:
  t=r.read_text(encoding="utf-8",errors="replace")
  for tok in ["PLAYER_SAFE","Notion","public-manifest.json"]:
   if tok not in t:fail(f"README missing policy token: {tok}")
 return err

def main():
 root=Path(os.environ.get("TOTFR_PUBLIC_ROOT",Path(__file__).resolve().parents[1]))
 err=validate(root)
 if err:
  print("TOTFR PUBLIC ART VALIDATION FAILED")
  for e in err:print("- "+e)
  return 1
 assets=(root/"assets")
 n=sum(1 for p in assets.rglob("*") if p.is_file()) if assets.exists() else 0
 print(f"TOTFR PUBLIC ART VALIDATION PASSED: assets={n}")
 print("END-OF-FILE SENTINEL: TOTFR-PUBLIC-ART-VALIDATOR-2026-09-05-V1")
 return 0
if __name__=="__main__":raise SystemExit(main())
