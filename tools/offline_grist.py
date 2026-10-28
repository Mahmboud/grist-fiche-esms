"""Grist engine adapter. Run with PYTHONPATH pointing to sandbox/grist and dependencies.

Never opens the source for writes. Exports to a separate copy, retaining physical
columns no longer registered in metadata (some historical documents have them).
"""
import sqlite3, marshal, json, shutil
import engine, actions, useractions, objtypes

def decode(value):
    return objtypes.decode_object(marshal.loads(value)) if isinstance(value, bytes) else value

def load(path):
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    def table(name):
        cur = db.execute('SELECT * FROM "' + name + '"')
        keys = [x[0] for x in cur.description]
        rr = cur.fetchall()
        data = {k: [decode(r[i]) for r in rr] for i,k in enumerate(keys)}
        return actions.TableData(name, data.pop('id'), data)
    eng = engine.Engine()
    eng.load_meta_tables(table('_grist_Tables'), table('_grist_Tables_column'))
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        if not name.startswith('_gristsys_') and name not in ('_grist_Tables','_grist_Tables_column'):
            eng.load_table(table(name))
    db.close()
    eng.load_done()
    return eng

def act(eng, *aa):
    return eng.apply_user_actions([useractions.from_repr(a) for a in aa], {'Email':'dev-migration@invalid','Name':'Migration DEV','Access':'owners','UserID':0,'UserRef':'dev','Origin':None,'SessionID':'dev','IsLoggedIn':True,'ShareRef':None,'LinkKey':{}})

def records(eng, name):
    td = eng.fetch_table(name, formulas=True)
    return [dict(id=i, **{k:v[n] for k,v in td.columns.items()}) for n,i in enumerate(td.row_ids)]

def encode(value, typ):
    value = objtypes.encode_object(value)
    if isinstance(value, (list,tuple)):
        if (typ.startswith('RefList:') or typ in ('ChoiceList','Attachments')) and value and value[0]=='L':
            return json.dumps(value[1:], ensure_ascii=False)
        return marshal.dumps(value,2)
    if isinstance(value, bool):
        return int(value) if typ=='Bool' else marshal.dumps(value,2)
    return value

def export(eng, source, destination):
    shutil.copy2(source, destination)
    db=sqlite3.connect(destination)
    types={(r['parentId'],r['colId']):r['type'] for r in records(eng,'_grist_Tables_column')}
    names={r['tableId']:r['id'] for r in records(eng,'_grist_Tables')}
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '_grist_%'") if not r[0].startswith('_gristsys_')]
    tables+=list(names)
    for name in dict.fromkeys(tables):
        td=eng.fetch_table(name, formulas=True)
        cols=list(td.columns)
        db.execute('CREATE TABLE IF NOT EXISTS "'+name+'" (id INTEGER PRIMARY KEY)')
        existing={r[1] for r in db.execute('PRAGMA table_info("'+name+'")')}
        def typ(k):
            return types.get((names.get(name),k),'Any')
        for k in cols:
            if k not in existing:
                t=typ(k)
                sqltype='BOOLEAN' if t=='Bool' else 'INTEGER' if t.startswith('Ref:') or t=='Int' else 'NUMERIC' if t in ('Numeric','ManualSortPos') or t.startswith(('Date','DateTime:')) else 'TEXT' if t in ('Text','Choice','ChoiceList') or t.startswith('RefList:') else 'BLOB'
                db.execute('ALTER TABLE "'+name+'" ADD COLUMN "'+k+'" '+sqltype)
        # Export engine-authoritative rows; physical unregistered columns survive.
        ids=set(td.row_ids)
        for old, in db.execute('SELECT id FROM "'+name+'"').fetchall():
            if old not in ids:db.execute('DELETE FROM "'+name+'" WHERE id=?',(old,))
        sql='INSERT INTO "'+name+'" (id,'+','.join('"'+k+'"' for k in cols)+') VALUES ('+','.join('?' for _ in range(len(cols)+1))+') ON CONFLICT(id) DO UPDATE SET '+','.join('"'+k+'"=excluded."'+k+'"' for k in cols)
        db.executemany(sql,[(rid,*(encode(td.columns[k][i],typ(k)) for k in cols)) for i,rid in enumerate(td.row_ids)])
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    db.close()
