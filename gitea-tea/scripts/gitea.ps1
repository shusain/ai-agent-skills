<#
.SYNOPSIS
Runs the installed Windows tea CLI with the shared saved-login directory.
.DESCRIPTION
Installed as C:/Users/shaun/AppData/Local/Programs/tea/gitea.ps1.
Uses C:/Users/shaun/.config/tea/config.yml, outside packaged PowerShell/Python
AppData redirection. Forwards arguments and pipeline input to tea.exe, restores
XDG_CONFIG_HOME, and returns tea's exit code. tea performs any requested remote
operation and may update its config for login/settings commands. This wrapper
does not read, print, copy, or discover credentials.
#>
$taskTea = 'C:\Users\shaun\AppData\Local\Programs\tea\tea.exe'
$taskConfigRoot = 'C:\Users\shaun\.config'
$taskConfigFile = Join-Path $taskConfigRoot 'tea/config.yml'
if (-not (Test-Path -LiteralPath $taskTea -PathType Leaf)) {
    throw 'Desktop tea is not installed at the configured path'
}
if (-not (Test-Path -LiteralPath $taskConfigFile -PathType Leaf)) {
    throw "Saved tea configuration is not visible at $taskConfigFile. Run the gitea-tea skill's Test-TeaLogin.ps1 in this shell."
}
$taskPreviousConfig = $env:XDG_CONFIG_HOME
$taskTeaExit = 1
try {
    $env:XDG_CONFIG_HOME = $taskConfigRoot
    if ($MyInvocation.ExpectingInput) { $input | & $taskTea @args }
    else { & $taskTea @args }
    $taskTeaExit = $LASTEXITCODE
} finally {
    if ($null -eq $taskPreviousConfig) {
        Remove-Item Env:\XDG_CONFIG_HOME -ErrorAction SilentlyContinue
    } else {
        $env:XDG_CONFIG_HOME = $taskPreviousConfig
    }
}
exit $taskTeaExit
