import * as T from 'three';
export function createWorld(scene){
 const obstacles=[],markers=[],props=[];
 const mat=(color,extra={})=>new T.MeshStandardMaterial({color,roughness:.83,...extra});
 const ground=new T.Mesh(new T.PlaneGeometry(220,260),mat('#263f3c'));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
 const grid=new T.GridHelper(220,220,0x537269,0x304e47);grid.position.y=.006;scene.add(grid);
 function box(name,x,z,w,d,h,color,bottom=0,solid=true){const m=new T.Mesh(new T.BoxGeometry(w,h,d),mat(color));m.position.set(x,bottom+h/2,z);m.castShadow=true;m.receiveShadow=true;scene.add(m);if(solid)obstacles.push({name,x,z,w,d,bottom,top:bottom+h,mesh:m});return m}
 function label(text,x,z,color='#c2e6d2',y=.035,size=1){const c=document.createElement('canvas');c.width=1024;c.height=128;const ctx=c.getContext('2d');ctx.fillStyle=color;ctx.font='600 48px system-ui';ctx.textAlign='center';ctx.fillText(text,512,80);const tex=new T.CanvasTexture(c),m=new T.Mesh(new T.PlaneGeometry(13*size,1.6*size),new T.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false}));m.rotation.set(-Math.PI/2,0,Math.PI);m.position.set(x,y,z);scene.add(m);markers.push(m)}
 function lane(name,x,z,w,d,color){box(name,x,z,w,d,.012,color,0,false);label(name,x,z- d/2+1.5);}
 lane('01 WALK / JOG',0,10,7,18,'#2f6354');lane('02 RUN / ORANGE',0,31,7,24,'#9b5c2f');lane('03 SPRINT / RED',0,55,7,24,'#8a393a');
 label('JUMP + CROUCH COURSE',12,5);box('low jump',12,18,7,.65,.42,'#b89654');box('medium jump',12,48,7,.65,.64,'#b89654');
 box('crouch tunnel roof',12,33,6,8,.25,'#587f94',1.4);box('tunnel left',8.85,33,.3,8,1.65,'#587f94');box('tunnel right',15.15,33,.3,8,1.65,'#587f94');
 for(const [x,z]of [[-17,26],[-23,35],[-17,44],[26,23],[31,39],[25,58]])box('solid wall',x,z,4,2,2.4,'#526970');
 label('BOX YARD',-12,0);for(let i=0;i<3;i++)box('stacked freight',-18-i*1.6,6,1.2,1.2,1.2+(i%2)*1.2,'#747663');
 const makeCrate=()=>{const m=new T.Mesh(new T.BoxGeometry(.58,.46,.5),mat('#d5aa69'));m.castShadow=true;const edges=new T.LineSegments(new T.EdgesGeometry(m.geometry),new T.LineBasicMaterial({color:0x54402a}));m.add(edges);return m};
 const crate=makeCrate();crate.position.set(-2,.23,2);scene.add(crate);props.push(crate);
 const ghostCrate=makeCrate();ghostCrate.visible=false;scene.add(ghostCrate);
 const bench=box('bench seat',-8,14,3,.8,.18,'#7f8673',.48);for(const x of [-9,-7])box('bench leg',x,14,.15,.65,.48,'#4b5e5b');
 const terminal=box('terminal',-8,20,1,.6,1.1,'#516a7a');box('screen',-8,19.67,.7,.03,.45,'#60bfa9',.6,false);
 label('INTERACTION',-8,23);label('START',0,-2);
 for(const [x,z,w,d]of [[0,-15,100,1],[0,95,100,1],[-50,40,1,110],[50,40,1,110]])box('boundary',x,z,w,d,2.5,'#3a5556');
 const state={collisions:0,lastCollision:null};
 function intersects(x,z,r,b){return Math.hypot(x-T.MathUtils.clamp(x,b.x-b.w/2,b.x+b.w/2),z-T.MathUtils.clamp(z,b.z-b.d/2,b.z+b.d/2))<r-1e-6}
 function fits(pos,height,r=.27){return !obstacles.some(b=>pos.y+.04<b.top&&pos.y+height>b.bottom+.01&&intersects(pos.x,pos.z,r,b))}
 function move(pos,delta,height,r=.27){const n=Math.max(1,Math.ceil(delta.length()/.08)),step=delta.clone().multiplyScalar(1/n),out=pos.clone();for(let i=0;i<n;i++){
  for(const axis of ['x','z']){const candidate=out.clone();candidate[axis]+=step[axis];const hit=obstacles.find(b=>candidate.y+.04<b.top&&candidate.y+height>b.bottom+.01&&intersects(candidate.x,candidate.z,r,b));if(!hit)out[axis]=candidate[axis];else{state.collisions++;state.lastCollision=hit.name}}
 }return out}
 function floor(x,z,y=0){let top=0;for(const b of obstacles)if(b.top<=y+.06&&Math.abs(x-b.x)<b.w/2+.1&&Math.abs(z-b.z)<b.d/2+.1)top=Math.max(top,b.top);return top}
 return {obstacles,props,crate,ghostCrate,bench,terminal,makeCrate,state,move,fits,floor,zone(pos){return Math.abs(pos.x)<=3.5&&pos.z>=19&&pos.z<=43?'orange':Math.abs(pos.x)<=3.5&&pos.z>43&&pos.z<=67?'red':'free'},reset(){crate.position.set(-2,.23,2);crate.rotation.set(0,0,0);state.collisions=0;state.lastCollision=null}};
}
