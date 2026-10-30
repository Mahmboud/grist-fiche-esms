"""Apply new widget URLs to a user-supplied current document, without data changes."""
import sys,json,pathlib,re
from offline_grist import load,records,export,objtypes
from migrate_moad_dev import update
BASE='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261030-r11/'
WIDGETS={205:'mon-acces.html',255:'liste-finess.html',40:'sites-esms.html',212:'administration-sauvegardes.html'}
def main(src,dst):
 if pathlib.Path(src).resolve()==pathlib.Path(dst).resolve():raise ValueError('Une nouvelle copie est obligatoire.')
 e=load(src);tables={t['tableId'] for t in records(e,'_grist_Tables')}
 assert {'GristHidden_SITES','GristHidden_UGECAM','CONTACTS','ESMS','Autodiagnostic','FINESS_CATALOGUE','ADMIN_OUTILS'}<=tables,'Modèle de référence attendu absent'
 before={t:records(e,t) for t in tables};sections={s['id']:s for s in records(e,'_grist_Views_section')}
 for sid,name in WIDGETS.items():
  assert sid in sections,(sid,'Section absente')
  old=sections[sid]['options'] or ''
  expr=r'https://mahmboud\.github\.io/grist-fiche-esms/widgets/moad-[^/]+/'+re.escape(name)
  new,count=re.subn(expr,BASE+name,old)
  assert count==1,(sid,'URL source non reconnue')
  update(e,'_grist_Views_section',sid,options=new)
 for t,rr in before.items():
  after=records(e,t);assert len(rr)==len(after),t
  for a,b in zip(rr,after):
   for k,v in a.items():assert objtypes.equal_encoding(v,b[k]),(t,a['id'],k)
 export(e,src,dst)
 print(json.dumps(dict(output=dst,sections=list(WIDGETS),data_preserved=True),ensure_ascii=False))
if __name__=='__main__':main(*sys.argv[1:])
