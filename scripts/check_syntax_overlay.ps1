$py = "C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe"
$script = @"
import ast, sys
try:
    src = open(r'Q:/Claudework/bridge base/rpa_overlay.py', encoding='utf-8').read()
    ast.parse(src)
    print('SYNTAX_OK')
except SyntaxError as e:
    print(f'SYNTAX_ERROR: {e}')
    sys.exit(1)
"@
$tmppy = [System.IO.Path]::GetTempFileName() + ".py"
[System.IO.File]::WriteAllText($tmppy, $script, [System.Text.Encoding]::UTF8)
& $py $tmppy
Remove-Item $tmppy -Force
