import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
const stage=document.getElementById('hero-stage');
try{
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.7));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;stage.prepend(renderer.domElement);
const scene=new T.Scene();scene.background=new T.Color('#c6d1bc');const camera=new T.OrthographicCamera(-2,2,2,-2,.05,60);camera.position.set(3.5,2.7,5.8);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(.3,1.1,0);orbit.enableDamping=true;orbit.enableZoom=false;orbit.enablePan=false;orbit.minPolarAngle=.7;orbit.maxPolarAngle=1.5;orbit.update();
const room=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();scene.add(new T.HemisphereLight(0xf3f2df,0x5a7266,2.2));
const sun=new T.DirectionalLight(0xffe7bf,3);sun.position.set(-3,6,5);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-4,right:4,top:4,bottom:-4,near:.1,far:20});sun.shadow.normalBias=.002;scene.add(sun);
const base=new T.Mesh(new T.CylinderGeometry(2.3,2.3,.12,96),new T.MeshStandardMaterial({color:'#90a788',roughness:.9}));base.position.y=-.065;base.receiveShadow=true;scene.add(base);
const circle=new T.Mesh(new T.RingGeometry(1.85,1.862,100),new T.MeshBasicMaterial({color:'#c0ceb2',side:T.DoubleSide}));circle.rotation.x=-Math.PI/2;circle.position.y=.001;scene.add(circle);
const loader=new GLTFLoader();const [robot,cat]=await Promise.all([loader.loadAsync('assets/c08_d0_lod1.glb'),loader.loadAsync('assets/k0_tech_01_d0_lod1.glb')]);robot.scene.position.x=-.25;cat.scene.position.set(.95,.01,.6);cat.scene.rotation.y=-.4;scene.add(robot.scene,cat.scene);
for(const g of [robot,cat])g.scene.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.frustumCulled=false}});
const robotMixer=new T.AnimationMixer(robot.scene),catMixer=new T.AnimationMixer(cat.scene);const rc=robot.animations.find(a=>a.name==='Standby_Idle')||robot.animations[0],cc=cat.animations.find(a=>/idle/i.test(a.name))||cat.animations[0];robotMixer.clipAction(rc).play();catMixer.clipAction(cc).play();
function resize(){const ratio=stage.clientWidth/stage.clientHeight,h=3.4;camera.left=-h*ratio/2;camera.right=h*ratio/2;camera.top=h/2;camera.bottom=-h/2;camera.updateProjectionMatrix();renderer.setSize(stage.clientWidth,stage.clientHeight)}new ResizeObserver(resize).observe(stage);resize();
document.getElementById('hero-loading').hidden=true;window.labHome={scene,renderer,camera,robot,cat};const reduced=matchMedia('(prefers-reduced-motion: reduce)');let previous=performance.now();renderer.setAnimationLoop(now=>{const dt=Math.min(.05,(now-previous)/1000);previous=now;if(!reduced.matches&&!document.hidden){robotMixer.update(dt);catMixer.update(dt)}orbit.update();renderer.render(scene,camera)});
}catch(error){document.getElementById('hero-loading').textContent='C08 + K0-Tech · explore the experiments below.';console.error(error)}
