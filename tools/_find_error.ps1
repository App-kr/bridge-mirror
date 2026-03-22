[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Get-ChildItem "Q:\" -Filter "*에러*" | ForEach-Object { Write-Output $_.FullName }
