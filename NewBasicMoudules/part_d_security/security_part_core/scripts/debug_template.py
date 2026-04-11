import os
from jinja2 import Environment, FileSystemLoader

# This script was moved under security_part/scripts so paths are relative to security_part
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
loader = FileSystemLoader(p, encoding='utf-8')
env = Environment(loader=loader)
name='login.html'
try:
    env.get_template(name)
    print("Loaded OK")
except UnicodeDecodeError as e:
    print("UnicodeDecodeError:", e)
    for sp in loader.searchpath:
        fp = os.path.join(sp, name)
        if os.path.exists(fp):
            print("Found file:", fp)
            b = open(fp,'rb').read()
            pos = getattr(e, 'start', None)
            if pos is None:
                try:
                    b.decode('utf-8')
                except UnicodeDecodeError as e2:
                    pos = e2.start
            start = max(0, (pos or 0) - 40)
            end = min(len(b), (pos or 0) + 40)
            print("Byte context:", b[start:end])
            print("Byte context repr:", repr(b[start:end]))
            try:
                print("Decoded with gbk:", b.decode('gbk')[:400])
            except Exception as e3:
                print("GBK decode failed:", e3)
            break
except Exception as ex:
    print('Other exception:', type(ex), ex)
