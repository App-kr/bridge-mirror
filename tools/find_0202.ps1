Get-ChildItem "Q:\" | Where-Object { $_.Name -like "0202*" } |
    Select-Object Name, FullName, Extension, Length, LastWriteTime | Format-List
