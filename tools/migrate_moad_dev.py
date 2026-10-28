"""Non-destructive DEV migration. Source is never modified or published.

Usage: python tools/migrate_moad_dev.py reference.grist output-directory
Requires the official grist-core Python engine on PYTHONPATH; see DEV-MOAD.md.
"""
import sys, json, re, unicodedata, collections, pathlib, hashlib, shutil
from offline_grist import load, act, records, export, objtypes
from predicate_formula import parse_predicate_formula

def norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD',str(s or '')).encode('ascii','ignore').decode().lower())
def ids(v):
    return [int(x) for x in v if isinstance(x,(int,float)) and x>0] if isinstance(v,(list,tuple)) else []
def bulk(e,t,rr):
    if not rr:return
    keys=sorted(set().union(*(r.keys() for r in rr))-{'id'})
    act(e,['BulkAddRecord',t,[r.get('id') for r in rr],{k:[r.get(k) for r in rr] for k in keys}])
def table(e,name,cols):
    act(e,['AddTable',name,[dict(id=k,type=t,isFormula=bool(f),formula=f) for k,t,f in cols]])
def col(e,t,k,typ,formula=''):
    act(e,['AddColumn',t,k,dict(type=typ,isFormula=bool(formula),formula=formula)])
def update(e,t,i,**v):act(e,['UpdateRecord',t,i,v])
def acl(e,t,rules,columns='*'):
    rid=act(e,['AddRecord','_grist_ACLResources',None,{'tableId':t,'colIds':columns}]).retValues[0]
    for pos,(formula,permission) in enumerate(rules,1):
        act(e,['AddRecord','_grist_ACLRules',None,{'resource':rid,'aclFormula':formula,'aclFormulaParsed':parse_predicate_formula(formula) if formula else '', 'permissionsText':permission,'rulePos':pos}])
def owner_only(e,t):
    existing=[r for r in records(e,'_grist_ACLResources') if r['tableId']==t]
    for rr in existing:
        gone=[r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==rr['id']]
        if gone:act(e,['BulkRemoveRecord','_grist_ACLRules',gone])
        act(e,['RemoveRecord','_grist_ACLResources',rr['id']])
    acl(e,t,[('user.Access == OWNER','+CRUD'),('','-CRUD')])

def widget_urls(e,base,mapping):
    # Grist customView is JSON encoded inside options. Some exports contain
    # an extra escaped layer; preserve it without touching section visibility.
    for r in records(e,'_grist_Views_section'):
        text=r.get('options') or ''
        text=re.sub(r'https://mahmboud.github.io/grist-fiche-esms/([\w-]+\.(?:html|js))',lambda m:base+mapping.get(m[1],m[1]),text)
        if text!=r.get('options'):update(e,'_grist_Views_section',r['id'],options=text)

def main(source,outdir):
    out=pathlib.Path(outdir);out.mkdir(parents=True,exist_ok=True)
    root=pathlib.Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'dev/moad-airmes-20261028/widgets.json').read_text())
    e=load(source)
    # Fix invalid display-column links in the supplied document, using its own
    # display helpers. This also prevents their automatic removal by Grist.
    act(e,['BulkUpdateRecord','_grist_Tables_column',[455,456],{'displayCol':[458,457]}])
    widget_urls(e,manifest['baselineBase'],manifest['baseline'])
    export(e,source,str(out/'MOAD_2026_DEV_BASE_REFERENCE.grist'))
    oldsites={r['id']:r for r in records(e,'SITES_nomenclature_UGECAM')}
    airmes={r['id']:r for r in records(e,'SITES_nomenclature_AIRMES')}
    oldesms={r['id']:r for r in records(e,'ESMS_Liste_UGECAM_')}
    raw=records(e,'Import_entite_AIRMES')
    ugecams=records(e,'UGECAM')
    oldanswers=records(e,'Autodiagnostic')
    issues=[]
    def issue(t,i,field,detail,candidates=[]):
        issues.append({'TABLE_SOURCE':t,'LIGNE_SOURCE':i,'CHAMP':field,'DETAIL':detail,'CANDIDATS':json.dumps(candidates,ensure_ascii=False),'STATUT':'À arbitrer'})
    # UGECAM identity comes from level-1 parent IDs, rather than similar names.
    aliases={'ugecamhautsdefrance':4,'ugecamnordest':8,'ugecamrhonealpes':7,'ugecamidf':10}
    def uid(r):
        v=r.get('NIVEAU1');return v if isinstance(v,int) and 1<=v<=11 else aliases.get(norm(v),0)
    site_rows=[];sitekeys={}
    for r in raw:
        if r.get('LEVEL')!=2 or not r.get('IS_ENTITE'):continue
        u=uid(r);name=re.sub(r'\s+',' ',str(r['NIVEAU2'])).strip()
        if not u:
            issue('Import_entite_AIRMES',r['id'],'NIVEAU1','UGECAM non résolue');continue
        sitekeys[(u,norm(name))]=r['id']
        site_rows.append(dict(id=r['id'],NOM=name,UGECAM=u,AIRMES_ID=str(r['ID_service']),SOURCE_LIGNE=r['id']))
    sitebyid={r['id']:r for r in site_rows}
    table(e,'SITES',[('NOM','Text',''),('UGECAM','Ref:UGECAM',''),('AIRMES_ID','Text',''),('SOURCE_LIGNE','Int',''),
       ('DIRECTION_NOMS','Text','"\\n".join(sorted([c.NOM_PRENOM_contact for c in CONTACTS.all if c.FONCTION.id in [20, 21, 23] and (c.SITE_PRINCIPAL.id == $id or $id in [s.id for s in c.SITES_RESP_AIRMES])]))')])
    # Add dependencies before populating formula rows.
    col(e,'CONTACTS','SITE_PRINCIPAL','Ref:SITES')
    col(e,'CONTACTS','SITES_RESP_AIRMES','RefList:SITES')
    bulk(e,'SITES',site_rows)
    # Candidate evidence from import relationships, across all levels.
    esms_sites=collections.defaultdict(set)
    for r in raw:
        sid=sitekeys.get((uid(r),norm(r.get('NIVEAU2'))))
        if sid:
            for eid in ids(r.get('Rattachement_ESMS_liste_UGECAM')):esms_sites[eid].add(sid)
    oldmap={}
    for oid,r in oldsites.items():
        # Headquarters/national records are profiles, never artificial sites.
        if norm(r['SITES_nomenclature_UGECAM']).startswith(('siege','dngu')):continue
        links=ids(r['SITES_appelation_AIRMES'])
        candidates={sitekeys[(airmes[x]['UGECAM'],norm(airmes[x]['SITES_appelation_AIRMES']))] for x in links if x in airmes and (airmes[x]['UGECAM'],norm(airmes[x]['SITES_appelation_AIRMES'])) in sitekeys}
        evidence=set().union(*(esms_sites[x['id']] for x in oldesms.values() if x.get('SITES_nomenclature_UGECAM')==oid))
        if len(candidates)==1 and (not evidence or candidates==evidence) and sitebyid[next(iter(candidates))]['UGECAM']==r['UGECAM']:
            oldmap[oid]=next(iter(candidates))
        else:issue('SITES_nomenclature_UGECAM',oid,'SITES_appelation_AIRMES','Correspondance absente, multiple ou contradictoire avec les rattachements Airmes.',sorted(candidates|evidence))
    for c in records(e,'CONTACTS'):
        primary=c['SITES_nomenclature_UGECAM'];sid=oldmap.get(primary,0)
        if primary and not sid and primary not in oldsites:issue('CONTACTS',c['id'],'SITE_PRINCIPAL','Référence historique invalide : '+str(primary))
        resp=sorted({oldmap[x] for x in ids(c['SITES_EN_RESPONSABILITE']) if x in oldmap and oldmap[x]!=sid})
        for x in ids(c['SITES_EN_RESPONSABILITE']):
            if x not in oldmap and x in oldsites and not norm(oldsites[x]['SITES_nomenclature_UGECAM']).startswith(('siege','dngu')):issue('CONTACTS',c['id'],'SITES_RESP_AIRMES','Site en responsabilité non résolu : '+str(x))
        update(e,'CONTACTS',c['id'],SITE_PRINCIPAL=sid,SITES_RESP_AIRMES=['L',*resp])
    # The target ESMS/service catalog follows active Airmes entities (levels 3+).
    # Shared FINESS links are not copied to multiple services without evidence.
    table(e,'ESMS',[('RAISON_SOCIALE','Text',''),('SITE','Ref:SITES',''),('UGECAM','Ref:UGECAM','$SITE.UGECAM'),('TYPOLOGIE','Text',''),('FINESS','Text',''),('ADRESSE','Text',''),('AIRMES_ID','Text',''),('SOURCE_LIGNE','Int',''),('ESMS_LEGACY_IDS','RefList:ESMS_Liste_UGECAM_','')])
    entities=[r for r in raw if isinstance(r.get('LEVEL'),(int,float)) and r['LEVEL']>=3 and r.get('IS_ENTITE') is True]
    # Engine represents Bool values as bool.
    usage=collections.Counter(x for r in entities for x in ids(r.get('Rattachement_ESMS_liste_UGECAM')))
    es=[]
    for r in entities:
        sid=sitekeys.get((uid(r),norm(r.get('NIVEAU2'))))
        if not sid:
            issue('Import_entite_AIRMES',r['id'],'SITE','Entité sans site Airmes résolu');continue
        name=str(r.get('NIVEAU'+str(int(r['LEVEL']))) or '').strip()
        linked=[x for x in ids(r.get('Rattachement_ESMS_liste_UGECAM')) if x in oldesms]
        exact=[x for x in linked if norm(oldesms[x]['ESMS_raison_sociale'])==norm(name)]
        unique=[x for x in linked if usage[x]==1]
        accepted=exact if len(exact)==1 else unique if len(unique)==1 else []
        src=oldesms[accepted[0]] if accepted else {}
        if linked and not accepted:issue('Import_entite_AIRMES',r['id'],'FINESS','FINESS/adresse non recopiés : lien historique partagé ou ambigu.',linked)
        es.append(dict(id=r['id'],RAISON_SOCIALE=name,SITE=sid,TYPOLOGIE=str(r.get('type_prestation_name') or ''),FINESS=src.get('FINESS',''),ADRESSE=src.get('ADRESSE',''),AIRMES_ID=str(r['ID_service']),SOURCE_LIGNE=r['id'],ESMS_LEGACY_IDS=['L',*linked]))
    bulk(e,'ESMS',es)
    # Clone the answer schema through the real Grist engine. The original table,
    # its row IDs and every original answer remain available to the owner.
    source_cols=[r for r in records(e,'_grist_Tables_column') if r['parentId']==38 and r['colId']!='manualSort' and not r['colId'].startswith('gristHelper_')]
    target_cols=[(r['colId'],r['type'],r['formula'] if r['isFormula'] else '') for r in source_cols]
    target_cols += [('SITE','Ref:SITES',''),('CONFLITS_MIGRATION','Int',''),('Site_nom','Text','$SITE.NOM'),('UGECAM_nom','Text','$SITE.UGECAM.UGECAM')]
    target_cols=[(k,t,'$SITE.NOM' if k=='gristHelper_Display' else '$SITE.UGECAM.UGECAM' if k=='gristHelper_Display2' else f) for k,t,f in target_cols]
    table(e,'Autodiagnostic_DEV',target_cols)
    for r in source_cols:
        if not r['isFormula'] and r['formula']:
            act(e,['ModifyColumn','Autodiagnostic_DEV',r['colId'],{'formula':r['formula'],'isFormula':False}])
    newref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='Autodiagnostic_DEV')
    newmeta={r['colId']:r for r in records(e,'_grist_Tables_column') if r['parentId']==newref}
    for r in source_cols:
        if not r['isFormula'] and r['formula']:
            update(e,'_grist_Tables_column',newmeta[r['colId']]['id'],recalcWhen=r['recalcWhen'],recalcDeps=objtypes.encode_object(r['recalcDeps']))
    groups=collections.defaultdict(list)
    for r in oldanswers:
        sid=oldmap.get(r['SITES_nomenclatures_UGECAM'])
        if sid:groups[sid].append(r)
        elif any(not empty(r.get(k)) for k in answer_keys(source_cols)):
            issue('Autodiagnostic',r['id'],'SITE','Réponses conservées dans la source ; site non résolu.')
    data=[]
    for s in site_rows:
        rs=groups[s['id']];item={'id':s['id'],'SITE':s['id'],'UGECAM':s['UGECAM'],'CONFLITS_MIGRATION':0}
        if rs:
            first=min(rs,key=lambda r:r.get('Cree_le') or float('inf'))
            latest=max(rs,key=lambda r:r.get('Derniere_mise_a_jour') or 0)
            for k,r in [('Cree_le',first),('Cree_par_contact',first),('Derniere_mise_a_jour',latest),('Derniere_mise_a_jour_contact',latest)]:
                item[k]=objtypes.encode_object(r.get(k))
        for k in answer_keys(source_cols):
            vv={json.dumps(rs0[k],ensure_ascii=False,sort_keys=True):rs0[k] for rs0 in rs if not empty(rs0.get(k))}
            if len(vv)==1:item[k]=objtypes.encode_object(next(iter(vv.values())))
            elif len(vv)>1:
                item['CONFLITS_MIGRATION']+=1
                issue('Autodiagnostic',s['id'],k,'Réponses contradictoires ; aucune valeur écrasée. Lignes source : '+str([r['id'] for r in rs]),[{'ligne':r['id'],'valeur':r.get(k)} for r in rs if not empty(r.get(k))])
        data.append(item)
    bulk(e,'Autodiagnostic_DEV',data)
    # Separate new history, so legacy references never change their meaning.
    hcols=[r for r in records(e,'_grist_Tables_column') if r['parentId']==40 and r['colId']!='manualSort']
    table(e,'Autodiagnostic_Historique_DEV',[(r['colId'],'Ref:Autodiagnostic_DEV' if r['colId']=='Site' else r['type'],r['formula'] if r['isFormula'] else '') for r in hcols])
    col(e,'DEMANDES_ACCES','SITE_AIRMES','Ref:SITES')
    col(e,'DEMANDES_ACCES','SITES_RESP_AIRMES','RefList:SITES')
    col(e,'DEMANDES_ACCES','ESMS_AIRMES','RefList:ESMS')
    table(e,'MIGRATION_A_ARBITRER',[('TABLE_SOURCE','Text',''),('LIGNE_SOURCE','Int',''),('CHAMP','Text',''),('DETAIL','Text',''),('CANDIDATS','Text',''),('STATUT','Choice','')])
    bulk(e,'MIGRATION_A_ARBITRER',issues)
    table(e,'MIGRATION_SITES',[('ANCIEN_SITE','Ref:SITES_nomenclature_UGECAM',''),('SITE','Ref:SITES','')])
    bulk(e,'MIGRATION_SITES',[dict(ANCIEN_SITE=k,SITE=v) for k,v in oldmap.items()])
    table(e,'PROFIL_SESSION',[('CONTACT','Ref:CONTACTS',''),('EMAIL','Text','$CONTACT.EMAIL'),('SIEGE','Bool','$CONTACT.SIEGE'),('DNGU','Bool','$CONTACT.DNGU')])
    bulk(e,'PROFIL_SESSION',[dict(id=c['id'],CONTACT=c['id']) for c in records(e,'CONTACTS')])
    acl(e,'PROFIL_SESSION',[('user.Access == OWNER','+CRUD'),('rec.EMAIL == user.Email','+R-CUD'),('','-CRUD')])
    # Demands may never self-validate or select another contact. The account
    # email is supplied by the existing trigger formula, not trusted client data.
    owner_only(e,'DEMANDES_ACCES')
    demand_rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='DEMANDES_ACCES')
    default_rule=next(r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==demand_rid and not r['aclFormula'])
    # Place creation/read rules before the final deny rule.
    update(e,'_grist_ACLRules',default_rule,rulePos=10)
    for pos,formula,perm in [(2,"rec.EMAIL == user.Email",'+R-CUD'),(1.5,"user.IsLoggedIn is True and newRec.EMAIL == user.Email and newRec.STATUT == 'À valider' and newRec.CONTACT == 0 and not newRec.DATE_VALIDATION and not newRec.VALIDE_PAR",'+C-RUD')]:
        act(e,['AddRecord','_grist_ACLRules',None,{'resource':demand_rid,'aclFormula':formula,'aclFormulaParsed':parse_predicate_formula(formula),'permissionsText':perm,'rulePos':pos}])
    # Closed by default: retained source tables and migration evidence are owner-only.
    for t in ['SITES_nomenclature_UGECAM','SITES_nomenclature_AIRMES','ESMS_Liste_UGECAM_','Import_entite_AIRMES','ESMS_liste_a_partir_sites_AIRMES','Autodiagnostic','Autodiagnostic_Historique','MIGRATION_A_ARBITRER','MIGRATION_SITES','ESMS_Liste_UGECAM__summary_UGECAM','ESMS_Liste_UGECAM__summary_SITES_nomenclature_UGECAM_UGECAM']:
        owner_only(e,t)
    for t in ['AUTODIAG_REFERENTIEL_QUESTIONS','REFERENTIEL_FONCTIONS','REFERENTIEL_INSCRIPTION_ESMS']:owner_only(e,t)
    valid="user.demande_acces.STATUT == 'Validé'"
    def scope(site,ug):
        return f"(user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == {ug}) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and ((user.droits_supp.SITE_PRINCIPAL != 0 and user.droits_supp.SITE_PRINCIPAL == {site}) or {site} in user.droits_supp.SITES_RESP_AIRMES)))"
    list_ok=f"{valid} and (user.droits_supp.ACCES_LISTE_ESMS is True or user.droits_supp.ACCES_ARBORESCENCE is True)"
    acl(e,'SITES',[('user.Access == OWNER','+CRUD'),('user.IsLoggedIn is True','+R-CUD'),('','-CRUD')])
    acl(e,'SITES',[('user.Access == OWNER','+CRUD'),(list_ok+' and '+scope('rec.id','rec.UGECAM'),'+R-CUD'),('','-CRUD')],'DIRECTION_NOMS')
    acl(e,'ESMS',[('user.Access == OWNER','+CRUD'),(list_ok+' and '+scope('rec.SITE','rec.UGECAM'),'+R-CUD'),('','-CRUD')])
    for t,site,ug,perm in [('Autodiagnostic_DEV','rec.SITE','rec.UGECAM','+RU-CD'),('Autodiagnostic_Historique_DEV','rec.Site.SITE','rec.Site.UGECAM','+R-CUD')]:
        acl(e,t,[('user.Access == OWNER','+CRUD'),(valid+' and user.droits_supp.ACCES is True and '+scope(site,ug),perm),('','-CRUD')])
    history_rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='Autodiagnostic_Historique_DEV')
    create_history=valid+' and user.droits_supp.ACCES is True and '+scope('newRec.Site.SITE','newRec.Site.UGECAM')
    act(e,['AddRecord','_grist_ACLRules',None,{'resource':history_rid,'aclFormula':create_history,'aclFormulaParsed':parse_predicate_formula(create_history),'permissionsText':'+C','rulePos':1.5}])
    # Protect row identity/scope against editor changes to permitted answer rows.
    acl(e,'Autodiagnostic_DEV',[('user.Access == OWNER','+CRUD'),('','-CUD')],'SITE,UGECAM,SITES_nomenclatures_UGECAM,CONFLITS_MIGRATION')
    # Signup catalogs are public professional nomenclature, with no contact data.
    owner_only(e,'UGECAM')
    rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='UGECAM')
    owner_default=next(r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==rid and not r['aclFormula'])
    update(e,'_grist_ACLRules',owner_default,aclFormula='user.IsLoggedIn is True',aclFormulaParsed=parse_predicate_formula('user.IsLoggedIn is True'),permissionsText='+R-CUD')
    act(e,['AddRecord','_grist_ACLRules',None,{'resource':rid,'aclFormula':'','permissionsText':'-CRUD','rulePos':3}])
    # Exported shared forms are disabled in DEV; Grist document memberships are
    # managed by the host and cannot be validated from a downloaded file.
    for r in records(e,'_grist_Shares'):
        opts=json.loads(r.get('options') or '{}');opts['publish']=False;update(e,'_grist_Shares',r['id'],options=json.dumps(opts))
    widget_urls(e,manifest['targetBase'],{v:manifest['target'].get(k,v) for k,v in manifest['baseline'].items()})
    # Replace baseline base (widget_urls normally handles original production URLs).
    for r in records(e,'_grist_Views_section'):
        text=r.get('options') or ''
        for src,dst in manifest['baseline'].items():text=text.replace(manifest['baselineBase']+dst,manifest['targetBase']+manifest['target'].get(src,dst))
        values={'options':text}
        if r['id'] in [37,40]:values.update(title='DEV — UGECAM → Sites → ESMS / services',tableRef=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='ESMS'))
        update(e,'_grist_Views_section',r['id'],**values)
    # Existing field references in the visible Autodiag custom sections refer to
    # the old table. Remove only the unused custom-view field mappings via engine.
    devref=next(x['id'] for x in records(e,'_grist_Tables') if x['tableId']=='Autodiagnostic_DEV')
    for sid in [150,153,162,209]:
        update(e,'_grist_Views_section',sid,tableRef=devref)
    # Recreate custom-section field mappings against their new table, rather
    # than leaving references to columns of the retained legacy tables.
    for sid in [37,40,150,153,162,209]:
        section=next(r for r in records(e,'_grist_Views_section') if r['id']==sid)
        gone=[r['id'] for r in records(e,'_grist_Views_section_field') if r['parentId']==sid]
        if gone:act(e,['BulkRemoveRecord','_grist_Views_section_field',gone])
        fields=[r for r in records(e,'_grist_Tables_column') if r['parentId']==section['tableRef'] and r['colId']!='manualSort' and not r['colId'].startswith('gristHelper_')]
        for pos,r in enumerate(fields,1):
            act(e,['AddRecord','_grist_Views_section_field',None,{'parentId':sid,'colRef':r['id'],'parentPos':pos}])
    # Repair native Ref displays using the new table's own helpers.
    newcols={r['colId']:r['id'] for r in records(e,'_grist_Tables_column') if r['parentId']==devref}
    update(e,'_grist_Tables_column',newcols['SITE'],visibleCol=next(r['id'] for r in records(e,'_grist_Tables_column') if r['colId']=='NOM' and r['parentId']==next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='SITES')),displayCol=newcols['Site_nom'])
    update(e,'_grist_Tables_column',newcols['UGECAM'],displayCol=newcols['UGECAM_nom'],visibleCol=320)
    tabrefs={t['tableId']:t['id'] for t in records(e,'_grist_Tables')}
    allcols=records(e,'_grist_Tables_column')
    for tableid,field in [('CONTACTS','SITE_PRINCIPAL'),('CONTACTS','SITES_RESP_AIRMES'),('ESMS','SITE'),('DEMANDES_ACCES','SITE_AIRMES'),('DEMANDES_ACCES','SITES_RESP_AIRMES'),('MIGRATION_SITES','SITE')]:
        ref=next(r['id'] for r in allcols if r['parentId']==tabrefs[tableid] and r['colId']==field)
        visible=next(r['id'] for r in allcols if r['parentId']==tabrefs['SITES'] and r['colId']=='NOM')
        update(e,'_grist_Tables_column',ref,visibleCol=visible)
        act(e,['SetDisplayFormula',tableid,None,ref,'$'+field+'.NOM'])
    export(e,source,str(out/'MOAD_2026_DEV_AIRMES_MIGRATION.grist'))
    report={'source_sha256':hashlib.sha256(pathlib.Path(source).read_bytes()).hexdigest(),'sites':len(site_rows),'esms_services':len(es),'contacts':len(records(e,'CONTACTS')),'autodiag_source':len(oldanswers),'autodiag_dev':len(data),'mapped_old_sites':len(oldmap),'issues':len(issues),'answer_conflicts':sum(r['CONFLITS_MIGRATION'] for r in data),'promotion':'BLOQUÉE — arbitrages et recette réelle Grist requis','details':issues}
    (out/'audit-migration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='details'},ensure_ascii=False))

def empty(v):
    return v is None or (isinstance(v,str) and not v.replace('\u00a0',' ').strip()) or (isinstance(v,(list,tuple)) and (not v or all(empty(x) for x in v)))
def answer_keys(cols):
    return [r['colId'] for r in cols if not r['isFormula'] and re.match(r'^(ORG|ECR|ADM|AGE|SOI|PPA|ACC|STA|SOC|PCA|ACU|EVO)',r['colId'])]

if __name__=='__main__':main(*sys.argv[1:])
