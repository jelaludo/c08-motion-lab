import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
// Three r160 can leak its texture.channel bookkeeping into TextureInfo. glTF
// uses texCoord for UV selection. Keep binary image/geometry chunks untouched.
export async function normalizedGLB(root,options){
 const bytes=await new GLTFExporter().parseAsync(root,options);if(!(bytes instanceof ArrayBuffer))return bytes;
 const view=new DataView(bytes),length=view.getUint32(12,true),document=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,length)));let changed=false;
 function visit(value){if(!value||typeof value!=='object')return;if(Object.hasOwn(value,'index')&&Object.hasOwn(value,'channel')){if(value.texCoord===undefined&&value.channel!==0)value.texCoord=value.channel;delete value.channel;changed=true}for(const child of Object.values(value))visit(child)}
 for(const material of document.materials||[])visit(material);if(!changed)return bytes;
 const json=new TextEncoder().encode(JSON.stringify(document)),padded=Math.ceil(json.length/4)*4,tail=new Uint8Array(bytes,20+length),out=new Uint8Array(20+padded+tail.length),header=new DataView(out.buffer);
 header.setUint32(0,0x46546c67,true);header.setUint32(4,2,true);header.setUint32(8,out.length,true);header.setUint32(12,padded,true);header.setUint32(16,0x4e4f534a,true);out.fill(0x20,20,20+padded);out.set(json,20);out.set(tail,20+padded);return out.buffer;
}
