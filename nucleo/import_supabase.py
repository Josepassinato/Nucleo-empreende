import urllib.request, urllib.error, json, re

URL = "https://armabaquiyqmdgwflslq.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFybWFiYXF1aXlxbWRnd2Zsc2xxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjQ3MDAwMSwiZXhwIjoyMDgyMDQ2MDAxfQ.9ffNOxRhY1X2QmVg7YfMcIWv_UHLIFmGbZxCEaZdpCQ"

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}

with open("/root/vibeschool_dados.sql") as f:
    full_sql = f.read()

# Split into statements
stmts = re.split(r';\s*\n', full_sql)
ok = 0
err = 0
errors = []

for stmt in stmts:
    stmt = stmt.strip()
    if not stmt or stmt.startswith('--'):
        continue
    
    # Only process INSERT statements
    m = re.match(r"INSERT INTO public\.(\w+)\s*\(([^)]+)\)\s*VALUES\s*(.*)", stmt, re.DOTALL)
    if not m:
        continue
    
    table = m.group(1)
    cols = [c.strip() for c in m.group(2).split(",")]
    values_block = m.group(3).strip().rstrip(';')
    
    # Split rows
    rows = []
    # Use a simple approach: split by '),\n(' 
    raw_rows = re.split(r"\)\s*,\s*\n\s*\(", values_block)
    
    for raw in raw_rows:
        raw = raw.strip().lstrip('(').rstrip(')')
        # Parse values - simple CSV-like with SQL quoting
        vals = []
        cur = ''
        in_q = False
        i = 0
        while i < len(raw):
            ch = raw[i]
            if not in_q and ch == "'":
                in_q = True
                cur += ch
            elif in_q and ch == "'" and i+1 < len(raw) and raw[i+1] == "'":
                cur += "''"
                i += 1
            elif in_q and ch == "'":
                in_q = False
                cur += ch
            elif not in_q and ch == ',':
                vals.append(cur.strip())
                cur = ''
            else:
                cur += ch
            i += 1
        vals.append(cur.strip())
        
        obj = {}
        for ci, col in enumerate(cols):
            if ci < len(vals):
                v = vals[ci]
                if v.upper() == 'NULL':
                    obj[col] = None
                elif v.lower() == 'true':
                    obj[col] = True
                elif v.lower() == 'false':
                    obj[col] = False
                elif v.startswith("'") and v.endswith("'"):
                    obj[col] = v[1:-1].replace("''", "'")
                else:
                    try:
                        obj[col] = int(v)
                    except:
                        try:
                            obj[col] = float(v)
                        except:
                            obj[col] = v
        rows.append(obj)
    
    # POST to Supabase
    body = json.dumps(rows).encode()
    req = urllib.request.Request(f"{URL}/rest/v1/{table}", data=body, headers=headers, method="POST")
    try:
        urllib.request.urlopen(req)
        ok += len(rows)
        print(f"OK {table}: {len(rows)} rows")
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        err += len(rows)
        errors.append(f"{table}: {msg}")
        print(f"ERR {table}: {msg[:120]}")

print(f"\nResumo: {ok} inseridos, {err} erros")
for e in errors[:10]:
    print(f"  {e[:200]}")
