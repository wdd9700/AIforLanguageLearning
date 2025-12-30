import sys, traceback
print(sys.version)
print('import cosyvoice...')
try:
    import cosyvoice
    print('cosyvoice import ok')
    from cosyvoice.cli.cosyvoice import CosyVoice2
    print('CosyVoice2 class ok')
except Exception as e:
    print('ERROR during import:', repr(e))
    traceback.print_exc()
    raise SystemExit(1)
