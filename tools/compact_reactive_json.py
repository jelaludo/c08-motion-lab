"""Remove JSON whitespace from published neural traces without changing any value."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1] / 'public/c08-motion-lab/docs/reactive/takes'
before = after = count = 0
for folder in root.iterdir():
    if not folder.is_dir():
        continue
    for name in ('prediction-trace.json', 'g1-motion.json'):
        path = folder / name
        if not path.exists():
            continue
        source = path.read_bytes()
        parsed = json.loads(source)
        encoded = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf8')
        assert json.loads(encoded) == parsed, path
        path.write_bytes(encoded)
        before += len(source)
        after += len(encoded)
        count += 1
print(json.dumps(dict(files=count, before_bytes=before, after_bytes=after, saved_bytes=before-after,
                      numeric_values_changed=False)))
