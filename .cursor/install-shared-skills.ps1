param(
  [Parameter(Mandatory = $false)]
  [string[]]$Projects,

  [Parameter(Mandatory = $false)]
  [string]$ProjectsFile,

  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Resolve-ProjectList {
  param(
    [string[]]$Projects,
    [string]$ProjectsFile
  )

  $list = New-Object System.Collections.Generic.List[string]

  if ($Projects) {
    foreach ($p in $Projects) {
      if (-not [string]::IsNullOrWhiteSpace($p)) { $list.Add($p.Trim()) }
    }
  }

  if ($ProjectsFile) {
    if (-not (Test-Path -LiteralPath $ProjectsFile)) {
      throw "ProjectsFile not found: $ProjectsFile"
    }
    $lines = Get-Content -LiteralPath $ProjectsFile -Encoding UTF8
    foreach ($line in $lines) {
      $t = $line.Trim()
      if ($t.Length -eq 0) { continue }
      if ($t.StartsWith('#')) { continue }
      $list.Add($t)
    }
  }

  return @($list | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
}

function Backup-IfNeeded {
  param(
    [string]$Path
  )

  if (-not (Test-Path -LiteralPath $Path)) { return }

  $item = Get-Item -LiteralPath $Path -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { return }

  if (-not $Force) {
    throw "Target exists and is not a link. Re-run with -Force to backup and replace: $Path"
  }

  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $backup = "$Path.bak.$stamp"
  Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $backup)
}

function Ensure-Junction {
  param(
    [string]$Target,
    [string]$Source
  )

  if (Test-Path -LiteralPath $Target) {
    $item = Get-Item -LiteralPath $Target -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { return }
    Backup-IfNeeded -Path $Target
  }

  $parent = Split-Path -Parent $Target
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
  }

  if (-not (Test-Path -LiteralPath $Source)) {
    throw "Source not found: $Source"
  }

  cmd /c "mklink /J ""$Target"" ""$Source""" | Out-Null
}

$sourceSkills = Join-Path $PSScriptRoot 'skills'
$sourceRules = Join-Path $PSScriptRoot 'rules'

$projectList = Resolve-ProjectList -Projects $Projects -ProjectsFile $ProjectsFile
if (-not $projectList -or $projectList.Count -eq 0) {
  throw "No projects provided. Use -Projects <paths...> or -ProjectsFile <utf8 text file>."
}

foreach ($proj in $projectList) {
  if (-not (Test-Path -LiteralPath $proj)) {
    Write-Warning "Skip missing project path: $proj"
    continue
  }

  $cursorDir = Join-Path $proj '.cursor'
  if (-not (Test-Path -LiteralPath $cursorDir)) {
    New-Item -ItemType Directory -Path $cursorDir | Out-Null
  }

  Ensure-Junction -Target (Join-Path $cursorDir 'skills') -Source $sourceSkills
  Ensure-Junction -Target (Join-Path $cursorDir 'rules') -Source $sourceRules

  Write-Host "OK: $proj"
}

