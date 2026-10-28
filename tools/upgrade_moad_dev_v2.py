"""Add site/UGECAM presentation data and route a new DEV copy to v2 widgets.

Usage: upgrade_moad_dev_v2.py input.grist output.grist
The input is never modified. No legacy table or answer is removed.
"""
import sys,json,math,re
from offline_grist import load,act,records,export,objtypes
from migrate_moad_dev import col,update,acl

def upgrade(source,destination):
    e=load(source)
    for name,role in [('DG_NOMS',53),('RESP_MS_NOMS',47),('RSI_NOMS',49),('QUALITE_NOMS',48)]:
        formula=f'''cs = [c for c in CONTACTS.all if c.FONCTION.id == {role} and (c.UGECAM.id == $id or (not c.UGECAM and c.SITE_PRINCIPAL.UGECAM.id == $id))]
siege = [c for c in cs if c.SIEGE]
return "\\n".join(sorted(set(c.NOM_PRENOM_contact.strip() for c in (siege or cs) if c.NOM_PRENOM_contact.strip())))'''
        col(e,'UGECAM',name,'Text',formula)
    gate="user.demande_acces.STATUT == 'Validé' and (user.droits_supp.ACCES_LISTE_ESMS is True or user.droits_supp.ACCES_ARBORESCENCE is True) and (user.droits_supp.DNGU is True or rec.id == user.droits_supp.UGECAM)"
    acl(e,'UGECAM',[('user.Access == OWNER','+CRUD'),(gate,'+R-CUD'),('','-CRUD')],'DG_NOMS,RESP_MS_NOMS,RSI_NOMS,QUALITE_NOMS')
    # Store only vetted public address/coordinate candidates. Business names
    # still come exclusively from Airmes; an address is not a site identity.
    mapping={r['ANCIEN_SITE']:r['SITE'] for r in records(e,'MIGRATION_SITES')}
    locations={r['id']:[] for r in records(e,'SITES')}
    def coordinate(v,limit):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and abs(v)<=limit
    legacy={r['id']:r for r in records(e,'ESMS_Liste_UGECAM_')}
    for r in legacy.values():
        sid=mapping.get(r['SITES_nomenclature_UGECAM'])
        if not sid:continue
        lat,lon=r.get('Latitude'),r.get('Longitude');address=str(r.get('ADRESSE') or '').strip()
        valid=coordinate(lat,90) and coordinate(lon,180) and (lat!=0 or lon!=0)
        if not address and not valid:continue
        loc={'adresse':address,'latitude':lat if valid else None,'longitude':lon if valid else None}
        if loc not in locations[sid]:locations[sid].append(loc)
    col(e,'SITES','LOCALISATIONS_JSON','Text')
    for sid,locs in locations.items():update(e,'SITES',sid,LOCALISATIONS_JSON=json.dumps(locs,ensure_ascii=False))
    resource=next(r for r in records(e,'_grist_ACLResources') if r['tableId']=='SITES' and r['colIds']=='DIRECTION_NOMS')
    update(e,'_grist_ACLResources',resource['id'],colIds='DIRECTION_NOMS,LOCALISATIONS_JSON')
    col(e,'ESMS','Latitude','Numeric');col(e,'ESMS','Longitude','Numeric')
    for r in records(e,'ESMS'):
        candidates=[legacy[i] for i in (r['ESMS_LEGACY_IDS'] or []) if i in legacy]
        matches=[x for x in candidates if (r.get('FINESS') and r['FINESS']==x['FINESS']) or (r.get('ADRESSE') and r['ADRESSE']==x['ADRESSE'])]
        coords={(x.get('Latitude'),x.get('Longitude')) for x in matches if coordinate(x.get('Latitude'),90) and coordinate(x.get('Longitude'),180) and (x['Latitude']!=0 or x['Longitude']!=0)}
        if len(coords)==1:
            lat,lon=next(iter(coords));update(e,'ESMS',r['id'],Latitude=lat,Longitude=lon)
    paths={'v6-dev.html':'v6-dev2.html','airmes-arborescence-v1-dev.html':'airmes-arborescence-v2-dev.html','admin-maintenance-v1-dev.html':'admin-maintenance-v2-dev.html','admin-nouveau-referent-v1-dev.html':'admin-nouveau-referent-v2-dev.html','admin-exports-excel-v1-dev.html':'admin-exports-excel-v2-dev.html'}
    for r in records(e,'_grist_Views_section'):
        options=r.get('options') or ''
        for old,new in paths.items():options=options.replace('/target/'+old,'/target/'+new)
        if options!=r.get('options'):update(e,'_grist_Views_section',r['id'],options=options)
    export(e,source,destination)
    print(json.dumps({'sites':len(locations),'sites_avec_localisation':sum(bool(x) for x in locations.values()),'localisations':sum(map(len,locations.values())),'output':destination},ensure_ascii=False))
if __name__=='__main__':upgrade(*sys.argv[1:])
