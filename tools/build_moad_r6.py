"""Create a new immutable, clean-label bundle; never edits an earlier URL."""
import pathlib,json,re
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'dev/moad-airmes-20261028/target';OUT=ROOT/'widgets/moad-20261029-r6';OUT.mkdir(parents=True,exist_ok=True)
FILES={'v6-dev5.html':'sites-esms.html','airmes-arborescence-v4-dev.html':'arborescence-airmes.html','contacts-annuaire-v2-dev.html':'contacts.html','autodiagnostic-synthese-v4-dev.html':'autodiagnostic-synthese.html','autodiagnostic-questionnaire-v5-dev.html':'autodiagnostic-questionnaire.html','autodiagnostic-historique-v1-dev.html':'autodiagnostic-historique.html','airmes-synthese-v1-dev.html':'airmes-synthese.html','acces-moad-v3-dev.html':'mon-acces.html','admin-demandes-acces-v1-dev.html':'administration-demandes.html','admin-maintenance-v2-dev.html':'administration-sauvegardes.html','admin-nouveau-referent-v3-dev.html':'administration-referent.html','admin-guide-v1-dev.html':'administration-guide.html','admin-exports-excel-v2-dev.html':'administration-exports.html','liste-finess-v2-dev.html':'liste-finess.html','moad-ref-config-dev.js':'moad-ref-config.js','public-sync-v1-dev.js':'public-sync.js','public-data-ui-v1-dev.js':'public-data-ui.js','finess-ui-v2-dev.js':'finess.js','finess-core-v1-dev.js':'identifiants.js'}
TABLES={'SITES':'GristHidden_SITES','UGECAM':'GristHidden_UGECAM','PROFIL_SESSION':'GristHidden_PROFIL_SESSION','Autodiagnostic_DEV':'Autodiagnostic','Autodiagnostic_Historique_DEV':'Autodiagnostic_Historique','ARBORESCENCE_AIRMES_DEV':'ARBORESCENCE_AIRMES'}
for source,dest in FILES.items():
 s=(SRC/source).read_text()
 for a,b in FILES.items():s=s.replace(a,b)
 for a,b in TABLES.items():
  if a.endswith('_DEV'):s=s.replace(a,b)
 # Keep column names and JSON keys intact. Table aliases are translated only
 # at the API boundary; a global UGECAM replacement would corrupt field names.
 if source.endswith('.html'):
  s=s.replace('<script src="https://docs.getgrist.com/grist-plugin-api.js"></script>','<script src="https://docs.getgrist.com/grist-plugin-api.js"></script><script src="moad-api.js"></script>')
 s=s.replace('grist.docApi.fetchTable(','moadApi.fetchTable(').replace('grist.docApi.applyUserActions(','moadApi.applyUserActions(').replace('grist.docApi.listTables(','moadApi.listTables(').replace('MoadPublicSync.sync(grist.docApi,','MoadPublicSync.sync(moadApi,')
 # Remove only visible environment banners, leaving business explanations intact.
 s=re.sub(r'<div\b[^>]*>DEV\s*·[^<]*</div>','',s)
 s=re.sub(r'<span\b[^>]*class="env"[^>]*>[^<]*</span>','',s)
 s=s.replace('<small>DEV · Validation par le propriétaire</small>','<small>Validation par le propriétaire</small>')
 s=s.replace(' — DEV','').replace('MOAD_DEV_sauvegarde_','MOAD_sauvegarde_')
 s=s.replace('Social et médico-social','Médico-social et social').replace('social et médico-social','médico-social et social')
 if source=='v6-dev5.html':
  s=re.sub(r'\.device-tag\{[^}]*\}\.site-devices\{[^}]*\}','',s)
  s=s.replace("${e.DISPOSITIF?'<span class=\"device-tag\">'+esc(e.DISPOSITIF)+'</span><br>':''}",'')
  s=s.replace('${e.DISPOSITIF?`<p class="device-tag">Dispositif : ${esc(e.DISPOSITIF)}</p>`:\'\'}','')
  s=s.replace('${siteDevices(s)}','')
  s=re.sub(r'function siteDevices\(s\)\{[^\n]*\}\n','',s)
  s=s.replace(',e.DISPOSITIF]',']')
 if source=='public-data-ui-v1-dev.js':
  s=s.replace('function detail(f){','function detail(f,showDispositif=false){')
  s=s.replace("+line('Dispositif',d.DISPOSITIF||'Non renseigné dans la source')", "+(showDispositif?line('Dispositif',d.DISPOSITIF||'Non renseigné dans la source'):'')")
  s=s.replace('function renderEntities(entities){','function renderEntities(entities,showDispositif=false){').replace('${detail(f)}','${detail(f,showDispositif)}')
  s=s.replace('sources}])','sources}],true)')
 if source=='finess-ui-v2-dev.js':
  # Dispositif is kept on the FINESS page, never propagated to ESMS tooltips.
  s=s.replace("${line('Dispositif',r.DISPOSITIF||d.DISPOSITIF||'Non renseigné dans la source')}",'')
 if source=='airmes-synthese-v1-dev.html':
  s='<!doctype html><html lang="fr"><meta charset="utf-8"><title>Arborescence Airmes</title><body><p>Les données sont disponibles dans l’arborescence Airmes.</p></body></html>'
  s=s.replace("'Import_entite_AIRMES'","'ARBORESCENCE_AIRMES'").replace("'ESMS_Liste_UGECAM_'","'ARBO_ESMS_REFERENCES'")
 if source=='autodiagnostic-questionnaire-v5-dev.html':
  s=s.replace("state.isSiege=cs[0].SIEGE===true;","state.actorContact=+cs[0].CONTACT||0;state.isSiege=cs[0].SIEGE===true;")
  s=s.replace('Auteur_contact:+after.Derniere_mise_a_jour_contact||0','Auteur_contact:state.actorContact||0')
 if source=='acces-moad-v3-dev.html':
  s=s.replace("await ft('ADMIN_OUTILS');S.owner=true","S.owner=(await ft('ADMIN_OUTILS')).length>0")
  s=s.replace("const primary=p.value==='SITE'?+s.value:0,scope=", "const primary=p.value==='SITE'?+s.value:0;if(!document.getElementById('nom').value.trim()||!document.getElementById('prenom').value.trim())throw Error('Nom et prénom obligatoires.');if(!S.u.some(x=>+x.id===+u.value)||!S.f.some(x=>+x[0]===+document.getElementById('fonction').value))throw Error('Choisissez une UGECAM et une fonction valides.');if(p.value==='SITE'&&!S.s.some(x=>+x.id===primary&&+x.UGECAM===+u.value))throw Error('Choisissez un site de cette UGECAM.');const scope=")
  s=s.replace("await moadApi.applyUserActions([['AddRecord','DEMANDES_ACCES',null,{", "const payload={")
  s=s.replace("CONTACT:0}]]);S.requests=", "CONTACT:0};if(S.email)payload.EMAIL=S.email;await grist.docApi.applyUserActions([['AddRecord','DEMANDES_ACCES',null,payload]]);S.requests=")
  s=s.replace('const b=document.getElementById(\'submit\'),m=',"const b=document.getElementById('submit');if(S.sending)return;S.sending=true;const m=")
  s=s.replace("m.textContent='Envoi impossible : '+e.message;b.disabled=false}}}","m.textContent='Envoi impossible : '+e.message;b.disabled=false}finally{S.sending=false}}}")
 if source=='admin-demandes-acces-v1-dev.html':
  s=s.replace("if(!cc.length)actions.push", "if(!S.p.some(p=>+p.CONTACT===cid))actions.push")
  s=s.replace("'PROFIL_SESSION',cid,{CONTACT:cid}","'PROFIL_SESSION',Math.max(0,...S.p.map(p=>p.id))+1,{CONTACT:cid}")
  s=s.replace('e:[],u:[]','e:[],u:[],p:[]')
  s=s.replace('[S.r,S.c,S.s,S.e,S.u]=','[S.r,S.c,S.s,S.e,S.u,S.p]=')
  s=s.replace("ft('UGECAM')]);if(render)","ft('UGECAM'),ft('PROFIL_SESSION')]);if(render)")
 if source=='admin-maintenance-v2-dev.html':
  s=s.replace('</head>','<script src="administration-referentiels.js" defer></script></head>')
 s=s.replace('grist.docApi.applyUserActions(','moadApi.applyUserActions(')
 (OUT/dest).write_text(s)
# The old CSV importer is no longer needed: only FINESS identifiers are retained.
(OUT/'identifiants.js').write_text('''(function(root){function norm(v){let s=String(v||'').toUpperCase().replace(/[\\s.\\-]/g,'');if(/^\\d{8}$/.test(s))s='0'+s;return /^[0-9][0-9A-Z][0-9]{7}$/.test(s)&&s!=='000000000'?s:''}function legalKeys(v){const s=String(v||'');if(norm(s))return[norm(s)];return [...s.matchAll(/(?<![0-9A-Z])[0-9](?:[\\s.-]*[0-9A-Z])(?:[\\s.-]*[0-9]){7}(?![0-9A-Z])/gi)].map(x=>norm(x[0])).filter(Boolean)}root.MoadFiness={norm,legalKeys}})(globalThis);''')
(OUT/'manifest.json').write_text(json.dumps(dict(files=FILES,tables=TABLES),ensure_ascii=False,indent=2))
print(json.dumps(dict(files=len(FILES),output=str(OUT))))
