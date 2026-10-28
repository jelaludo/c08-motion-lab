from pathlib import Path
import json,struct
OUT=Path(__file__).resolve().parents[1]/'evaluation/vanilla-base'
path=OUT/'c08-quaternius.glb';payload=path.read_bytes();size=struct.unpack_from('<I',payload,12)[0];document=json.loads(payload[20:20+size]);binary=payload[20+size:]
for i,node in enumerate(document['nodes']):
 if 'skin' not in node:continue
 assert not any(k in node for k in ('matrix','translation','rotation','scale'))
 for parent in document['nodes']:
  if i in parent.get('children',[]):parent['children'].remove(i)
 for s in document['scenes']:
  if i not in s['nodes']:s['nodes'].append(i)
for animation in document['animations']:
 animation['channels']=[c for c in animation['channels'] if c['target']['path']!='scale' and not document['nodes'][c['target']['node']].get('name','').startswith('SOCKET_') and document['nodes'][c['target']['node']].get('name') not in ('ROOT','SENSOR_YAW')]
 used=sorted({c['sampler'] for c in animation['channels']});mapping={a:b for b,a in enumerate(used)};animation['samplers']=[animation['samplers'][i] for i in used]
 for c in animation['channels']:c['sampler']=mapping[c['sampler']]
slots=[]
for mesh in document.get('meshes',[]):
 for primitive in mesh['primitives']:
  slots.extend((primitive['attributes'],k) for k in primitive['attributes'])
  if 'indices' in primitive:slots.append((primitive,'indices'))
for skin in document.get('skins',[]):
 if 'inverseBindMatrices' in skin:slots.append((skin,'inverseBindMatrices'))
for animation in document['animations']:
 for sampler in animation['samplers']:slots.extend(((sampler,'input'),(sampler,'output')))
used=sorted({d[k] for d,k in slots});mapping={a:b for b,a in enumerate(used)};document['accessors']=[document['accessors'][i] for i in used]
for d,k in slots:d[k]=mapping[d[k]]
slots=[]
for accessor in document['accessors']:
 if 'bufferView' in accessor:slots.append((accessor,'bufferView'))
 if 'sparse' in accessor:slots.extend(((accessor['sparse']['indices'],'bufferView'),(accessor['sparse']['values'],'bufferView')))
used=sorted({d[k] for d,k in slots});mapping={a:b for b,a in enumerate(used)};document['bufferViews']=[document['bufferViews'][i] for i in used]
for d,k in slots:d[k]=mapping[d[k]]
encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary)
