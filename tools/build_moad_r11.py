"""Prepare fresh URLs only; the Grist document must be an explicitly supplied copy."""
import pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'widgets/moad-20261030-r11';OUT.mkdir(exist_ok=True)
for name in ['liste-finess.html','sites-esms.html','administration-sauvegardes.html','moad-api.js','identifiants.js','finess.js','public-sync.js','public-data-ui.js']:
 (OUT/name).write_bytes((ROOT/'widgets/moad-20261029-r7'/name).read_bytes())
(OUT/'moad-ref-config.js').write_bytes((ROOT/'widgets/moad-20261029-r9/moad-ref-config.js').read_bytes())
s=(ROOT/'widgets/moad-20261029-r10/mon-acces.html').read_text()
s=s.replace('Bienvenue sur la plateforme MOAD DUI','Bienvenue sur la plateforme Grist du secteur MS UGECAM')
start='<p>Cette plateforme accompagne l’expérimentation menée par la '
a=s.index(start);b=s.index('</p>',a)+4
s=s[:a]+'''<p>Cette plateforme est en expérimentation par la <strong>DNGU et l’équipe DUI</strong>. Elle permet de recueillir l’autodiagnostic des établissements sur les usages du DUI Airmes, de consulter les informations sur les sites et les ESMS/services issues d’Airmes ou de data.gouv.fr. Une expérimentation est également à venir sur l’exposition aux UGECAM d’indicateurs d’activités des ESMS depuis les données d’Airmes.</p>'''+s[b:]
s=s.replace('gérer l’inscription, le rattachement et les habilitations MOAD.','recueillir les réponses à l’autodiagnostic sur les usages du DUI Airmes ; mettre à disposition des données relatives aux établissements du Groupe UGECAM, notamment leur arborescence, leurs sites et ESMS/services ainsi que leurs responsables et référents professionnels ; gérer les accès nécessaires à ces usages.')
(OUT/'mon-acces.html').write_text(s)
s=(OUT/'liste-finess.html').read_text()
s=s.replace('<select id="ugecam"', '<select id="category" aria-label="Catégorie FINESS"><option value="">Toutes les catégories</option></select><select id="ugecam"',1)
s=s.replace("owner:false,busy:false","owner:false,busy:false,esms:[]")
s=s.replace("const effective=r=>", "const categoryKey=r=>String(r.CATEGORIE_CODE||'').trim()||'__unknown__';\nconst effective=r=>")
s=s.replace("sector=$('sector').value;", "sector=$('sector').value,category=$('category').value;",1)
s=s.replace("(!sector||r.SECTEUR===sector)&&", "(!sector||r.SECTEUR===sector)&&(!category||categoryKey(r)===category)&&")
s=s.replace("[S.catalogue,S.u,S.sites]=await Promise.all([ft('FINESS_CATALOGUE'),ft('UGECAM'),ft('SITES')])", "[S.catalogue,S.u,S.sites,S.esms]=await Promise.all([ft('FINESS_CATALOGUE'),ft('UGECAM'),ft('SITES'),ft('ESMS')])")
s=s.replace("$('sector').value=sector;const dates=", "$('sector').value=sector;const category=$('category').value;const categories=new Map();S.catalogue.map(effective).forEach(r=>{const key=categoryKey(r);if(!categories.has(key))categories.set(key,r.CATEGORIE||'Catégorie non renseignée')});$('category').innerHTML='<option value=\"\">Toutes les catégories</option>'+[...categories].sort(([a],[b])=>a.localeCompare(b,'fr',{numeric:true})).map(([code,label])=>`<option value=\"${esc(code)}\">${esc(code==='__unknown__'?label:code+' — '+label)}</option>`).join('');$('category').value=categories.has(category)?category:'';const dates=")
s=s.replace("['search','ugecam','attachment','sector','active']", "['search','ugecam','attachment','sector','category','active']")
s=s.replace("${esc(S.sites.find(s=>+s.id===+r.SITE)?.NOM||r.RATTACHEMENT||'À rattacher')}</td>", "${esc(S.sites.find(s=>+s.id===+r.SITE)?.NOM||r.RATTACHEMENT||'À rattacher')}${!+r.SITE?'<br><small>'+esc(attachmentReason(r))+'</small>':''}</td>")
s=s.replace("function render(){", """function attachmentReason(r){if(String(r.RATTACHEMENT||'').includes('multiples'))return 'Plusieurs sites portent ce FINESS : arbitrage nécessaire.';const linked=S.esms.filter(e=>[e.FINESS,e.FINESS_NORMALISE,...(Array.isArray(e.FINESS_CODES)?e.FINESS_CODES:[])].some(v=>String(v)===String(r.FINESS)));return linked.length?'Un ESMS/service porte ce FINESS, mais son site reste à renseigner.':'FINESS de cette UGECAM identifié dans la source publique, sans correspondance FINESS dans les ESMS/services de la base.'}
function render(){""")
s=s.replace('<p class="muted">Même périmètre de visibilité', '<details class="panel"><summary>Pourquoi certains FINESS sont-ils à rattacher ?</summary><p>La source publique permet d’identifier une UGECAM grâce à son FINESS juridique. Elle ne décrit pas les sites de niveau 2 Airmes. Le rattachement à un site est déduit des ESMS/services de cette base qui portent le même FINESS : une correspondance absente ou plusieurs sites possibles doivent être vérifiés par le propriétaire.</p><p>La liste comprend aussi des établissements sanitaires ou des structures absentes de l’arborescence Airmes importée. Aucun site n’est attribué sur la seule ressemblance d’un nom.</p></details><p class="muted">Même périmètre de visibilité')
s=s.replace('</style>','#category{max-width:330px} </style>')
(OUT/'liste-finess.html').write_text(s)
s=(OUT/'sites-esms.html').read_text()
s=s.replace('Établissements à rapprocher (${unlinked.length})</summary>', 'Établissements à rapprocher (${unlinked.length})</summary><p class="muted" style="font-size:12px;line-height:1.5">Ces établissements ont été repris de l’ancienne liste ESMS / FINESS sans correspondance unique avec un site Airmes. Leur rattachement se vérifie dans Administration → Sauvegarde &amp; restauration → Référentiels.</p>')
(OUT/'sites-esms.html').write_text(s)
print(OUT)
