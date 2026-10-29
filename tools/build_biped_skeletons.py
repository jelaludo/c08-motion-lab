"""Publish only recovered joint data, never source frames or private source paths."""
from pathlib import Path
import argparse, gzip, hashlib, json, os

PUBLIC = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--workspace', type=Path, default=Path(os.environ.get('MOTION_LAB_WORKSPACE', PUBLIC.parent.parent)))
args = parser.parse_args()
catalog = json.loads((PUBLIC/'docs/biped-motion/catalog.json').read_text(encoding='utf-8'))
out = PUBLIC/'docs/biped-motion/data'
out.mkdir(parents=True, exist_ok=True)
rows = []
for test in catalog['tests']:
    slug = test['id']
    assert slug and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in slug)
    source = args.workspace/'video-mocap'/slug/'joint-trajectory.json'
    original = json.loads(source.read_text(encoding='utf-8'))
    keys = ['fps', 'frame_count', 'duration_s', 'joint_names', 'parent_indices', 'timestamps', 'positions', 'display_offset']
    data = {key: original[key] for key in keys}
    data.update(schema='motion-lab-recovered-skeleton/1', id=slug, label=test['title'], provenance='GEM-X raw recovered SOMA77 motion; source imagery excluded', coordinate_system={'up': '+Y', 'units': 'metres', 'space': 'raw recovered world'}, display_note='One constant display translation; optional XZ camera following changes display only. No per-frame floor correction or contact solve.')
    assert len(data['positions']) == data['frame_count'] == len(data['timestamps'])
    assert len(data['joint_names']) == len(data['parent_indices']) == 77
    encoded = json.dumps(data, separators=(',', ':'), allow_nan=False).encode('utf-8')
    destination = out/f'{slug}-skeleton.json.gz'
    destination.write_bytes(gzip.compress(encoded, mtime=0))
    rows.append({'id': slug, 'path': destination.relative_to(PUBLIC).as_posix(), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'frames': data['frame_count'], 'joints': 77, 'raw_source_media_included': False})
report = {'status': 'passed', 'cases': len(rows), 'artifacts': rows, 'checks': ['Only explicit recovered-joint fields copied', 'No source video, source frames, local paths or weights', 'Finite JSON serialization and matching 77-joint/frame counts']}
(PUBLIC/'research/biped-skeleton-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
