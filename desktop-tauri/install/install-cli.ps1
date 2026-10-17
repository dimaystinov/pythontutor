param([Parameter(Mandatory=$true)][string]$SourceCli, [switch]$Remove)
$ErrorActionPreference = 'Stop'
$bin = Join-Path $env:LOCALAPPDATA 'PythonTutor\bin'
$parts = @(([Environment]::GetEnvironmentVariable('Path', 'User') -split ';') | Where-Object { $_ })
if ($Remove) {
    $parts = @($parts | Where-Object { $_.TrimEnd('\') -ine $bin.TrimEnd('\') })
    Remove-Item (Join-Path $bin 'opencode.exe') -Force -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path $bin -Force | Out-Null
    Copy-Item -LiteralPath $SourceCli -Destination (Join-Path $bin 'opencode.exe') -Force
    if (-not ($parts | Where-Object { $_.TrimEnd('\') -ieq $bin.TrimEnd('\') })) { $parts += $bin }
}
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
# Notify Explorer so newly opened terminals inherit the new user PATH.
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class TutorEnvironment {
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, UIntPtr w, string l, uint f, uint t, out UIntPtr r);
}
'@
$result = [UIntPtr]::Zero
[void][TutorEnvironment]::SendMessageTimeout([IntPtr]0xffff, 0x1a, [UIntPtr]::Zero, 'Environment', 2, 5000, [ref]$result)
