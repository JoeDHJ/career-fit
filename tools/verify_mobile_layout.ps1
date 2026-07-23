param(
    [string]$AtlasUrl = "http://127.0.0.1:8765",
    [string]$CareerFitUrl = "http://127.0.0.1:8766",
    [int]$Width = 390,
    [int]$Height = 844
)

$ErrorActionPreference = "Stop"
$session = "career-fit-mobile-check-$PID"
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) $session
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

function Invoke-PlaywrightCli {
    param([string[]]$Arguments)

    $output = & npx --yes --package @playwright/cli playwright-cli "--session=$session" @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Playwright CLI failed: $($output -join [Environment]::NewLine)"
    }
    return ($output -join [Environment]::NewLine)
}

function Read-PlaywrightJson {
    param([string]$Output)

    $lines = $Output -split "`r?`n"
    foreach ($line in $lines) {
        try {
            $value = $line.Trim() | ConvertFrom-Json
            if ($value -is [string]) {
                return ($value | ConvertFrom-Json)
            }
            return $value
        }
        catch {
        }
    }
    throw "Playwright did not return a JSON measurement: $Output"
}

function Assert-NoHorizontalOverflow {
    param([string]$PageName, [object]$Measurement)

    if ($Measurement.width -ne $Width) {
        throw "$PageName viewport width was $($Measurement.width), expected $Width."
    }
    if ($Measurement.scrollWidth -gt $Measurement.clientWidth) {
        throw "$PageName has horizontal overflow: scrollWidth=$($Measurement.scrollWidth), clientWidth=$($Measurement.clientWidth)."
    }
}

try {
    Push-Location $tempDir

    Invoke-PlaywrightCli @("open", $AtlasUrl) | Out-Null
    Invoke-PlaywrightCli @("resize", "$Width", "$Height") | Out-Null
    $atlasMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        'JSON.stringify({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth})'
    ))
    Assert-NoHorizontalOverflow "AI Labor Atlas" $atlasMeasurement
    Invoke-PlaywrightCli @("close") | Out-Null

    Invoke-PlaywrightCli @("open", $CareerFitUrl) | Out-Null
    Invoke-PlaywrightCli @("resize", "$Width", "$Height") | Out-Null
    Invoke-PlaywrightCli @(
        "eval",
        "(()=>{const i=document.querySelector('#occupation-query');i.value='Data Analyst';document.querySelector('#occupation-search-button').click();return true})()"
    ) | Out-Null
    Invoke-PlaywrightCli @("eval", "new Promise(r=>setTimeout(r,300))") | Out-Null
    $emptyAlias = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({message:(document.querySelector('.occupation-context-empty')||{}).textContent||'',status:(document.querySelector('#occupation-status')||{}).textContent||''})"
    ))
    if ($emptyAlias.message -notlike "*This occupation family was recognized*") {
        throw "Career Fit did not expose the alias-empty release message."
    }
    if ($emptyAlias.status -notlike "*Occupation family recognized*") {
        throw "Career Fit did not expose the alias-empty status."
    }

    Invoke-PlaywrightCli @(
        "eval",
        "(()=>{const i=document.querySelector('#occupation-query');i.value='ML Engineer';document.querySelector('#occupation-search-button').click();return true})()"
    ) | Out-Null
    Invoke-PlaywrightCli @("eval", "new Promise(r=>setTimeout(r,300))") | Out-Null
    $careerMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,candidateCards:document.querySelectorAll('.occupation-candidate').length,mappingNotes:document.querySelectorAll('.occupation-candidate-note').length,confirmationControls:Array.from(document.querySelectorAll('.occupation-candidate button')).some(button=>button.textContent.includes('Use this occupation'))})"
    ))
    Assert-NoHorizontalOverflow "Career Fit" $careerMeasurement
    if ($careerMeasurement.candidateCards -lt 1 -or $careerMeasurement.mappingNotes -lt 1 -or -not $careerMeasurement.confirmationControls) {
        throw "Career Fit alias candidate cards, mapping notes, or confirmation controls were not visible."
    }

    Write-Output "Mobile layout check passed at ${Width}px for AI Labor Atlas and Career Fit."
}
finally {
    try {
        Invoke-PlaywrightCli @("close") | Out-Null
    }
    catch {
    }
    Pop-Location
    if (Test-Path -LiteralPath $tempDir) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force
    }
}
