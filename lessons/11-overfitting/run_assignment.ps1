param([string]$PythonExe = 'python')

$ErrorActionPreference = 'Stop'
& $pythonExe "$PSScriptRoot\scripts\complete_assignment.py"
if ($LASTEXITCODE -ne 0) { throw 'Experiment execution failed.' }
& $pythonExe "$PSScriptRoot\scripts\write_analysis.py"
if ($LASTEXITCODE -ne 0) { throw 'Analysis generation failed.' }
