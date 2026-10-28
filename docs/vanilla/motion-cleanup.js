// Conservative offline curve filtering. Original source clips remain untouched.
export function smoothClip(clip, radius=3, loop=false){
 if(!radius)return clip;
 for(const track of clip.tracks){
  const width=track.getValueSize(),count=track.times.length,source=track.values.slice(),quaternion=track.name.endsWith('.quaternion'),unique=loop?count-1:count;
  for(let i=0;i<count;i++){
   const sum=new Array(width).fill(0);let weight=0;
   for(let offset=-radius;offset<=radius;offset++){
    let index=i+offset;if(loop)index=((index%unique)+unique)%unique;else index=Math.max(0,Math.min(count-1,index));
    const w=Math.exp(-.5*(offset/(radius*.55))**2);let sign=1;
    if(quaternion){let dot=0;for(let k=0;k<4;k++)dot+=source[index*width+k]*source[Math.min(i,unique-1)*width+k];if(dot<0)sign=-1}
    for(let k=0;k<width;k++)sum[k]+=source[index*width+k]*w*sign;weight+=w;
   }
   const divisor=quaternion?Math.hypot(...sum):weight;for(let k=0;k<width;k++)track.values[i*width+k]=sum[k]/divisor;
  }
 }
 return clip;
}

