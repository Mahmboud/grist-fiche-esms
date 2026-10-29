"""Public-only UGECAM extracts. Never reads a Grist document or credentials.

National files stay in the ignored cache. Each adapter validates its schema;
failed adapters keep their previous complete extract, explicitly marked stale.
The immutable snapshot is published before its small, mutable latest pointer.
"""
import argparse,collections,csv,datetime,gzip,hashlib,io,json,pathlib,re,sys,urllib.request,zipfile
import ijson,openpyxl,py7zr
from defusedxml import ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parent
DATASETS={
 'structures':'finess-structures-1', 'activites':'finess-activites-1',
 'has-essms':'resultats-devaluation-des-etablissements-et-services-sociaux-et-medico-sociaux-essms',
 'has-sanitaire':'base-sur-la-qualite-et-la-securite-des-soins-anciennement-scope-sante',
 'ror':'offres-de-sante-sanitaire-medico-social-et-de-ville-en-france-metropolitaine-et-drom-1',
 'cnsa':'prix-hebergement-et-tarifs-dependance-des-ehpad-donnees-brutes'}
NOMS={
 'categories':'https://smt.esante.gouv.fr/fhir/CodeSystem/tre-r397-categorie-entite-geographique-exercice',
 'engagements':'https://smt.esante.gouv.fr/fhir/CodeSystem/tre-r395-engagement',
 'unites':'https://mos.esante.gouv.fr/NOS/TRE_R329-NatureCapacite/FHIR/TRE-R329-NatureCapacite/TRE_R329-NatureCapacite-FHIR.json',
 'statuts-capacite':'https://mos.esante.gouv.fr/NOS/TRE_R330-TypeStatutCapacite/FHIR/TRE-R330-TypeStatutCapacite/TRE_R330-TypeStatutCapacite-FHIR.json'}
SAE='https://data.drees.solidarites-sante.gouv.fr/api/explore/v2.1/catalog/datasets/708_bases-statistiques-sae/records?limit=100'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def js(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=lambda x:x.isoformat() if hasattr(x,'isoformat') else str(x),allow_nan=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(v):
 s=re.sub(r'[\s.\-]','',str(v or '').upper())
 if re.fullmatch(r'\d{8}',s):s='0'+s
 return s if re.fullmatch(r'[0-9][0-9A-Z][0-9]{7}',s) and s!='000000000' else ''
def prop(c,k):
 p=next((p for p in c.get('property',[]) if p['code']==k),{})
 return next((v for k,v in p.items() if k.startswith('value')),None)
def number(v):
 if v is None or str(v).strip()=='':return None
 try:
  x=float(str(v).replace(',','.'));return x if x>=0 and x<float('inf') else None
 except (ValueError,TypeError):return None
def flatten_concepts(cc):
 for c in cc:
  yield c
  yield from flatten_concepts(c.get('concept',[]))

class Collector:
 def __init__(self,cache,offline=False):
  self.cache=pathlib.Path(cache);self.cache.mkdir(parents=True,exist_ok=True);self.offline=offline;self.legal={r['finess_juridique'] for r in json.loads((ROOT/'ugecam-public.json').read_text())};self.sources=[];self.structures=[];self.facts=[];self.nomenclatures=[]
 def get(self,url,refresh=False):
  if not url.startswith('https://'):raise ValueError('HTTPS obligatoire')
  p=self.cache/(sha(url.encode())+pathlib.Path(url.split('?')[0]).suffix)
  if p.exists() and (self.offline or not refresh):return p
  if self.offline:raise ValueError('Cache absent : '+url)
  tmp=p.with_suffix(p.suffix+'.part')
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'MOAD-UGECAM-public-data/1.0','Accept':'*/*'})
   with urllib.request.urlopen(req,timeout=120) as inp,tmp.open('wb') as out:
    size=0
    while b:=inp.read(1024*1024):
     size+=len(b)
     if size>1500*1024*1024:raise ValueError('Fichier trop volumineux')
     out.write(b)
   if size<10:raise ValueError('Réponse vide')
   tmp.replace(p);return p
  finally:
   if tmp.exists():tmp.unlink()
 def meta(self,key):
  u='https://www.data.gouv.fr/api/1/datasets/'+DATASETS[key]+'/'
  d=json.loads(self.get(u,True).read_text());rr=[r for r in d['resources'] if r.get('url')]
  if not rr:raise ValueError('Jeu sans ressources')
  return rr
 def resource(self,key,match):
  rr=[r for r in self.meta(key) if match(r)]
  if not rr:raise ValueError('Ressource attendue absente : '+key)
  r=max(rr,key=lambda x:x.get('last_modified') or '');p=self.get(r['url'],refresh='static.data.gouv.fr/resources/' not in r['url'])
  return p,dict(resourceUrl=r['url'],sourceUrl='https://www.data.gouv.fr/datasets/'+DATASETS[key],sourceDate=r.get('last_modified',''),sha256=sha(p.read_bytes()))
 def adapter(self,key,fn,previous):
  start=(len(self.structures),len(self.facts),len(self.nomenclatures))
  try:
   info=fn();self.sources.append(dict(id=key,status='ok',checkedAt=now(),**info))
  except Exception as ex:
   del self.structures[start[0]:];del self.facts[start[1]:];del self.nomenclatures[start[2]:]
   old=next((s for s in previous.get('sources',[]) if s['id']==key),{})
   if key=='structures':self.structures.extend(previous.get('structures',[]))
   elif key=='nomenclatures':self.nomenclatures.extend(previous.get('nomenclatures',[]))
   else:self.facts.extend(f for f in previous.get('facts',[]) if f['source']==key)
   info={k:v for k,v in old.items() if k not in ['id','status','error','checkedAt']}
   self.sources.append(dict(id=key,status='stale' if old else 'error',checkedAt=now(),error=str(ex)[:500],**info))
   print(key,'ERROR',str(ex),file=sys.stderr,flush=True)
 def noms(self):
  digests=[];dates=[]
  for name,url in NOMS.items():
   p=self.get(url,True);d=json.loads(p.read_text());cc=list(flatten_concepts(d.get('concept',[])))
   if d.get('resourceType')!='CodeSystem' or not cc:raise ValueError('Nomenclature invalide : '+name)
   digests.append(sha(p.read_bytes()));dates.append(d.get('meta',{}).get('lastUpdated',''))
   if name=='categories':
    for c in cc:
     domain=prop(c,'domaine');domain=domain.get('code','') if isinstance(domain,dict) else domain or ''
     self.nomenclatures.append(dict(CLE='categorie:'+c['code'],CODE=c['code'],LIBELLE=c.get('display',''),DOMAINE=domain,PARENT=prop(c,'parent') or '',STATUT=prop(c,'status') or '',VERSION=d.get('version',''),SOURCE_URL=url,DATE_SOURCE=d.get('meta',{}).get('lastUpdated','')))
   else:
    self.nomenclatures.extend(dict(CLE=name+':'+c['code'],CODE=c['code'],LIBELLE=c.get('display',''),DOMAINE=name,PARENT=prop(c,'parent') or '',STATUT=prop(c,'status') or '',VERSION=d.get('version',''),SOURCE_URL=url,DATE_SOURCE=d.get('meta',{}).get('lastUpdated','')) for c in cc)
  return dict(sourceUrl=NOMS['categories'],resourceUrl=' | '.join(NOMS.values()),sourceDate=max(dates),sha256=sha('|'.join(digests).encode()),count=len(self.nomenclatures))
 def structure(self):
  p,info=self.resource('structures',lambda r:'journalier' in r['title'] and r['url'].endswith('.json.gz'));seen=set();found=set();generated=''
  with gzip.open(p,'rb') as f:
   for pm in ijson.items(f,'pmej.item'):
    gi=pm['informationsGeneralesPMEJ'];ej=norm(gi['numFinessPm'])
    if ej not in self.legal:continue
    found.add(ej)
    for eg in pm.get('ege') or []:
     g=eg['informationsGeneralesEGE'];code=norm(g['numFinessEge'])
     if not code or code in seen:raise ValueError('FINESS géographique invalide ou doublon')
     seen.add(code);ad=(eg.get('adresse') or [{}])[0];tel=next((x.get('telecom') or {} for x in eg.get('contact') or [] if (x.get('typeContact') or {}).get('roleContact')=='01'),{})
     ds=[]
     for en in eg.get('engagement') or []:
      if en.get('typeEngagement')=='DISP' and (not en.get('dateFinEngagement') or en['dateFinEngagement'][:10]>=now()[:10]) and (not en.get('dateCaduciteEngagement') or en['dateCaduciteEngagement'][:10]>=now()[:10]) and (not en.get('dateEffetEngagement') or en['dateEffetEngagement'][:10]<=now()[:10]):
       ds.append(dict(code=en.get('sousTypeEngagement') or '',date=en.get('dateEffetEngagement') or '',nom=en.get('nomEngagement') or ''))
     self.structures.append(dict(FINESS=code,FINESS_JURIDIQUE=ej,RAISON_SOCIALE=g.get('nomEgeCourt') or '',RAISON_SOCIALE_LONGUE=g.get('nomEgeLong') or '',CATEGORIE_CODE=eg.get('categorieentiteGeographiqueExercice') or '',ADRESSE=' '.join(str(x) for x in [ad.get('ligneQuatre') or ' '.join(str(ad.get(x) or '') for x in ['numeroVoie','typeVoie','libelleVoie']),ad.get('codePostal'),ad.get('ligneAcheminement')] if x),TELEPHONE=tel.get('telephone') or '',EMAIL=tel.get('courriel') or '',SIRET=g.get('siret') or '',DATE_OUVERTURE=g.get('dateOuverture') or '',DATE_AUTORISATION=g.get('datePremiereAutorisation') or '',DATE_FERMETURE=g.get('dateFermeture') or '',ETAT=eg.get('etatObjet') or '',DATE_MAJ_SOURCE=eg.get('dateDerniereMaj') or '',DISPOSITIFS=ds))
  if found!=self.legal:raise ValueError('FINESS juridiques absents : '+','.join(sorted(self.legal-found)))
  if len(self.structures)<200:raise ValueError('Extraction groupe anormalement petite')
  return dict(**info,count=len(self.structures),legalKeys=sorted(found))
 def activities(self):
  p,info=self.resource('activites',lambda r:'journalier' in r['title'] and r['url'].endswith('.json.gz'));targets={r['FINESS'] for r in self.structures};seen=set();found=set()
  with gzip.open(p,'rb') as f:
   for pm in ijson.items(f,'pmej.item'):
    ej=norm(pm.get('numFiness'))
    if ej not in self.legal:continue
    found.add(ej)
    auth={x['caracteristiquesGeneriques']['activiteAeId']:x for x in pm.get('activitesAutorisees') or []}
    for eg in pm.get('ege') or []:
     code=norm(eg.get('numFinessEge'))
     if code not in targets:continue
     aa=[]
     for x in eg.get('activitesExercees') or []:
      g=x['caracteristiquesGeneriques'];a=auth.get(g.get('identifiantAutorisation'));aa.append(dict(id=g['activiteAeId'],etat=g.get('etatObjet'),debut=g.get('dateDebutActiviteAutorisee'),fin=g.get('dateFinEffectiveActivite') or g.get('dateFinActiviteAutorisee'),nature=x.get('nature'),capacites=x.get('capacite') or [],autorisation=None if not a else dict(id=a['caracteristiquesGeneriques']['activiteAeId'],etat=a['caracteristiquesGeneriques'].get('etatObjet'),capacites=a.get('capacite') or [])))
     if code in seen:raise ValueError('Activités dupliquées')
     seen.add(code);self.fact('activites',code,dict(activites=aa),f'{len(aa)} activités décrites',info)
  if found!=self.legal:raise ValueError('Activités : périmètre juridique incomplet')
  return dict(**info,count=len(seen))
 def fact(self,source,code,data,summary,info):
  self.facts.append(dict(source=source,FINESS=code,data=data,summary=summary,sourceDate=info.get('sourceDate',''),sourceUrl=info.get('sourceUrl','')))
 def has_essms(self):
  p,info=self.resource('has-essms',lambda r:r['title']=='open_data_par_essms.xlsx');targets={r['FINESS'] for r in self.structures};groups=collections.defaultdict(list)
  w=openpyxl.load_workbook(p.open('rb'),read_only=True,data_only=True);it=w.active.values;headers=next(it)
  if not {'finess_geo','eval_date_fin','eval_code','indice_qualite'}.issubset(headers):raise ValueError('Schéma HAS ESSMS modifié')
  for row in it:
   r=dict(zip(headers,row));code=norm(r['finess_geo'])
   if code in targets:groups[code].append({k:v for k,v in r.items() if k.startswith(('eval_date','cotation_')) or k in ['eval_code','multi_essms','indice_qualite','nb_ci_atteints','nb_ci','essms_categ_finess_code','essms_secteur']})
  w.close()
  for code,rr in groups.items():
   rr.sort(key=lambda x:str(x.get('eval_date_fin') or ''),reverse=True);self.fact('has-essms',code,dict(evaluations=rr,lien='https://www.has-sante.fr/fiche-essms/'+code),f"Évaluation du {str(rr[0].get('eval_date_fin') or '')[:10]} · niveau {rr[0].get('indice_qualite') or 'non renseigné'}",info)
  return dict(**info,count=len(groups))
 def has_san(self):
  p,info=self.resource('has-sanitaire',lambda r:r['title']=='base-document-etablissements.jsonl');targets={r['FINESS'] for r in self.structures};count=0
  with p.open() as f:
   for line in f:
    r=json.loads(line);code=norm(r.get('finess_geo'))
    if not code:raise ValueError('Schéma HAS sanitaire modifié')
    if code not in targets:continue
    # Public aggregate indicators only. No professional/person directories.
    data={k:r[k] for k in ['certification_v2021','certification_v2014','activites'] if k in r}
    # Keep the newest public collection for each indicator, not every past year.
    latest=[]
    for indicator in r.get('IQSS',[]):
     values=indicator.get('valeurs') or []
     if values:
      v=max(values,key=lambda v:v.get('annee_recueil') or 0)
      latest.append({**{k:indicator[k] for k in ['indicateur','secteur','theme','source'] if k in indicator},'valeurs':[{k:v[k] for k in ['annee_recueil','resultat','classe','evolution'] if k in v}]})
    data['IQSS']=latest;data['lien']='https://www.has-sante.fr/fiche-etablissement/'+code
    self.fact('has-sanitaire',code,data,'Certification et indicateurs de qualité HAS',info);count+=1
  if not count:raise ValueError('Aucun rapprochement HAS sanitaire')
  return dict(**info,count=count)
 def cnsa(self):
  rr=[r for r in self.meta('cnsa') if r['format']=='csv' and re.search(r'20\d{2}(?:\d{2})?[_-]brute',r['title'])]
  def period(r):return re.search(r'(20\d{2}(?:\d{2})?)[_-]brute',r['title'])[1]
  latest_year=max(period(r)[:4] for r in rr);annual=[r for r in rr if len(period(r))==4 and period(r)<latest_year];chosen=[r for r in rr if period(r).startswith(latest_year)]
  if annual:chosen.append(max(annual,key=period))
  targets={r['FINESS'] for r in self.structures};found={};digests=[];urls=[];dates=[]
  for resource in sorted(chosen,key=period):
   p=self.get(resource['url']);urls.append(resource['url']);dates.append(resource.get('last_modified') or '');digests.append(sha(p.read_bytes()))
   with p.open(encoding='utf-8-sig') as f:
    reader=csv.DictReader(f,delimiter=';')
    if 'finessEt' not in reader.fieldnames:raise ValueError('Schéma CNSA modifié')
    for r in reader:
     code=norm(r['finessEt'])
     if code in targets:
      # Later file period supersedes an older snapshot; empty cells stay empty.
      r['PERIODE_FICHIER']=period(resource);r['SOURCE_FICHIER']=resource['url'];found[code]=r
  info=dict(resourceUrl=' | '.join(urls),sourceUrl='https://www.data.gouv.fr/datasets/'+DATASETS['cnsa'],sourceDate=max(dates),sha256=sha('|'.join(digests).encode()))
  for code,r in found.items():self.fact('cnsa',code,r,'Tarifs déclarés · mise à jour '+r.get('DATE_MAJ','non indiquée'),info)
  return dict(**info,count=len(found),warning='Dernière ligne disponible par FINESS : fichiers de l’année en cours complétés par le dernier annuel. La date de déclaration est conservée ; ce n’est pas un tarif en temps réel.')
 def sae(self):
  d=json.loads(self.get(SAE,True).read_text());rr=[r for r in d['results'] if 'CSV' in r['nom_du_fichier']];r=max(rr,key=lambda r:r['annee']);year=r['annee'];p=self.get(r['url_de_telechargement'],True);info=dict(resourceUrl=r['url_de_telechargement'],sourceUrl='https://data.drees.solidarites-sante.gouv.fr/explore/dataset/708_bases-statistiques-sae/',sourceDate=year,sha256=sha(p.read_bytes()))
  # Workspaces without /proc cannot use py7zr's optional memory detection.
  if not pathlib.Path('/proc/meminfo').exists():py7zr.py7zr.get_memory_limit=lambda:64*1024*1024
  dest=self.cache/('sae-'+sha(p.read_bytes())[:16]);dest.mkdir(exist_ok=True)
  with py7zr.SevenZipFile(p) as z:
   names=[n for n in z.getnames() if '/Bases CSV/' in n and pathlib.PurePosixPath(n).name.upper().startswith('SYGEN_')]
   if len(names)!=1 or '..' in pathlib.PurePosixPath(names[0]).parts:raise ValueError('Archive SAE inattendue')
   target=dest/names[0]
   if not target.exists():z.extract(path=dest,targets=names)
  targets={r['FINESS'] for r in self.structures};count=0
  with target.open(encoding='cp1252') as f:
   reader=csv.DictReader(f,delimiter=';')
   if not {'FI','AN','LIT_SSR','PLA_SSR'}.issubset(reader.fieldnames):raise ValueError('Schéma SAE SYGEN modifié')
   for r in reader:
    code=norm(r['FI'])
    if code in targets:self.fact('sae',code,dict(millesime=year,type_base='statistique consolidée',bordereau='SYGEN',variables=r),'Capacités et activité sanitaires · SAE '+year,info);count+=1
  if not count:raise ValueError('Aucun rapprochement SAE')
  return dict(**info,count=count,warning='Base annuelle consolidée ; périmètre géographique de déclaration SAE conservé, sans ventilation aux services Airmes.')
 def ror(self):
  rr=[r for r in self.meta('ror') if r['format']=='zip' or r['url'].endswith('.zip')];targets={r['FINESS'] for r in self.structures};group=collections.defaultdict(list);resources=[];dates=[];digests=[]
  ns='{urn:ihe:iti:csd:2013}'
  for r in rr:
   p=self.get(r['url']);resources.append(r['url']);dates.append(r.get('last_modified') or '');digests.append(sha(p.read_bytes()));matched={};fac={};service_defs={}
   with zipfile.ZipFile(p) as z:
    names=[n for n in z.namelist() if n.lower().endswith('.xml')]
    if not names or len(names)>100:raise ValueError('Archive ROR sans XML exploitable')
    for xmlname in names:
     # CSD directories contain top-level organizations, services and facilities.
     # Process only directory children, retaining each complete subtree until end.
     with z.open(xmlname) as inp:
      stack=[]
      for event,node in ET.iterparse(inp,events=['start','end']):
       if event=='start':stack.append(node);continue
       if len(stack)==3:
        tag=node.tag.rsplit('}',1)[-1]
        if tag=='organization':
         ids=[norm(x.get('code')) for x in node.findall(ns+'otherID') if x.get('assigningAuthorityName')=='1.2.250.1.213.3.2'];code=next((c for c in ids if c in targets),'')
         if code:matched[node.get('entityID')]=code
        elif tag=='service':
         if node.findtext(ns+'primaryName'):service_defs[node.get('entityID')]=node.findtext(ns+'primaryName')
        elif tag=='facility':
         orgs=[x.get('entityID') for x in node.findall('.//'+ns+'organizations/'+ns+'organization')];code=next((matched[o] for o in orgs if o in matched),'')
         if code:
          name=node.findtext(ns+'primaryName') or '';record=node.find(ns+'record');services=[dict(id=x.get('entityID'),libelle=service_defs.get(x.get('entityID'),'') or x.get('entityID')) for x in node.findall('.//'+ns+'organizations/'+ns+'organization/'+ns+'service')+node.findall('.//'+ns+'services/'+ns+'service')]
          group[code].append(dict(nom=name,identifiant=node.get('entityID'),services=services,date_maj=record.get('updated','') if record is not None else '',region_fichier=r['title']))
        node.clear();stack[-2].remove(node)
       elif len(stack)==2:node.clear()
       stack.pop()
  info=dict(sourceUrl='https://www.data.gouv.fr/datasets/'+DATASETS['ror'],resourceUrl=' | '.join(resources),sourceDate=min(dates),sourceDateMax=max(dates),sha256=sha('|'.join(digests).encode()))
  for code,items in group.items():self.fact('ror',code,dict(offres=items),f'{len(items)} unités/offres décrites dans le ROR',info)
  if not group:raise ValueError('Aucune offre ROR rapprochée : vérifier le schéma')
  return dict(**info,count=len(group),warning='Dates des fichiers régionaux hétérogènes ; aucune disponibilité de lit en temps réel.')
 def run(self,out):
  out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);previous={}
  if (out/'latest.json').exists():
   pointer=json.loads((out/'latest.json').read_text());b=(out/pointer['file']).read_bytes();previous=json.loads(gzip.decompress(b) if pointer['file'].endswith('.gz') else b)
  for key,fn in [('nomenclatures',self.noms),('structures',self.structure),('activites',self.activities),('has-essms',self.has_essms),('has-sanitaire',self.has_san),('ror',self.ror),('sae',self.sae),('cnsa',self.cnsa)]:
   print('Collect',key,flush=True);self.adapter(key,fn,previous)
  if any(s['status']!='ok' for s in self.sources if s['id'] in ['structures','nomenclatures','activites']):raise ValueError('Socle FINESS incomplet : publication refusée')
  if len({(f['source'],f['FINESS']) for f in self.facts})!=len(self.facts):raise ValueError('Doublon de faits')
  self.publish(out)
 def publish(self,out):
  out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
  targets={r['FINESS'] for r in self.structures};self.facts=[f for f in self.facts if f['FINESS'] in targets];self.enrich()
  pack=dict(schemaVersion=1,preparedAt=now(),legalKeys=sorted(self.legal),sources=self.sources,structures=sorted(self.structures,key=lambda r:r['FINESS']),facts=sorted(self.facts,key=lambda r:(r['source'],r['FINESS'])),nomenclatures=self.nomenclatures)
  raw=js(pack).encode();b=gzip.compress(raw,compresslevel=9,mtime=0);digest=sha(b);rel='snapshots/'+digest+'.json.gz';(out/'snapshots').mkdir(exist_ok=True);(out/rel).write_bytes(b)
  pointer=dict(schemaVersion=1,preparedAt=pack['preparedAt'],file=rel,sha256=digest,bytes=len(b),uncompressedBytes=len(raw),sources=self.sources)
  (out/'latest.json').write_text(js(pointer)+'\n');print(js(dict(bytes=len(b),structures=len(self.structures),facts=len(self.facts),sources=self.sources)),flush=True)
 def enrich(self):
  noms={r['CLE']:r for r in self.nomenclatures};facts={(f['source'],f['FINESS']):f for f in self.facts}
  for r in self.structures:
   c=noms.get('categorie:'+r['CATEGORIE_CODE'],{});r['CATEGORIE']=c.get('LIBELLE') or r['CATEGORIE_CODE'];r['DOMAINE']=c.get('DOMAINE','');r['SECTEUR_SUGGERE']={'SAN':'Sanitaire','SOC':'Social et médico-social'}.get(r['DOMAINE'],'À qualifier')
   r['DISPOSITIF']=' · '.join(sorted(set(noms.get('engagements:'+x['code'],{}).get('LIBELLE') or x['code'] for x in r['DISPOSITIFS'])))
   # No authorization capacity is copied to each exercising establishment.
   # Only active exercised activities and unsegmented capacities are eligible.
   a=facts.get(('activites',r['FINESS']),{}).get('data',{}).get('activites',[]);totals={};conflict=False;seen={}
   for x in a:
    if x['etat']!='A':continue
    for v in x['capacites']:
     if any(v.get(k) for k in ['modeFinancement','habilitation','typeLogement','genre']):continue
     unit=v.get('uniteMesureCapacite');status=v.get('statutCapacite');n=number(v.get('nombre'));cid=v.get('idCapacite')
     if n is None or status not in ['01','08','09']:continue
     if cid in seen:
      if seen[cid]!=(status,unit,n):conflict=True
      continue
     seen[cid]=(status,unit,n);totals[(status,unit)]=totals.get((status,unit),0)+n
   r['CAPACITES']=[dict(statut=k[0],libelle_statut=noms.get('statuts-capacite:'+k[0],{}).get('LIBELLE') or k[0],unite=k[1],libelle_unite=noms.get('unites:'+k[1],{}).get('LIBELLE') or k[1],nombre=v) for k,v in sorted(totals.items())] if not conflict else []
   r['STATUT_CAPACITES']='Capacités non ventilées des activités exercées actives ; unités séparées' if totals and not conflict else 'Non renseigné ou ambigu dans les activités exercées'

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);ap.add_argument('--output',required=True);ap.add_argument('--offline',action='store_true');a=ap.parse_args();Collector(a.cache,a.offline).run(a.output)
