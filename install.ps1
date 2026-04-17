# Edison Skills installer for Windows
# Usage: .\install.ps1 -User       # copies to %USERPROFILE%\.claude\skills\
#        .\install.ps1 -PluginDir   # prints the --plugin-dir flag to use
param([switch]$User, [switch]$PluginDir)
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($User) {
    $dest = "$env:USERPROFILE\.claude\skills"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Get-ChildItem "$RepoRoot\skills\edison-*" | ForEach-Object {
        $name = $_.Name
        if (Test-Path "$dest\$name") {
            Write-Warning "$name already exists at $dest\$name — overwriting. Customisations will be lost."
        }
        Copy-Item $_.FullName $dest -Recurse -Force
        Write-Host "Installed $name"
    }
    Write-Host "Done. Skills available in Claude Code."
} else {
    Write-Host "Add this flag to your Claude Code command:"
    Write-Host "  --plugin-dir '$RepoRoot'"
}
