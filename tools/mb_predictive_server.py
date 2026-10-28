"""Loopback-only MB-Predictive UI and serialized local GPU generation service."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import json, threading, uuid, subprocess, traceback, re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'public/c08-motion-lab/docs'
JOBS = ROOT / 'evaluation/mb-predictive/local-jobs'
JOBS.mkdir(parents=True, exist_ok=True)
PORT = 8791
jobs = {}
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=1)
predictor = None

def harvest_records():
    manifest = ROOT/'evaluation/pose-harvest/catalog.json'
    if not manifest.exists():
        return []
    return json.loads(manifest.read_text(encoding='utf8'))['cases']

def sampled_case(settings):
    import numpy as np
    from scipy.spatial.transform import Rotation
    record = next((c for c in harvest_records() if c['id'] == settings['harvest_id']), None)
    if record is None or record.get('validation') != 'passed':
        raise ValueError('This sampled-pose experiment is not available')
    source = ROOT / record['directory']
    meta = json.loads((source/'g1-motion.json').read_text(encoding='utf8'))
    context = np.array(meta['inputs'][0]['context'], np.float32)
    anchor = context[-1, :2].copy()
    rotation = Rotation.from_euler('z', settings['yaw'], degrees=True)
    goals = []
    for item in meta['inputs']:
        goal = np.array(item['target'], np.float32)
        for row in goal:
            delta = np.array([*(row[:2]-anchor), 0.])
            row[:2] = anchor + rotation.apply(delta)[:2]*settings['spacing']
            row[3:7] = (rotation*Rotation.from_quat(row[3:7])).as_quat()
        goals.append(goal)
    provenance = {**meta['source_harvest'], 'target_placement_variant': {'spacing': settings['spacing'], 'yaw_degrees': settings['yaw']}}
    return {'id': settings['harvest_id'], 'label': 'Sampled-pose variation / '+record['label'], 'context': context, 'goals': goals, 'source_harvest': provenance, 'provenance_type': meta['provenance_type'], 'purpose': meta['purpose']+' Fresh target-placement variation.'}

def work(identifier, settings):
    global predictor
    try:
        jobs[identifier].update(status='running', message='Initializing MotionBricks on the local GPU...')
        from mb_predictive_generate import Predictor, goal
        from mb_predictive_finalize import finalize_case
        if predictor is None:
            predictor = Predictor()
        folder = JOBS / identifier
        folder.mkdir(exist_ok=True)
        jobs[identifier]['message'] = 'Generating movement and a matched interpolation baseline...'
        case = sampled_case(settings) if 'harvest_id' in settings else {'id': identifier, 'label': 'Local custom target', 'goals': [goal(settings['pose'], settings['x'], settings['y'], settings['yaw'])]}
        case['id'] = identifier
        predictor.generate(case, folder)
        jobs[identifier]['message'] = 'Retargeting both outputs to C08...'
        result = subprocess.run([str(ROOT/'tools/blender-4.5.15-windows-x64/blender.exe'), '-b', '-t', '2', '--python', str(ROOT/'tools/mb_predictive_retarget.py'), '--', str(folder)], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=120)
        (folder/'retarget.log').write_text(result.stdout + result.stderr, encoding='utf8')
        if result.returncode or not (folder/'linear/c08-motionbricks-test.glb').exists():
            raise RuntimeError('C08 adaptation failed; see the local job log.')
        jobs[identifier]['message'] = 'Validating the exported animation and preparing its trace...'
        finalize_case(folder, folder/'public')
        jobs[identifier].update(status='complete', message='Fresh prediction ready.', base='/mb-predictive/generated/' + identifier + '/')
    except Exception as error:
        jobs[identifier].update(status='failed', error=str(error), message='Generation failed.')
        (JOBS/(identifier+'-error.txt')).write_text(traceback.format_exc(), encoding='utf8')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def send_json(self, value, status=200):
        payload = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == '/api/predictive/status':
            return self.send_json({'service': 'mb-predictive', 'generation': 'local GPU', 'ready': True})
        if route == '/api/predictive/pose-catalog':
            manifest = ROOT/'evaluation/pose-harvest/private-catalog.json'
            return self.send_json(json.loads(manifest.read_text(encoding='utf8')) if manifest.exists() else {'cases': []})
        if route.startswith('/api/predictive/jobs/'):
            job = jobs.get(route.rsplit('/', 1)[-1])
            return self.send_json(job or {'error': 'Unknown job'}, 200 if job else 404)
        if route.startswith('/api/'):
            return self.send_json({'error': 'Unknown API route'}, 404)
        return super().do_GET()

    def do_POST(self):
        if self.headers.get('Host') not in (f'127.0.0.1:{PORT}', f'localhost:{PORT}'):
            return self.send_json({'error': 'Invalid host'}, 403)
        if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
            return self.send_json({'error': 'Use the local UI'}, 403)
        if self.path != '/api/predictive/generate':
            return self.send_json({'error': 'Unknown route'}, 404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2048 or self.headers.get_content_type() != 'application/json':
                raise ValueError('Expected a small JSON target specification')
            value = json.loads(self.rfile.read(size))
            if 'harvest_id' in value:
                settings = {'harvest_id': str(value['harvest_id']), 'spacing': float(value['spacing']), 'yaw': float(value['yaw'])}
                if not (.5 <= settings['spacing'] <= 1.5 and -45 <= settings['yaw'] <= 45 and any(c['id'] == settings['harvest_id'] for c in harvest_records())):
                    raise ValueError('Unsupported sampled-pose variation')
            else:
                settings = {key: float(value[key]) for key in ('x', 'y', 'yaw')}
                settings['pose'] = value['pose']
                if not (.3 <= settings['x'] <= 1.4 and -.4 <= settings['y'] <= .4 and -60 <= settings['yaw'] <= 60 and settings['pose'] in ('neutral', 'crouch', 'reach_right')):
                    raise ValueError('Target is outside the supported input range')
        except (ValueError, KeyError, TypeError) as error:
            return self.send_json({'error': str(error)}, 400)
        with lock:
            if any(job['status'] in ('queued', 'running') for job in jobs.values()):
                return self.send_json({'error': 'A prediction is already running; wait for it to complete.'}, 409)
            identifier = uuid.uuid4().hex
            jobs[identifier] = {'id': identifier, 'status': 'queued', 'message': 'Queued on the local GPU.'}
            executor.submit(work, identifier, settings)
        return self.send_json({'id': identifier, 'status': 'queued'}, 202)

    def translate_path(self, path):
        route = urlsplit(path).path
        evaluation_prefix = '/mb-predictive/evaluation/'
        if route.startswith(evaluation_prefix):
            base = (ROOT/'evaluation/pose-harvest/local-view').resolve()
            target = base.joinpath(route[len(evaluation_prefix):]).resolve()
            return str(target) if target.is_relative_to(base) else str(SITE/'__not_found__')
        prefix = '/mb-predictive/generated/'
        if route.startswith(prefix):
            parts = route[len(prefix):].split('/')
            identifier = parts[0]
            if not re.fullmatch('[0-9a-f]{32}', identifier):
                return str(SITE/'__not_found__')
            base = (JOBS/identifier/'public').resolve()
            target = base.joinpath(*parts[1:]).resolve()
            if not target.is_relative_to(base):
                return str(SITE/'__not_found__')
            return str(target)
        return super().translate_path(path)

if __name__ == '__main__':
    print(f'MB-Predictive local UI: http://127.0.0.1:{PORT}/mb-predictive/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
