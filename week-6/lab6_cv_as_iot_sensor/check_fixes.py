from pathlib import Path

APP_PATH = Path(__file__).resolve().with_name("app.py")
with APP_PATH.open(encoding='utf-8') as f:
    src = f.read()

checks = {
    'NMSBoxes fix (np.array)': 'np.array(raw, dtype=np.int64).flatten()' in src,
    'CameraManager.release() method': 'def release(self, camera_id' in src,
    'No init_db() at module level': 'init_db()\n' not in src[:src.index('async def lifespan')],
    'Latest endpoint crash fix': 'if meta:' in src[src.index('def latest()'):src.index('def latest()')+600],
    'record_video try/finally': 'try:' in src[src.index('def record_short_video'):src.index('def record_short_video')+600],
    'motion_capture try/finally': 'try:' in src[src.index('async def motion_capture'):src.index('async def motion_capture')+1500],
    'db_insert try/finally': 'finally:' in src[src.index('def db_insert'):src.index('def db_insert')+350],
    'db_query try/finally': 'finally:' in src[src.index('def db_query('):src.index('def db_query(')+350],
    '_update_last_seen try/finally': 'finally:' in src[src.index('def _update_last_seen'):src.index('def _update_last_seen')+350],
    'unregister try/finally': 'finally:' in src[src.index('def unregister'):src.index('def unregister')+350],
    'Security: no StaticFiles': 'StaticFiles' not in src,
    'Security: custom /files endpoint': '/files/{file_path:path}' in src,
    'motion_detected in broadcast': 'motion_detected' in src[src.index('async def motion_capture'):src.index('async def motion_capture')+3500],
    'COCO labels 80 classes': 'toothbrush' in src,
    'Stream cap reuse': 'if cap is None' in src[src.index('async def stream_frames'):src.index('async def stream_frames')+400],
    'No detect_uploaded_image dead code': 'def detect_uploaded_image' not in src,
    'PUT /config endpoint': '@app.put("/config")' in src,
    'Syntax OK': True,
}

import ast
try:
    ast.parse(src)
except SyntaxError as e:
    checks['Syntax OK'] = False
    print(f'Syntax error: {e}')

all_ok = True
for name, ok in sorted(checks.items()):
    status = 'OK' if ok else 'MISSING'
    if not ok: all_ok = False
    print(f'  [{status}] {name}')

print()
print('ALL FIXES APPLIED!' if all_ok else 'SOME FIXES ARE MISSING!')
