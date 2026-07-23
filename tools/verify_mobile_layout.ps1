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

function Wait-ForCondition {
    param(
        [string]$Expression,
        [int]$TimeoutMs = 6000
    )

    $waitScript = "new Promise(resolve=>{const deadline=Date.now()+$TimeoutMs;const check=()=>{let ready=false;try{ready=Boolean($Expression)}catch{};if(ready||Date.now()>=deadline){resolve(ready);return;}setTimeout(check,50)};check()})"
    $value = Read-PlaywrightJson (Invoke-PlaywrightCli @("eval", $waitScript))
    if (-not [bool]$value) {
        throw "Timed out waiting for Playwright condition: $Expression"
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
    $atlasAccessibility = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({count:document.querySelectorAll('.bubble').length,role:document.querySelector('.bubble').getAttribute('role'),tabindex:document.querySelector('.bubble').getAttribute('tabindex'),demo:document.querySelector('.dataset-notice').textContent})"
    ))
    $atlasKeyboard = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "(()=>{var list=document.querySelectorAll('.bubble');var target=list.length>1?list[1]:list[0];target.focus();target.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return JSON.stringify({detail:document.querySelector('#detail-title').textContent,title:(target.getAttribute('aria-label')||'').slice(7)})})()"
    ))
    if ($atlasAccessibility.count -lt 1 -or $atlasAccessibility.role -ne "button" -or $atlasAccessibility.tabindex -ne "0" -or $atlasKeyboard.detail -ne $atlasKeyboard.title -or $atlasAccessibility.demo -notlike "*DEMO DATASET*") {
        throw "AI Labor Atlas keyboard semantics or demo-data disclosure failed."
    }
    Invoke-PlaywrightCli @("close") | Out-Null

    Invoke-PlaywrightCli @("open", $CareerFitUrl) | Out-Null
    Invoke-PlaywrightCli @("resize", "$Width", "$Height") | Out-Null
    Wait-ForCondition "document.querySelector('#review-panel') && !document.querySelector('#review-panel').hidden"
    $reviewMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({reviewVisible:!document.querySelector('#review-panel').hidden,coverageVisible:!document.querySelector('#coverage-panel').hidden,inputCoverage:document.querySelector('#input-coverage-score').textContent,fitBefore:document.querySelector('#fit-score').textContent})"
    ))
    if (-not $reviewMeasurement.reviewVisible -or -not $reviewMeasurement.coverageVisible -or [string]::IsNullOrWhiteSpace($reviewMeasurement.inputCoverage) -or $reviewMeasurement.fitBefore -ne "Review first") {
        throw "Career Fit did not expose the provisional review and coverage panels."
    }
    Invoke-PlaywrightCli @(
        "eval",
        "(()=>{document.querySelector('#job-input').value='Office coordinator. Must have communication and Excel. Preferred: customer service. Schedule meetings and maintain records.';document.querySelector('#candidate-input').value='I am looking for work and do not have a current resume.';document.querySelector('#analyze-button').click();return true})()"
    ) | Out-Null
    Wait-ForCondition "(document.querySelector('#status')?.textContent || '').includes('More input needed')"
    $guidedMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,visible:!document.querySelector('#guided-intake').hidden,requirements:document.querySelectorAll('#guided-intake-requirement option').length,task:!!document.querySelector('#guided-intake-task'),context:!!document.querySelector('#guided-intake-context')})"
    ))
    Assert-NoHorizontalOverflow "Career Fit guided intake" $guidedMeasurement
    if (-not $guidedMeasurement.visible -or $guidedMeasurement.requirements -lt 1 -or -not $guidedMeasurement.task -or -not $guidedMeasurement.context) {
        throw "Career Fit did not expose the resume-free guided intake controls."
    }
    Invoke-PlaywrightCli @(
        "eval",
        "(()=>{document.querySelector('#guided-intake-task').value='Scheduled appointments and maintained a shared calendar';document.querySelector('#guided-intake-context').value='At a community group';document.querySelector('#guided-intake-result').value='Reduced missed follow-ups';document.querySelector('#guided-intake-button').click();return true})()"
    ) | Out-Null
    Wait-ForCondition "(document.querySelector('#guided-intake-status')?.textContent || '').includes('recorded')"
    Invoke-PlaywrightCli @("eval", "(()=>{document.querySelector('#apply-review-button').click();return true})()") | Out-Null
    Wait-ForCondition "(document.querySelector('#status')?.textContent || '').includes('Reviewed analysis')"
    $reviewedMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({status:document.querySelector('#status').textContent,reviewStatus:document.querySelector('#review-status').textContent,fitAfter:document.querySelector('#fit-score').textContent})"
    ))
    if ($reviewedMeasurement.status -notlike "*Reviewed analysis*" -or $reviewedMeasurement.reviewStatus -notlike "*applied*" -or $reviewedMeasurement.fitAfter -eq "Review first") {
        throw "Career Fit did not recalculate from the review state."
    }
    Invoke-PlaywrightCli @(
        "eval",
        "(()=>{const i=document.querySelector('#occupation-query');i.value='Data Analyst';document.querySelector('#occupation-search-button').click();return true})()"
    ) | Out-Null
    Wait-ForCondition "document.querySelector('.occupation-context-empty') && document.querySelector('.occupation-context-empty').textContent.includes('recognized')"
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
    Wait-ForCondition "document.querySelectorAll('.occupation-candidate').length > 0"
    $careerMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,candidateCards:document.querySelectorAll('.occupation-candidate').length,mappingNotes:document.querySelectorAll('.occupation-candidate-note').length,confirmationControls:Array.from(document.querySelectorAll('.occupation-candidate button')).some(button=>button.textContent.includes('Use this occupation'))})"
    ))
    Assert-NoHorizontalOverflow "Career Fit" $careerMeasurement
    if ($careerMeasurement.candidateCards -lt 1 -or $careerMeasurement.mappingNotes -lt 1 -or -not $careerMeasurement.confirmationControls) {
        throw "Career Fit alias candidate cards, mapping notes, or confirmation controls were not visible."
    }
    Invoke-PlaywrightCli @("eval", "(()=>{document.querySelector('.occupation-candidate button').click();return true})()") | Out-Null
    Wait-ForCondition "document.querySelector('#market-context') && !document.querySelector('#market-context').hidden"
    $marketMeasurement = Read-PlaywrightJson (Invoke-PlaywrightCli @(
        "eval",
        "JSON.stringify({visible:!document.querySelector('#market-context').hidden,metricCount:document.querySelectorAll('#market-metrics .market-metric').length,provenance:(document.querySelector('#market-provenance')||{}).textContent||''})"
    ))
    if (-not $marketMeasurement.visible -or $marketMeasurement.metricCount -lt 3 -or [string]::IsNullOrWhiteSpace($marketMeasurement.provenance)) {
        throw "Career Fit did not expose the separate Atlas market context."
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
