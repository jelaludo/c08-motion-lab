import * as T from 'three';
export function obstacleCorners(ob){const base=ob.base_z??ob.base_y??0,dx=ob.shape==='box'?ob.depth/2:ob.radius,dy=ob.shape==='box'?ob.width/2:ob.radius;const result=[];for(const x of [-1,1])for(const y of [-1,1])for(const z of [base,base+ob.height])result.push([ob.center[0]+x*dx,ob.center[1]+y*dy,z]);return result;}
export function createObstacleMesh(ep,ob,scale){
 const b=ep.display.display_basis,matrix=new T.Matrix4().set(b[0][0],b[0][1],b[0][2],0,b[1][0],b[1][1],b[1][2],0,b[2][0],b[2][1],b[2][2],0,0,0,0,1),base=ob.base_z??ob.base_y??0;
 let geometry;if(ob.shape==='box'){if(![ob.depth,ob.width,ob.height].every(x=>Number.isFinite(x)&&x>0))throw Error('An obstacle box has invalid native dimensions.');geometry=new T.BoxGeometry(ob.depth*scale,ob.width*scale,ob.height*scale)}else{if(![ob.radius,ob.height].every(x=>Number.isFinite(x)&&x>0))throw Error('An obstacle pillar has invalid native dimensions.');geometry=new T.CylinderGeometry(ob.radius*scale,ob.radius*scale,ob.height*scale,24);geometry.rotateX(Math.PI/2)}geometry.applyMatrix4(matrix);
 const color=ob.kind==='hurdle'?'#9e7e58':ob.kind==='overhead'?'#6f9fa8':'#a7aa87',mesh=new T.Mesh(geometry,new T.MeshStandardMaterial({color,roughness:.85}));
 const xyz=[...ob.center,base+ob.height/2];mesh.position.set(...b.map((row,i)=>(row.reduce((s,v,j)=>s+v*xyz[j],0)-ep.display.display_origin[i])*scale));mesh.name='obstacle-'+(ob.kind||ob.shape||'pillar');mesh.userData={nativeObstacle:ob,baseColor:color};return mesh;
}
