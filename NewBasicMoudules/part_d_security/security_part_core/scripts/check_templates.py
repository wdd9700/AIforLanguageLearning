import os

# This script was moved under security_part/scripts so paths are relative to security_part
p = os.path.join(os.path.dirname(__file__), '..', 'templates')
errors = []
for root, dirs, files in os.walk(p):
    for fn in files:
        fp = os.path.join(root, fn)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                f.read()
        except Exception as e:
            errors.append((fp, type(e).__name__, str(e)))
if not errors:
    print('ALL_OK')
else:
    for fp, etype, msg in errors:
        print(fp + ' | ' + etype + ' | ' + msg)
