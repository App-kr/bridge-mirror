Get-ChildItem "Q:\" -Recurse -Depth 1 -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "002|에러클로드" } |
    Select-Object Name, FullName
