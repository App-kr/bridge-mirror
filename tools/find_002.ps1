Get-ChildItem "Q:\" | Where-Object { $_.Name -like "*002*" -or $_.Name -like "*에러*" } | Select-Object Name, FullName, Extension
