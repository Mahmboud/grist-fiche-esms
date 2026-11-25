"""HAS official XLSX join: per-ESSMS quality level + original per-evaluation ratings."""
import collections,datetime,re,openpyxl
META={'eval_code','multi_essms','oe_nom','oe_numero_accreditation','nb_at','raison_sociale','essms_categ_finess_code','essms_categ_finess_libelle','essms_secteur','essms_type_structure','indice_qualite','nb_ci_atteints','nb_ci','3.6.2_nc'}
def norm(v):
 s=re.sub(r'[\s.\-]','',str(v or '').upper())
 if re.fullmatch(r'\d{8}',s):s='0'+s
 return s if re.fullmatch(r'[0-9][0-9A-Z][0-9]{7}',s) and s!='000000000' else ''
def cell(v):return v.isoformat() if isinstance(v,(datetime.date,datetime.datetime)) else v
def extract(essms_file,eval_file,targets):
 groups=collections.defaultdict(list);w=openpyxl.load_workbook(essms_file,read_only=True,data_only=True)
 try:
  it=w.active.values;head=next(it);assert {'finess_geo','eval_code','indice_qualite','eval_date_fin','nb_ci','nb_ci_atteints'}.issubset(head),'Schéma HAS ESSMS modifié'
  codeidx=head.index('finess_geo')
  for row in it:
   code=norm(row[codeidx])
   if code not in targets:continue
   data={k:cell(v) for k,v in zip(head,row) if k in META or k.startswith(('eval_date','cotation_'))}
   assert data['indice_qualite'] in ['A','B','C','D',None,''],'Niveau HAS inconnu'
   groups[code].append(data)
 finally:w.close()
 evalcodes={r['eval_code'] for rr in groups.values() for r in rr};reports={};w=openpyxl.load_workbook(eval_file,read_only=True,data_only=True)
 try:
  it=w.active.values;head=next(it);assert {'eval_code','cotation_chapitre_1','cotation_chapitre_2','cotation_chapitre_3'}.issubset(head),'Schéma HAS évaluations modifié';idx=head.index('eval_code')
  for row in it:
   if row[idx] not in evalcodes:continue
   r={k:cell(v) for k,v in zip(head,row) if k.startswith('cotation_') or k in ['eval_code','oe_nom','oe_numero_accreditation','multi_essms','nb_ci_atteints','raisons_sociales_essms']};assert r['eval_code'] not in reports,'Évaluation HAS dupliquée';reports[r['eval_code']]=r
 finally:w.close()
 for code,rr in groups.items():
  seen=set()
  for r in rr:
   assert r['eval_code'] not in seen,'ESSMS/évaluation dupliqué';seen.add(r['eval_code']);assert r['eval_code'] in reports,('Rapport manquant',r['eval_code']);r['cotations_rapport']=reports[r['eval_code']];r['cotations_rapport_disponibles']=True
   for data in [r,r['cotations_rapport']]:
    for k,v in data.items():
     if k.startswith('cotation_') and isinstance(v,(int,float)):assert 0<=v<=4,(code,k,v)
   if r['nb_ci_atteints'] is not None and r['nb_ci'] is not None:assert 0<=r['nb_ci_atteints']<=r['nb_ci']
  rr.sort(key=lambda r:(r.get('eval_date_fin') or '',r['eval_code']),reverse=True)
 return dict(groups)
