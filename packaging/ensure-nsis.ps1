# Resolve the actual compiler, including portable and registered installations.
$ErrorActionPreference = 'Stop'

function Find-NsisCompiler {
    $candidates = @(
        $env:MAKENSIS,
        "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
        "$env:ProgramFiles\NSIS\makensis.exe"
    )
    $command = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($key in @('HKLM:\SOFTWARE\NSIS', 'HKLM:\SOFTWARE\WOW6432Node\NSIS', 'HKCU:\SOFTWARE\NSIS')) {
        $registry = Get-Item -LiteralPath $key -ErrorAction SilentlyContinue
        if ($registry) {
            $directory = $registry.GetValue('')
            if ($directory) { $candidates += Join-Path $directory 'makensis.exe' }
        }
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate }
    }
    if ($env:ChocolateyInstall) {
        $packages = Get-ChildItem "$env:ChocolateyInstall\lib\nsis*" -Directory -ErrorAction SilentlyContinue
        foreach ($package in $packages) {
            $compiler = Get-ChildItem $package.FullName -Filter makensis.exe -Recurse -File |
                Select-Object -First 1
            if ($compiler) { return $compiler.FullName }
        }
    }
}

try {
    $compiler = Find-NsisCompiler
    if (-not $compiler) {
        # Package metadata alone does not guarantee that the compiler exists.
        $output = (& choco install nsis --force --no-progress -y 2>&1 | Out-String)
        Write-Host $output
        if ($LASTEXITCODE -ne 0) { throw "Chocolatey failed ($LASTEXITCODE): $output" }
        $compiler = Find-NsisCompiler
    }
    if (-not $compiler) { throw 'NSIS installation did not provide makensis.exe' }
    Write-Host "Using NSIS compiler: $compiler"
    & $compiler /VERSION
    if ($LASTEXITCODE -ne 0) { throw "NSIS compiler could not run ($LASTEXITCODE)" }
    "MAKENSIS=$compiler" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
}
catch {
    $message = $_.ToString().Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Host "::error title=NSIS setup failed::$message"
    exit 1
}
