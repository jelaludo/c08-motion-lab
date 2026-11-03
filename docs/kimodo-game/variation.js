// Draw only at state entry. A take stays fixed through the current action/loop.
// A shuffle bag covers the eligible pool and avoids consecutive repeats.
export function createVariationPicker(random=()=>Math.random()){
 const bags=new Map(),last=new Map();let draws=0;
 return {pick(key,candidates){
  if(!candidates.length)return null;
  const signature=candidates.map(t=>t.id).sort().join('|');let bag=bags.get(key);
  if(!bag||bag.signature!==signature||!bag.ids.length){
   const ids=candidates.map(t=>t.id);for(let i=ids.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[ids[i],ids[j]]=[ids[j],ids[i]]}
   if(ids.length>1&&ids.at(-1)===last.get(key)){const j=Math.floor(random()*(ids.length-1));[ids[j],ids[ids.length-1]]=[ids.at(-1),ids[j]]}
   bag={signature,ids};bags.set(key,bag);
  }
  const id=bag.ids.pop();last.set(key,id);draws++;return {take:candidates.find(t=>t.id===id),draw:draws,pool:candidates.map(t=>t.id)};
 },get draws(){return draws}};
}
