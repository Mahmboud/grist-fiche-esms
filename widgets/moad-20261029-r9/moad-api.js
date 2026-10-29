(function(root){'use strict';
const tables={SITES:'GristHidden_SITES',UGECAM:'GristHidden_UGECAM',PROFIL_SESSION:'GristHidden_PROFIL_SESSION',Autodiagnostic_DEV:'Autodiagnostic',Autodiagnostic_Historique_DEV:'Autodiagnostic_Historique',ARBORESCENCE_AIRMES_DEV:'ARBORESCENCE_AIRMES'};
const table=t=>tables[t]||t;
const projection={GristHidden_SITES:'PORTAIL_SITES_JSON',GristHidden_UGECAM:'PORTAIL_UGECAM_JSON',GristHidden_PROFIL_SESSION:'PORTAIL_PROFIL_JSON'};
let directoryCache=null,directoryTime=0,requestCache=null,requestTime=0;
async function directory(){if(!directoryCache||Date.now()-directoryTime>1000){directoryTime=Date.now();directoryCache=(async()=>{const gate=rows(await grist.docApi.fetchTable('FINESS_ACCES_PAGE'));if(!gate.length)throw Error('Accès réservé aux profils validés.');const bytes=Uint8Array.from(atob(gate[0].ANNUAIRE_GZIP||''),c=>c.charCodeAt(0));const plain=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();return JSON.parse(plain)})().catch(e=>{directoryCache=null;throw e})}return directoryCache}
function requests(){if(!requestCache||Date.now()-requestTime>1000){requestTime=Date.now();requestCache=grist.docApi.fetchTable('DEMANDES_ACCES').then(rows).catch(e=>{requestCache=null;throw e})}return requestCache}
const rows=d=>(d.id||[]).map((_,i)=>Object.fromEntries(Object.entries(d).map(([k,v])=>[k,v[i]])));
function columns(rr){const keys=[...new Set(['id',...rr.flatMap(r=>Object.keys(r))])];return Object.fromEntries(keys.map(k=>[k,rr.map(r=>r[k])]))}
async function fetchTable(t){const actual=table(t);if(!projection[actual]&&!['ESMS','FINESS_CATALOGUE','DONNEES_PUBLIQUES','ARBO_ESMS_REFERENCES','ARBORESCENCE_AIRMES'].includes(actual))return grist.docApi.fetchTable(actual);
 try{const direct=await grist.docApi.fetchTable(actual);if(direct.id?.length)return direct}catch{}
 if(!projection[actual]){const all=await directory();return columns(all[actual]||[])}
 const reqs=await requests();
 const own=reqs.find(r=>r.STATUT==='Validé')||reqs.find(r=>r.EMAIL)||reqs.find(r=>r.STATUT==='Référentiel inscription');
 const rr=JSON.parse(own?.[projection[actual]]||'[]');if(!Array.isArray(rr))throw Error('Référentiel indisponible');return columns(rr);
}
root.moadApi={fetchTable,applyUserActions:(aa,options)=>{directoryCache=null;requestCache=null;return grist.docApi.applyUserActions(aa.map(a=>{const copy=[...a];if(typeof copy[1]==='string')copy[1]=table(copy[1]);return copy}),options)},listTables:async()=>{const actual=await grist.docApi.listTables();return [...new Set([...actual,...Object.keys(tables).filter(k=>actual.includes(tables[k]))])]},getAccessToken:o=>grist.docApi.getAccessToken(o)};
})(globalThis);
