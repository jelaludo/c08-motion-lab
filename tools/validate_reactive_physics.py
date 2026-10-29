"""Independent CSV/NPZ swept-circle audit for the expanded reactive course.

This deliberately does not import the generator or its collision routines.
It checks the played trajectory, including inter-frame segments, and preserves
the distinction between root-proxy clearance and full-avatar collision tests.
"""
from pathlib import Path
import argparse
import csv
import json
import math
import numpy as np


def sweep_clearance(path, center, radius):
    a = path[:-1]
    delta = path[1:] - a
    offset = np.asarray(center) - a
    length2 = np.sum(delta * delta, axis=1)
    fraction = np.divide(np.sum(offset * delta, axis=1), length2,
                         out=np.zeros_like(length2), where=length2 > 1e-16)
    fraction = np.clip(fraction, 0, 1)
    closest = a + delta * fraction[:, None]
    distance = np.linalg.norm(closest - center, axis=1) - radius
    return float(distance.min()), int(np.sum(distance < -0.001))


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--public', type=Path, default=root / 'public/c08-motion-lab/docs/reactive')
    parser.add_argument('--report', type=Path, default=root / 'logs/reactive-physics-validation.json')
    parser.add_argument('--working', action='store_true', help='Audit generated native files before publication; CSV checks wait for the final audit.')
    args = parser.parse_args()
    catalog = json.loads((args.public / 'catalog.json').read_text(encoding='utf8'))
    rows, errors, environments = [], [], {}
    for case in catalog['cases']:
        folder = args.public / case['id'] if args.working else args.public / 'takes' / case['id']
        episode_path = folder / 'episode.json' if args.working else args.public / case['episode']
        episode = json.loads(episode_path.read_text(encoding='utf8'))
        env = episode['environment']
        if args.working:
            data = [dict(time_s=i / episode['sample_rate'], g1_x_m=p[0], g1_y_m=p[1],
                         g1_z_m=p[2], cat_x_m=env['cat_path'][i][0], cat_y_m=env['cat_path'][i][1])
                    for i, p in enumerate(episode['raw_root_path'])]
        else:
            data = list(csv.DictReader((folder / 'root-trajectory.csv').open(encoding='utf8')))
        path = np.array([[float(r['g1_x_m']), float(r['g1_y_m'])] for r in data])
        cat = np.array([[float(r['cat_x_m']), float(r['cat_y_m'])] for r in data])
        times = np.array([float(r['time_s']) for r in data])
        native = np.load(folder / ('g1-motion.npz' if args.working else 'native-g1-motion.npz'))['qpos']
        fps = episode['sample_rate']
        duration = episode['duration_s']
        bounds = env['bounds']
        xmin, xmax, ymin, ymax = bounds
        rr, cr = env['root_radius_m'], env['cat_radius_m']
        failures = []
        if xmax - xmin < 30 or ymax - ymin < 8:
            failures.append('Arena is smaller than 30 m by 8 m')
        if len(env['obstacles']) < 8:
            failures.append('Fewer than eight obstacles')
        if duration < (32 if case['scenario'] in ('pursuit', 'mixed') else 24):
            failures.append('Take duration below the expanded protocol')
        if len(path) != round(duration * fps) + 1 or not np.allclose(np.diff(times), 1 / fps):
            failures.append('CSV timestamps/frame count disagree with duration')
        if native.shape[0] != len(path) or np.max(np.abs(native[:, :2] - path)) > 1e-6:
            failures.append('Native played NPZ and exported trajectory disagree')
        if not np.isfinite(native).all() or not np.isfinite(cat).all():
            failures.append('Nonfinite data')
        if np.max(np.abs(np.array(episode['raw_root_path'])[:, :2] - path)) > 1e-6:
            failures.append('Viewer root path and CSV disagree')
        if np.max(np.abs(np.array(env['cat_path']) - cat)) > 1e-6:
            failures.append('Viewer cat path and CSV disagree')
        predicted = np.array(episode['predicted_root_path'])
        if predicted.shape != (len(path), 3):
            failures.append('Unmodified selected predictions were not preserved')
        root_change = np.linalg.norm(predicted[:, :2] - path, axis=1)
        key = (case['scenario'], case['seed'])
        if key in environments and env != environments[key]:
            failures.append('Paired conditions do not share the exact environment')
        environments[key] = env
        root_clearance, cat_clearance, swept_bad, cat_bad = math.inf, math.inf, 0, 0
        min_pillar_gap, impassable_pillar_pairs = math.inf, 0
        for i, ob in enumerate(env['obstacles']):
            if not (xmin + ob['radius'] <= ob['center'][0] <= xmax - ob['radius']
                    and ymin + ob['radius'] <= ob['center'][1] <= ymax - ob['radius']):
                failures.append('Obstacle lies outside the arena bounds')
            clearance, bad = sweep_clearance(path, np.array(ob['center']), rr + ob['radius'])
            root_clearance, swept_bad = min(root_clearance, clearance), swept_bad + bad
            clearance, bad = sweep_clearance(cat, np.array(ob['center']), cr + ob['radius'])
            cat_clearance, cat_bad = min(cat_clearance, clearance), cat_bad + bad
            for other in env['obstacles'][i + 1:]:
                gap = float(np.linalg.norm(np.array(ob['center']) - other['center'])) - ob['radius'] - other['radius']
                min_pillar_gap = min(min_pillar_gap, gap)
                impassable_pillar_pairs += gap < 2 * rr
        if swept_bad or cat_bad:
            failures.append('Continuous trajectory intersects an inflated obstacle circle')
        # Every obstacle must be physically separated, but every gap need not be
        # traversable. The planner must route around gaps narrower than the avatar.
        if min_pillar_gap < 0:
            failures.append('Pillar geometry overlaps; spacing is reported separately')
        root_wall = float(min((path[:, 0] - xmin - rr).min(), (xmax - rr - path[:, 0]).min(), (path[:, 1] - ymin - rr).min(), (ymax - rr - path[:, 1]).min()))
        cat_wall = float(min((cat[:, 0] - xmin - cr).min(), (xmax - cr - cat[:, 0]).min(), (cat[:, 1] - ymin - cr).min(), (ymax - cr - cat[:, 1]).min()))
        if root_wall < -.001 or cat_wall < -.001:
            failures.append('Circle proxy leaves arena bounds')
        trace = json.loads((folder / 'prediction-trace.json').read_text(encoding='utf8'))
        for segment in trace['metadata']['segments']:
            start, n = segment['start_frame'], segment['frames']
            if start >= 4 and not np.allclose(segment['context'], native[start - 4:start], atol=1e-5):
                failures.append('Generation context does not match actual corrected playback')
                break
            if not np.allclose(segment['last_four_generated'], native[start + n - 4:start + n], atol=1e-5):
                failures.append('Saved final context does not match actual played poses')
                break
        speed = np.linalg.norm(np.diff(path, axis=0) * fps, axis=1)
        command_max = max(c['desired_speed'] for c in episode['commands'])
        if case['scenario'] in ('speedzones', 'pursuit', 'mixed') and command_max < 2:
            failures.append('Expanded running command never reaches 2 m/s')
        if case['scenario'] == 'speedzones' and case['condition'] == 'reactive' and np.sum(speed > 1.5) / fps < 3:
            failures.append('Reactive speed-zone take lacks three seconds of measured running above 1.5 m/s')
        cat_separation, _ = sweep_clearance(path - cat, np.array([0., 0.]), rr + cr)
        row = dict(id=case['id'], duration_s=duration, frames=len(path), arena_bounds=bounds,
                   obstacles=len(env['obstacles']), minimum_pillar_gap_m=min_pillar_gap,
                   pillar_pairs_narrower_than_root_diameter=impassable_pillar_pairs,
                   minimum_continuous_root_clearance_m=root_clearance,
                   minimum_continuous_cat_clearance_m=cat_clearance,
                   swept_root_penetrations=swept_bad, swept_cat_penetrations=cat_bad,
                   minimum_root_wall_clearance_m=root_wall, minimum_cat_wall_clearance_m=cat_wall,
                   mean_speed_m_s=float(speed.mean()), max_speed_m_s=float(speed.max()),
                   seconds_above_1_5_m_s=float(np.sum(speed > 1.5) / fps),
                   root_travel_m=float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()),
                   actual_root_extent_m=(path.max(axis=0) - path.min(axis=0)).tolist(),
                   cat_travel_m=float(np.linalg.norm(np.diff(cat, axis=0), axis=1).sum()),
                   actual_cat_extent_m=(cat.max(axis=0) - cat.min(axis=0)).tolist(),
                   minimum_continuous_root_cat_clearance_m=cat_separation,
                   corrected_root_frames=int(np.sum(root_change > 1e-5)),
                   maximum_root_correction_from_unmodified_prediction_m=float(root_change.max()),
                   max_command_speed_m_s=command_max, failures=failures)
        rows.append(row)
        errors.extend(f'{case["id"]}: {failure}' for failure in failures)
    report = dict(status='failed' if errors else 'passed', cases=len(rows),
                  mode='native working files; published CSV not yet audited' if args.working else 'published CSV and native NPZ',
                  checks=['Expanded arena dimensions and obstacle count/spacing',
                          'Long pursuit duration', 'CSV/native/viewer path agreement',
                          'Independent continuous circle sweeps, including between frames',
                          'Cat obstacle avoidance and arena containment',
                          'Corrected playback forms subsequent neural context',
                          'Actual and commanded running speed reported separately'],
                  limitation='Circle-proxy navigation validation; this is not a whole-body collision or dynamics guarantee.',
                  results=rows, errors=errors)
    args.report.parent.mkdir(exist_ok=True, parents=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(dict(status=report['status'], cases=len(rows), errors=errors[:15])))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
