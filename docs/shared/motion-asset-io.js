// Content-addressed static playback assets. No inference service or credentials.
import * as T from 'three';
const buffers=new Map();
export async function assetBytes(value){
 const url=new URL(value,location.href).href;
 if(!buffers.has(url))buffers.set(url,(async()=>{
  const r=await fetch(url);if(!r.ok)throw Error('Motion asset returned '+r.status);const bytes=new Uint8Array(await r.arrayBuffer());
  const expected=new URL(url).pathname.match(/\/([a-f0-9]{64})\.(?:glb|json(?:\.gz)?)$/)?.[1];
  if(expected&&globalThis.crypto?.subtle){const actual=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');if(actual!==expected)throw Error('Motion asset integrity mismatch')}
  return bytes;
 })().catch(e=>{buffers.delete(url);throw e}));
 return buffers.get(url);
}
export async function readMotionJSON(value){
 const bytes=await assetBytes(value);let decoded=bytes;
 if(bytes[0]===0x1f&&bytes[1]===0x8b){if(!globalThis.DecompressionStream)throw Error('This player requires browser gzip decompression support.');decoded=new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer())}
 return JSON.parse(new TextDecoder().decode(decoded));
}
export async function loadMotionModel(loader,value){const bytes=await assetBytes(value);return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')}
export async function loadPublishedAsset(loader,output,assetURL){
 const gltf=await loadMotionModel(loader,assetURL(output.model));if(output.animation)gltf.animations=[T.AnimationClip.parse(await readMotionJSON(assetURL(output.animation)))];return gltf;
}
export async function loadPublishedClip(output,assetURL){return T.AnimationClip.parse(await readMotionJSON(assetURL(output.animation)))}
