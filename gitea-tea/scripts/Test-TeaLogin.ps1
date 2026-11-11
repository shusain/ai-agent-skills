<#
.SYNOPSIS
Reports tea profile visibility without reading or displaying credentials.
.DESCRIPTION
Run in the failing Windows Codex shell. Outputs JSON with process identity,
configuration-path metadata, parent executable paths, and saved login names.
Opens the config only to check read access and file length; never reads its
contents. Calls the installed wrapper's local login-list operation. Does not
change credentials, permissions, persistent environment settings, or remote state.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$teaWrapper = 'C:/Users/shaun/AppData/Local/Programs/tea/gitea.ps1'
$teaConfig = 'C:/Users/shaun/.config/tea/config.yml'
$report = [ordered]@{
    Identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    PowerShell = (Get-Process -Id $PID).Path
    PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    ConfigPath = $teaConfig
    XdgConfigHome = $env:XDG_CONFIG_HOME
    LocalAppData = $env:LOCALAPPDATA
    UserProfile = $env:USERPROFILE
    ConfigReadable = $false
    ConfigBytes = $null
    ConfigError = $null
    WrapperExists = [IO.File]::Exists($teaWrapper)
    LoginNames = @()
    LoginExitCode = $null
    LoginError = $null
    Ancestors = @()
}

$configStream = $null
try {
    $configStream = [IO.File]::Open($teaConfig, [IO.FileMode]::Open,
        [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $report.ConfigReadable = $true
    $report.ConfigBytes = $configStream.Length
} catch {
    $report.ConfigError = $_.Exception.GetBaseException().GetType().Name
} finally {
    if ($null -ne $configStream) { $configStream.Dispose() }
}

try {
    $loginJson = & $teaWrapper logins list --output json
    $report.LoginExitCode = $LASTEXITCODE
    if ($LASTEXITCODE -eq 0) {
        $report.LoginNames = @($loginJson | ConvertFrom-Json | ForEach-Object { $_.name })
    }
} catch {
    $report.LoginError = $_.Exception.GetBaseException().GetType().Name
}

try {
    $ancestorId = $PID
    for ($depth = 0; $depth -lt 8 -and $ancestorId -gt 0; $depth++) {
        $ancestor = Get-CimInstance Win32_Process -Filter "ProcessId=$ancestorId"
        if ($null -eq $ancestor) { break }
        $report.Ancestors += [ordered]@{
            Name = $ancestor.Name
            Executable = $ancestor.ExecutablePath
        }
        $ancestorId = $ancestor.ParentProcessId
    }
} catch {
    # Ancestry is optional when the shell cannot query process metadata.
}

$report | ConvertTo-Json -Depth 5
