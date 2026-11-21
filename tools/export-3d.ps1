# Regenerate STEP models and PNG renders for every KiCad board in this repo.
# Run from the repo root in PowerShell:  .\tools\export-3d.ps1
# STL files are converted from the STEP files separately.

$ErrorActionPreference = "Stop"
$cli = Get-ChildItem "C:\Program Files\KiCad\*\bin\kicad-cli.exe" |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $cli) { throw "kicad-cli.exe not found under C:\Program Files\KiCad" }
Write-Host "Using $($cli.FullName)"

Get-ChildItem -Recurse -Filter *.kicad_pcb | ForEach-Object {
    $pcb  = $_.FullName
    $name = $_.BaseName
    $dir  = $_.DirectoryName
    New-Item -ItemType Directory -Force "$dir\3d"   | Out-Null
    New-Item -ItemType Directory -Force "$dir\docs" | Out-Null

    Write-Host "== $name"
    & $cli.FullName pcb export step --force --subst-models --no-dnp `
        --include-silkscreen --include-soldermask --include-pads --include-tracks `
        -o "$dir\3d\$name.step" $pcb
    foreach ($side in "top", "bottom") {
        & $cli.FullName pcb render --side $side --quality high `
            --width 1600 --height 1200 --background transparent `
            --perspective --rotate "-30,0,-20" `
            -o "$dir\docs\$name-$side.png" $pcb
    }
}
