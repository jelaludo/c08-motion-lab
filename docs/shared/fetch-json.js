/** Read regular JSON or an explicitly gzip-compressed JSON artifact.
 * Browsers may transparently decode HTTP Content-Encoding, so inspect the bytes
 * instead of assuming that every .gz response still needs decompression.
 */
export async function fetchJSON(input,{cache='no-cache',fallbackURL}={}){
 const url=String(input),response=await fetch(url,{cache});
 if(!response.ok)throw Error(`Unable to load take data (${response.status}): ${url}`);
 const bytes=new Uint8Array(await response.arrayBuffer());
 if(bytes[0]===0x1f&&bytes[1]===0x8b){
  if(typeof DecompressionStream==='function'){
   const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
   try{return JSON.parse(await new Response(stream).text())}catch(e){throw Error(`Compressed take data could not be decoded: ${url}. ${e.message}`)}
  }
  const plain=fallbackURL||url.replace(/\.json\.gz(?=([?#]|$))/i,'.json');
  if(plain!==url){const fallback=await fetch(plain,{cache});if(fallback.ok)return fallback.json()}
  throw Error('This browser cannot decompress the recorded take data, and no uncompressed copy is available. Open the lab in a current Chrome, Edge, Firefox or Safari browser.');
 }
 try{return JSON.parse(new TextDecoder().decode(bytes))}catch(e){throw Error(`Take data is not valid JSON: ${url}. ${e.message}`)}
}
