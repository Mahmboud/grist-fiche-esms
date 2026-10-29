import pathlib,shutil,re
root=pathlib.Path(__file__).resolve().parents[1];src=root/'widgets/moad-20261029-r6';out=root/'widgets/moad-20261029-r7';out.mkdir(exist_ok=True)
for p in src.iterdir():
 if p.is_file():
  s=p.read_text().replace('/moad-20261029-r6/','/moad-20261029-r7/')
  # Local immutable dependency, independently verified as an exact URL.
  s=re.sub(r'https://mahmboud.github.io/grist-fiche-esms/dev/moad-airmes-20261028/target/moad-ref-config.js\?v=1','moad-ref-config.js',s)
  if p.name=='sites-esms.html':
   start='${services(s.id).map(e=>`<button class="entity ${S.entity===e.id?\'active\':\'\'}" data-esms="${e.id}">${esc(e.RAISON_SOCIALE)}</button>`).join(\'\')}'
   assert start in s;s=s.replace(start,'')
  if p.name=='autodiagnostic-questionnaire.html':s=s.replace("await ft('ADMIN_OUTILS');state.isOwner=true","state.isOwner=(await ft('ADMIN_OUTILS')).length>0")
  (out/p.name).write_text(s)
api=(out/'moad-api.js').read_text()
api=api.replace("const table=t=>tables[t]||t;",'''const table=t=>tables[t]||t;
const projection={GristHidden_SITES:'PORTAIL_SITES_JSON',GristHidden_UGECAM:'PORTAIL_UGECAM_JSON',GristHidden_PROFIL_SESSION:'PORTAIL_PROFIL_JSON'};
let directoryCache=null,directoryTime=0,requestCache=null,requestTime=0;\nasync function directory(){if(!directoryCache||Date.now()-directoryTime>1000){directoryTime=Date.now();directoryCache=(async()=>{const gate=rows(await grist.docApi.fetchTable('FINESS_ACCES_PAGE'));if(!gate.length)throw Error('Accès réservé aux profils validés.');const bytes=Uint8Array.from(atob(gate[0].ANNUAIRE_GZIP||''),c=>c.charCodeAt(0));const plain=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();return JSON.parse(plain)})().catch(e=>{directoryCache=null;throw e})}return directoryCache}\nfunction requests(){if(!requestCache||Date.now()-requestTime>1000){requestTime=Date.now();requestCache=grist.docApi.fetchTable('DEMANDES_ACCES').then(rows).catch(e=>{requestCache=null;throw e})}return requestCache}\nconst rows=d=>(d.id||[]).map((_,i)=>Object.fromEntries(Object.entries(d).map(([k,v])=>[k,v[i]])));
function columns(rr){const keys=[...new Set(['id',...rr.flatMap(r=>Object.keys(r))])];return Object.fromEntries(keys.map(k=>[k,rr.map(r=>r[k])]))}
async function fetchTable(t){const actual=table(t);if(!projection[actual]&&!['ESMS','FINESS_CATALOGUE','DONNEES_PUBLIQUES','ARBO_ESMS_REFERENCES','ARBORESCENCE_AIRMES'].includes(actual))return grist.docApi.fetchTable(actual);
 try{const direct=await grist.docApi.fetchTable(actual);if(direct.id?.length)return direct}catch{}
 if(!projection[actual]){const all=await directory();return columns(all[actual]||[])}\n const requests=rows(await grist.docApi.fetchTable('DEMANDES_ACCES'));
 const own=requests.find(r=>r.STATUT==='Validé')||reqs.find(r=>r.EMAIL)||reqs.find(r=>r.STATUT==='Référentiel inscription');
 const rr=JSON.parse(own?.[projection[actual]]||'[]');if(!Array.isArray(rr))throw Error('Référentiel indisponible');return columns(rr);
}''')
api=api.replace('fetchTable:t=>grist.docApi.fetchTable(table(t))','fetchTable')
api=api.replace("const requests=rows(await grist.docApi.fetchTable('DEMANDES_ACCES'));","const reqs=await requests();").replace("const own=requests.find","const own=reqs.find")
api=api.replace('applyUserActions:(aa,options)=>grist.docApi.applyUserActions(', 'applyUserActions:(aa,options)=>{directoryCache=null;requestCache=null;return grist.docApi.applyUserActions(').replace('return copy}),options),listTables:', 'return copy}),options)},listTables:')
(out/'moad-api.js').write_text(api)
print(out)
