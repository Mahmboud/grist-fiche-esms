(function(root){'use strict';
const SCHEMA=1,ORIGIN='https://mahmboud.github.io',BASE='/grist-fiche-esms/dev/public-data-v1/';
const SOURCES=['structures','activites','nomenclatures','has-essms','has-sanitaire','ror','sae','cnsa'];
const names={'structures':'FINESS+ Structures','activites':'FINESS+ Activités','nomenclatures':'Nomenclatures ANS','has-essms':'HAS ESSMS','has-sanitaire':'HAS sanitaire','ror':'ROR','sae':'SAE DREES','cnsa':'CNSA EHPAD'};
const rowArray=d=>Array.isArray(d)?d:(d.id||[]).map((_,i)=>Object.fromEntries(Object.entries(d).map(([k,v])=>[k,v[i]])));
const stable=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const norm=v=>{let s=String(v||'').toUpperCase().replace(/[\s.\-]/g,'');if(/^\d{8}$/.test(s))s='0'+s;return /^[0-9][0-9A-Z][0-9]{7}$/.test(s)&&s!=='000000000'?s:''};
function legal(v){if(Array.isArray(v))return v.filter(x=>x!=='L').map(norm).filter(Boolean);const s=String(v||'');return norm(s)?[norm(s)]:[...s.matchAll(/(?<![0-9A-Z])[0-9](?:[\s.-]*[0-9A-Z])(?:[\s.-]*[0-9]){7}(?![0-9A-Z])/gi)].map(x=>norm(x[0])).filter(Boolean)}
function validate(pack){
 if(pack?.schemaVersion!==SCHEMA||!Array.isArray(pack.structures)||!Array.isArray(pack.facts)||!Array.isArray(pack.sources)||!Array.isArray(pack.nomenclatures)||!Array.isArray(pack.legalKeys))throw Error('Format de données inconnu.');
 if(!Number.isFinite(Date.parse(pack.preparedAt))||Date.parse(pack.preparedAt)>Date.now()+3600000)throw Error('Date de préparation invalide.');
 if(Date.now()-Date.parse(pack.preparedAt)>7*86400000)throw Error('Extraction préparée depuis plus de 7 jours. Actualisation refusée ; les données actuelles sont conservées.');
 if(pack.structures.length<200||pack.structures.length>10000||pack.facts.length>50000||pack.nomenclatures.length>20000)throw Error('Volume de données inattendu.');
 const src=new Map(pack.sources.map(s=>[s.id,s]));
 if(src.size!==SOURCES.length||SOURCES.some(k=>!src.has(k)))throw Error('Liste de sources incomplète.');
 for(const k of ['structures','activites','nomenclatures'])if(src.get(k)?.status!=='ok')throw Error('Socle FINESS incomplet : '+names[k]);
 const seen=new Set();for(const r of pack.structures){if(!norm(r.FINESS)||r.FINESS!==norm(r.FINESS)||!pack.legalKeys.includes(r.FINESS_JURIDIQUE)||seen.has(r.FINESS)||typeof r.RAISON_SOCIALE!=='string'||!Array.isArray(r.CAPACITES))throw Error('Établissement invalide ou doublonné.');seen.add(r.FINESS)}
 const facts=new Set();for(const f of pack.facts){const k=f.source+':'+f.FINESS;if(!SOURCES.includes(f.source)||f.source==='structures'||f.source==='nomenclatures'||!seen.has(f.FINESS)||facts.has(k)||!f.data||typeof f.data!=='object')throw Error('Donnée complémentaire invalide.');facts.add(k)}
 const nk=new Set();for(const n of pack.nomenclatures){if(typeof n.CLE!=='string'||nk.has(n.CLE)||typeof n.CODE!=='string'||typeof n.LIBELLE!=='string')throw Error('Nomenclature invalide.');nk.add(n.CLE)}
 return pack;
}
function upsert(table,key,incoming,existing){
 const index=new Map();for(const r of existing){if(index.has(r[key]))throw Error('Clé dupliquée dans '+table);index.set(r[key],r)}
 let next=Math.max(0,...existing.map(r=>r.id))+1;const actions=[],before=[],changes={ajouts:0,modifications:0};
 for(const item of incoming){const old=index.get(item[key]);if(old){const diff=Object.fromEntries(Object.entries(item).filter(([k,v])=>stable(old[k])!==stable(v)));if(Object.keys(diff).length){actions.push(['UpdateRecord',table,old.id,diff]);before.push(['UpdateRecord',table,old.id,Object.fromEntries(Object.keys(diff).map(k=>[k,old[k]??null]))]);changes.modifications++}}
 else{const id=next++;actions.push(['AddRecord',table,id,item]);before.push(['RemoveRecord',table,id]);changes.ajouts++}}
 return {actions,before,changes};
}
function plan(pack,state,snapshot){
 validate(pack);const map=new Map();for(const u of state.UGECAM){for(const k of legal(u.FINESS_JURIDIQUES||u.FINESS_Juridique)){if(map.has(k))throw Error('FINESS juridique associé à plusieurs UGECAM : '+k);map.set(k,u.id)}}
 const missing=[...map.keys()].filter(k=>!pack.legalKeys.includes(k));if(missing.length)throw Error('Périmètre du flux à compléter pour : '+missing.join(', '));
 const structures=pack.structures.filter(r=>map.has(r.FINESS_JURIDIQUE)),by=new Map(structures.map(r=>[r.FINESS,r]));
 for(const old of state.FINESS_CATALOGUE){const current=by.get(old.FINESS);if(current&&(+old.UGECAM!==+map.get(current.FINESS_JURIDIQUE)||norm(old.FINESS_JURIDIQUE)!==current.FINESS_JURIDIQUE))throw Error('Rattachement juridique modifié pour '+old.FINESS+' : arbitrage propriétaire nécessaire avant actualisation.');}
 const okay=new Set(pack.sources.filter(s=>s.status==='ok').map(s=>s.id)),stamp=pack.preparedAt;
 const facts=[...structures.map(r=>({source:'structures',FINESS:r.FINESS,data:r,summary:r.RAISON_SOCIALE,sourceDate:pack.sources.find(s=>s.id==='structures').sourceDate,sourceUrl:pack.sources.find(s=>s.id==='structures').sourceUrl})),...pack.facts.filter(f=>by.has(f.FINESS)&&okay.has(f.source))].map(f=>({CLE:f.source+':'+f.FINESS,SOURCE:f.source,FINESS:f.FINESS,FINESS_JURIDIQUE:by.get(f.FINESS).FINESS_JURIDIQUE,UGECAM:map.get(by.get(f.FINESS).FINESS_JURIDIQUE),DONNEES_JSON:JSON.stringify(f.data),RESUME:f.summary||'',DATE_SOURCE:f.sourceDate||'',SOURCE_URL:f.sourceUrl||'',DATE_EXTRACTION:stamp,PRESENT_SOURCE:true}));
 const factKeys=new Set(facts.map(f=>f.CLE));for(const old of state.DONNEES_PUBLIQUES)if(okay.has(old.SOURCE)&&map.has(old.FINESS_JURIDIQUE)&&!factKeys.has(old.CLE))facts.push({CLE:old.CLE,PRESENT_SOURCE:false,DATE_EXTRACTION:stamp});
 const existingFin=new Set(state.FINESS_CATALOGUE.map(r=>r.FINESS));
 const catalogue=structures.filter(r=>!existingFin.has(r.FINESS)).map(r=>({FINESS:r.FINESS,FINESS_JURIDIQUE:r.FINESS_JURIDIQUE,UGECAM:map.get(r.FINESS_JURIDIQUE),RAISON_SOCIALE:r.RAISON_SOCIALE,RAISON_SOCIALE_LONGUE:r.RAISON_SOCIALE_LONGUE,CATEGORIE_CODE:r.CATEGORIE_CODE,CATEGORIE:r.CATEGORIE,ADRESSE:r.ADRESSE,TELEPHONE:r.TELEPHONE,SIRET:r.SIRET,DATE_OUVERTURE:r.DATE_OUVERTURE,DATE_AUTORISATION:r.DATE_AUTORISATION,DATE_MAJ_SOURCE:r.DATE_MAJ_SOURCE,MILLESIME_ETAB:stamp.slice(0,10),SOURCE_ETAB_URL:pack.sources.find(s=>s.id==='structures').sourceUrl,PRESENT_SOURCE:true,IMPORT_LE:stamp}));
 const refs=pack.nomenclatures.map(n=>Object.fromEntries(['CLE','CODE','LIBELLE','DOMAINE','PARENT','STATUT','VERSION','SOURCE_URL','DATE_SOURCE'].map(k=>[k,n[k]||''])));
 const src=pack.sources.map(s=>({SOURCE:s.id,LIBELLE:names[s.id],STATUT:s.status,DATE_SOURCE:s.sourceDate||'',DATE_VERIFICATION:s.checkedAt||'',DATE_EXTRACTION:stamp,URL:s.sourceUrl||'',SHA256:s.sha256||'',NB_FINESS:s.count||0,AVERTISSEMENT:[s.warning,s.error].filter(Boolean).join('\n')}));
 const parts=[upsert('FINESS_CATALOGUE','FINESS',catalogue,state.FINESS_CATALOGUE),upsert('DONNEES_PUBLIQUES','CLE',facts,state.DONNEES_PUBLIQUES),upsert('REFERENTIEL_FINESS','CLE',refs,state.REFERENTIEL_FINESS),upsert('SOURCES_PUBLIQUES','SOURCE',src,state.SOURCES_PUBLIQUES)];
 const actions=parts.flatMap(p=>p.actions),before=parts.flatMap(p=>p.before).reverse();
 const summary={nouveaux_finess:parts[0].changes.ajouts,donnees:parts[1].changes,referentiels:parts[2].changes,sources_conservees:pack.sources.filter(s=>s.status!=='ok').map(s=>s.id),structures_actives:structures.filter(s=>s.ETAT==='A'&&!s.DATE_FERMETURE).length,structures_totales:structures.length};
 if(!actions.length)return {actions:[],summary,before:[]};
 const journal={DATE:new Date().toISOString(),SNAPSHOT:snapshot,STATUT:'Terminé',BILAN_JSON:JSON.stringify(summary),RESTAURATION_JSON:JSON.stringify(before)};actions.push(['AddRecord','ACTUALISATIONS_PUBLIQUES',null,journal]);
 return {actions,before,summary};
}
const TABLES=['UGECAM','FINESS_CATALOGUE','DONNEES_PUBLIQUES','REFERENTIEL_FINESS','SOURCES_PUBLIQUES'];
async function read(api){return Object.fromEntries(await Promise.all(TABLES.map(async t=>[t,rowArray(await api.fetchTable(t))])))}
async function digest(b){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('')}
async function get(url){const c=new AbortController(),timer=setTimeout(()=>c.abort(),90000);try{const r=await fetch(url,{cache:'no-store',signal:c.signal,credentials:'omit',referrerPolicy:'no-referrer'});if(!r.ok)throw Error('Source indisponible (HTTP '+r.status+').');return await r.arrayBuffer()}finally{clearTimeout(timer)}}
async function download(){const u=new URL(BASE+'latest.json',ORIGIN);u.searchParams.set('t',Date.now());const pointer=JSON.parse(new TextDecoder().decode(await get(u)));if(pointer.schemaVersion!==SCHEMA||!/^snapshots\/[a-f0-9]{64}\.json\.gz$/.test(pointer.file)||!Number.isInteger(pointer.bytes)||pointer.bytes>15*1024*1024||!Number.isInteger(pointer.uncompressedBytes)||pointer.uncompressedBytes>40*1024*1024)throw Error('Index du flux invalide.');const b=await get(new URL(BASE+pointer.file,ORIGIN));if(b.byteLength!==pointer.bytes||await digest(b)!==pointer.sha256)throw Error('Intégrité de l’extraction incorrecte. Aucun import.');if(typeof DecompressionStream==='undefined')throw Error('Votre navigateur doit prendre en charge la décompression gzip.');const raw=await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();if(raw.byteLength!==pointer.uncompressedBytes)throw Error('Taille décompressée incorrecte.');const pack=validate(JSON.parse(new TextDecoder().decode(raw)));if(pack.preparedAt!==pointer.preparedAt)throw Error('Dates du flux incohérentes.');return {pack,hash:pointer.sha256}}
let busy=false;
async function sync(api,progress=()=>{}){
 if(busy)throw Error('Une actualisation est déjà en cours.');busy=true;
 try{const admin=rowArray(await api.fetchTable('ADMIN_OUTILS'));if(!admin.length)throw Error('Actualisation réservée aux propriétaires.');progress('Téléchargement de l’extraction publique contrôlée…');const {pack,hash}=await download();const previous=rowArray(await api.fetchTable('ACTUALISATIONS_PUBLIQUES'));if(previous.some(r=>r.SNAPSHOT===hash&&r.STATUT==='Terminé'))return {identical:true,preparedAt:pack.preparedAt};progress('Contrôle des FINESS et préparation de la transaction…');const state=await read(api),p=plan(pack,state,hash);const current=await read(api);if(stable(current)!==stable(state))throw Error('Les données ont changé pendant le contrôle. Relancez l’actualisation.');if(p.actions.length){progress('Enregistrement des données publiques et du journal…');await api.applyUserActions(p.actions)}return {...p.summary,preparedAt:pack.preparedAt,sources:pack.sources};}finally{busy=false}
}
const api={validate,plan,upsert,norm,legal,rowArray,stable,sync,download,names,TABLES};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.MoadPublicSync=api;
})(typeof globalThis!=='undefined'?globalThis:this);
