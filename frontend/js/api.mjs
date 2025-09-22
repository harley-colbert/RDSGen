export async function apiGet(path){
  const r = await fetch(path, {headers:{'Accept':'application/json'}});
  if(!r.ok) throw new Error(`[GET ${path}] ${r.status} ${await r.text()}`);
  return r.json();
}
export async function apiPost(path, data){
  const r = await fetch(path, {
    method:'POST',
    headers:{'Content-Type':'application/json','Accept':'application/json'},
    body: JSON.stringify(data)
  });
  if(!r.ok) throw new Error(`[POST ${path}] ${r.status} ${await r.text()}`);
  return r.json();
}
