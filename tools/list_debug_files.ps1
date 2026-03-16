Get-ChildItem "Q:\Claudework\bridge base\tools\" -Filter "*.ps1" |
    Where-Object { $_.LastWriteTime -gt [datetime]"2026-03-14 06:00" } |
    Sort-Object LastWriteTime |
    Select-Object Name, LastWriteTime |
    Format-Table -AutoSize
