param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$researchPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $researchPython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Creating project environment failed.' }
}
if (-not $SkipInstall) {
    & $researchPython -m pip install -r requirements-research.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
$researchScripts = @('run_research.py', 'verify_sources.py', 'make_figures.py', 'make_report.py', 'build_academic_paper.py', 'build_research_presentation.py', 'export_and_check_presentation.py', 'audit_research.py')
foreach ($researchScript in $researchScripts) {
    Write-Host "Running $researchScript"
    & $researchPython -X utf8 (Join-Path 'scripts' $researchScript)
    if ($LASTEXITCODE -ne 0) { throw "Failed: $researchScript" }
}
Write-Host 'Completed. Open outputs/presentation/ensemble_report.pptx.'
