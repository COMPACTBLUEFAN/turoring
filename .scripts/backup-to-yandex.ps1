# Бэкап всей папки «Обучение 2.0» в Яндекс.Диск одним zip-архивом, старый заменяется.
# Запускает Планировщик заданий Windows (задача «Обучение 2.0 — бэкап в Яндекс.Диск»); можно и вручную:
#   powershell -NoProfile -ExecutionPolicy Bypass -File ".scripts\backup-to-yandex.ps1"
# Архив собирается во временный файл и подменяет старый только после успешной сборки,
# поэтому сбой посреди архивации не портит прошлый бэкап. Итог каждого запуска — в backup.log рядом с архивом.

$ErrorActionPreference = "Stop"
$src  = Split-Path $PSScriptRoot -Parent
$dir  = "C:\Yandex.Disk\Бэкапы"
$zip  = Join-Path $dir "Обучение 2.0.zip"
$tmp  = Join-Path $env:TEMP "Обучение 2.0.backup.zip"
$log  = Join-Path $dir "backup.log"

function Write-Log($msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $msg
    Add-Content -Path $log -Value $line -Encoding UTF8
    # в логе — последние 100 запусков
    $all = Get-Content $log -Encoding UTF8
    if ($all.Count -gt 100) { $all | Select-Object -Last 100 | Set-Content $log -Encoding UTF8 }
}

try {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory($src, $tmp, [IO.Compression.CompressionLevel]::Optimal, $true, [Text.Encoding]::UTF8)

    # проверка: архив открывается и в нём есть AGENTS.md
    $z = [IO.Compression.ZipFile]::OpenRead($tmp)
    $count = $z.Entries.Count
    $ok = $z.Entries | Where-Object { $_.FullName -match "AGENTS\.md$" }
    $z.Dispose()
    if (-not $ok) { throw "в архиве нет AGENTS.md — бэкап не заменён" }

    Move-Item -Path $tmp -Destination $zip -Force
    Write-Log ("ok · файлов: {0} · {1:N1} МБ" -f $count, ((Get-Item $zip).Length / 1MB))
}
catch {
    Write-Log ("ОШИБКА · " + $_.Exception.Message)
    if (Test-Path $tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    exit 1
}
