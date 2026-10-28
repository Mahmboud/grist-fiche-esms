"""Create isolated widgets; never writes a production path."""
import pathlib,json,re
root=pathlib.Path(__file__).resolve().parents[1]
dest=root/'dev/moad-airmes-20261028'
active={'admin-exports-excel-v1.html', 'autodiagnostic-questionnaire-v4.html', 'admin-demandes-acces-v1.html', 'admin-maintenance-v1.html', 'airmes-synthese-v1.html', 'admin-guide-v1.html', 'moad-ref-config.js', 'v5.html', 'acces-moad-v1.html', 'autodiagnostic-synthese-v3.html', 'airmes-arborescence-v1.html', 'contacts-annuaire-v2.html', 'autodiagnostic-historique-v1.html', 'admin-nouveau-referent-v1.html'}
prod=[p for p in root.iterdir() if p.name in active]
special={'v5.html':'v6-dev.html','autodiagnostic-questionnaire-v4.html':'autodiagnostic-questionnaire-v5-dev.html','autodiagnostic-synthese-v3.html':'autodiagnostic-synthese-v4-dev.html','acces-moad-v1.html':'acces-moad-v2-dev.html'}
mapping={p.name:special.get(p.name,p.stem+'-dev'+p.suffix) for p in prod}
manifest={'baselineBase':'https://mahmboud.github.io/grist-fiche-esms/dev/moad-airmes-20261028/reference/','targetBase':'https://mahmboud.github.io/grist-fiche-esms/dev/moad-airmes-20261028/target/','baseline':mapping,'target':mapping}
dest.mkdir(parents=True,exist_ok=True)
(dest/'widgets.json').write_text(json.dumps(manifest,indent=2))
for mode in ('reference','target'):
    d=dest/mode;d.mkdir(exist_ok=True)
    for p in prod:
        if mode=='target' and (d/mapping[p.name]).exists():continue
        text=p.read_text()
        for src,target in mapping.items():
            text=text.replace('https://mahmboud.github.io/grist-fiche-esms/'+src,manifest['baselineBase' if mode=='reference' else 'targetBase']+target)
        if p.suffix=='.html':text=text.replace('<body>','<body><div style="background:#fef3c7;color:#713f12;padding:8px;font:700 12px system-ui">DEV · '+('Référence conservée' if mode=='reference' else 'Migration Airmes — recette requise')+'</div>',1)
        if mode=='target':
            # Legacy administration/export widgets must not operate on the wrong
            # model. They remain available in the reference DEV document.
            if p.name.startswith(('admin-maintenance','admin-exports','admin-nouveau','airmes-synthese')):
                text='<!doctype html><html lang="fr"><meta charset="utf-8"><body style="font:16px system-ui;padding:24px"><h2>DEV — module en attente de recette</h2><p>Cette fonction reste disponible dans la copie DEV de référence. Elle sera adaptée après arbitrage des correspondances de sites.</p></body></html>'
            elif p.name.startswith('autodiagnostic-'):
                text=text.replace("'Autodiagnostic'","'Autodiagnostic_DEV'").replace("'Autodiagnostic_Historique'","'Autodiagnostic_Historique_DEV'")
                text=text.replace('gristHelper_Display2','UGECAM_nom').replace('gristHelper_Display','Site_nom')
                # Read profile from this user's own contact, never the newest
                # request belonging to another person when running as owner.
                start=text.find('async function detectSiege(){');end=text.find('\nfunction fieldInfo',start)
                if start>=0 and end>start:
                    text=text[:start]+"async function detectSiege(){try{const me=await grist.docApi.getAccessToken({readOnly:true});/* ACL still determines the actual perimeter. */const cs=await ft('CONTACTS');if(cs.length===1){state.isSiege=cs[0].SIEGE===true;state.isDngu=cs[0].DNGU===true}}catch{state.isSiege=false;state.isDngu=false}}"+text[end:]
                    text=text.replace("const me=await grist.docApi.getAccessToken({readOnly:true});/* ACL still determines the actual perimeter. */",'')
            elif p.name=='contacts-annuaire-v2.html':
                text=text.replace('SITES_nomenclature_UGECAM','SITE_PRINCIPAL').replace("sites:'SITE_PRINCIPAL'","sites:'SITES'")
        (d/mapping[p.name]).write_text(text)
print(dest)
