#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,sys

ALLOWED_ROOT={"README.md","public-manifest.json",".github","tools","assets"}
ALLOWED_CONTROL={"README.md","public-manifest.json",".github/workflows/validate-public-art.yml","tools/validate_public_art.py","tools/test_public_art.py"}
IMG_EXT={".png",".jpg",".jpeg",".webp",".gif"};MAX_BYTES=10*1024*1024
FORBID=re.compile(r"(^|[\/_.:-])(dm|dmhold|dm_hold|dm-only|dm_only|secret|unreleased|spoiler)([\/_.:-]|$)",re.I)
ARCH={".zip",".7z",".rar",".tar",".gz",".tgz",".bz2"};APPROVAL=re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ASSET_KEYS={"path","public_id","classification","sha256","bytes","approval_ref"};TOP_KEYS={"schema_version","repository_purpose","assets"}

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
 root=Path(root).resolve();err=[];man=root/"public-manifest.json"
 def fail(x):err.append(x)
 for p in root.iterdir():
  if p.name==".git":continue
  if p.name not in ALLOWED_ROOT:fail(f"unexpected top-level path: {p.name}")
 for p in root.rglob("*"):
  if ".git" in p.parts or "__pycache__" in p.parts or p.suffix==".pyc" or not p.is_file():continue
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():fail(f"symlink prohibited: {rel}")
  if not rel.startswith("assets/") and rel not in ALLOWED_CONTROL:fail(f"unexpected control/public file: {rel}")
  if p.suffix.lower() in ARCH or "_staging" in rel.lower() or "/staging/" in rel.lower():fail(f"archive/staging prohibited: {rel}")
  if FORBID.search(rel):fail(f"sensitive filename/path token prohibited: {rel}")
  if rel.startswith("assets/"):
   if p.suffix.lower() not in IMG_EXT:fail(f"non-image file in assets/: {rel}")
   if p.stat().st_size>MAX_BYTES:fail(f"asset exceeds {MAX_BYTES} bytes: {rel}")
 try:data=json.loads(man.read_text(encoding="utf-8"))
 except Exception as e:fail(f"manifest missing/invalid: {e}");data={}
 if data:
  if set(data)!=TOP_KEYS:fail(f"manifest top-level keys must be exactly {sorted(TOP_KEYS)}")
  if data.get("schema_version")!=1:fail("manifest schema_version must be 1")
  if data.get("repository_purpose")!="PLAYER_SAFE_PUBLIC_NOTION_ART":fail("manifest repository_purpose mismatch")
  assets=data.get("assets")
  if not isinstance(assets,list):fail("manifest assets must be a list");assets=[]
 else:assets=[]
 seen=set();ids=set();listed=set()
 for i,a in enumerate(assets):
  if not isinstance(a,dict):fail(f"manifest row {i} not object");continue
  if set(a)!=ASSET_KEYS:fail(f"manifest asset keys mismatch at row {i}")
  path=str(a.get("path",""));pid=str(a.get("public_id",""));approval=str(a.get("approval_ref",""))
  if not path.startswith("assets/") or path.startswith("assets//") or ".." in Path(path).parts or len(path)>240:fail(f"invalid manifest path: {path}")
  if path in seen:fail(f"duplicate manifest path: {path}")
  seen.add(path);listed.add(path)
  if not pid or pid in ids:fail(f"missing/duplicate public_id: {pid}")
  ids.add(pid)
  if a.get("classification")!="PLAYER_SAFE":fail(f"non-player-safe classification: {path}")
  if not APPROVAL.fullmatch(approval):fail(f"invalid approval_ref: {path}")
  if FORBID.search(path) or FORBID.search(pid) or FORBID.search(approval):fail(f"sensitive token in manifest entry: {path}")
  p=root/path
  if not p.exists() or not p.is_file():fail(f"manifest asset missing: {path}");continue
  if p.suffix.lower() not in IMG_EXT:fail(f"unsupported asset extension: {path}")
  if p.stat().st_size>MAX_BYTES:fail(f"asset exceeds {MAX_BYTES} bytes: {path}")
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
 w=root/".github/workflows/validate-public-art.yml"
 if not w.exists():fail("validation workflow missing")
 else:
  t=w.read_text(encoding="utf-8",errors="replace")
  for tok in ["pull_request:","permissions:","contents: read","persist-credentials: false","actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1","actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97","validate-public-art"]:
   if tok not in t:fail(f"workflow missing hardening token: {tok}")
  for bad in ["pull_request_target","contents: write","pull-requests: write","issues: write"]:
   if bad in t:fail(f"workflow contains prohibited token: {bad}")
 return err

def main():
 root=Path(os.environ.get("TOTFR_PUBLIC_ROOT",Path(__file__).resolve().parents[1]));err=validate(root)
 if err:
  print("TOTFR PUBLIC ART VALIDATION FAILED")
  for e in err:print("- "+e)
  return 1
 adir=root/"assets";n=sum(1 for p in adir.rglob("*") if p.is_file()) if adir.exists() else 0
 print(f"TOTFR PUBLIC ART VALIDATION PASSED: assets={n}")
 print("END-OF-FILE SENTINEL: TOTFR-PUBLIC-ART-VALIDATOR-2026-09-05-V2")
 return 0
if __name__=="__main__":raise SystemExit(main())
