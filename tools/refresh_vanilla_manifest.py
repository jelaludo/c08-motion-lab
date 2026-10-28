"""Version the Vanilla candidates from their recipes, source assets and playback code."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'public/c08-motion-lab/docs'
path = DOCS / 'vanilla/manifest.json'
data = json.loads(path.read_text(encoding='utf8'))
def source_hash(source):
    payload = source.read_bytes()
    # Git stores text with LF even when Windows checks it out with CRLF.
    if source.suffix == '.js':
        payload = payload.replace(b'\r\n', b'\n')
    return hashlib.sha256(payload).hexdigest()

data['hash_normalization'] = 'JavaScript SHA-256 uses UTF-8 bytes with CRLF normalized to LF, matching Git and Pages; binary assets use unchanged bytes.'
data['hashes'] = {
    str(p.relative_to(DOCS)).replace('\\', '/'): source_hash(p)
    for p in [DOCS / 'quaternius/c08-quaternius.glb', DOCS / 'vanilla/c08-extra.glb', DOCS / 'vanilla/vanilla.js', DOCS / 'vanilla/motion-cleanup.js', DOCS / 'shared/review-store.js', DOCS / 'shared/review-panel.js', DOCS / 'shared/bake-take.js']
}
data['version'] = 'v1-' + hashlib.sha256(json.dumps([data['candidates'], data['hashes']], sort_keys=True).encode()).hexdigest()[:12]
path.write_text(json.dumps(data, indent=2), encoding='utf8')
print(data['version'])
