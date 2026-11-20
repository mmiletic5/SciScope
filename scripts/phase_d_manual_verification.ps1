[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repoRoot

$runId = [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'")
$runDirectory = Join-Path $repoRoot "evals/protected/phase_d_final_review/manual_verification/$runId"
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$logPath = Join-Path $runDirectory 'verification.log'
$summaryPath = Join-Path $runDirectory 'summary.json'
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
$script:steps = [System.Collections.Generic.List[object]]::new()
$originalTestUrl = $env:SCISCOPE_TEST_DATABASE_URL
$testUrlWasSet = Test-Path Env:SCISCOPE_TEST_DATABASE_URL
$originalPythonPath = $env:PYTHONPATH
$pythonPathWasSet = Test-Path Env:PYTHONPATH
$dbReady = $false
$pythonReady = $false

function Add-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Status,
        [int]$ExitCode = 0,
        [string]$Summary = '',
        [string]$Command = ''
    )
    $record = [ordered]@{
        name = $Name
        status = $Status
        exit_code = $ExitCode
        summary = $Summary
        command = $Command
    }
    $script:steps.Add($record)
    $line = '{0} [{1}] {2} (exit={3}) command="{4}" {5}' -f `
        [DateTime]::UtcNow.ToString('o'), $Status, $Name, $ExitCode, $Command, $Summary
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    Write-Host ('[{0}] {1} - {2}' -f $Status, $Name, $Summary)
}

function Invoke-Captured {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$SuccessSummary = 'command completed'
    )
    try {
        $priorErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $captured = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
        }
        finally {
            $ErrorActionPreference = $priorErrorActionPreference
        }
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) { $exitCode = 1 }
        $safeSummary = $SuccessSummary
        if ($exitCode -ne 0) {
            $safeSummary = 'command failed; detailed output withheld'
        }
        elseif ($Name -match 'pytest') {
            $summaryLine = $captured |
                Where-Object { $_ -match '\d+ passed|\d+ failed|\d+ skipped|\d+ deselected' } |
                Select-Object -Last 1
            if ($summaryLine) { $safeSummary = $summaryLine.Trim() }
        }
        $relativeExecutable = $FilePath
        if ($FilePath.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
            $relativeExecutable = $FilePath.Substring($repoRoot.Length).TrimStart([char[]]@('\', '/'))
            $relativeExecutable = $relativeExecutable.Replace('\', '/')
        }
        Add-Step -Name $Name -Status $(if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }) `
            -ExitCode $exitCode -Summary $safeSummary `
            -Command (($relativeExecutable + ' ' + ($Arguments -join ' ')).Trim())
        return [PSCustomObject]@{
            ExitCode = [int]$exitCode
            Output = ($captured -join [Environment]::NewLine)
        }
    }
    catch {
        Add-Step -Name $Name -Status 'FAIL' -ExitCode 1 `
            -Summary 'command could not be started; details withheld'
        return [PSCustomObject]@{ ExitCode = 1; Output = '' }
    }
}

function Get-JsonOutput {
    param([Parameter(Mandatory = $true)][string]$Text)
    try { return ($Text | ConvertFrom-Json -ErrorAction Stop) }
    catch { return $null }
}

function Invoke-DbPreflight {
    param([Parameter(Mandatory = $true)][string]$Name)
    $result = Invoke-Captured -Name $Name -FilePath $python `
        -Arguments @('scripts/phase_d_readonly_db_preflight.py') `
        -SuccessSummary 'read-only identity, corpus counts, embedding set, and payload checks'
    if ($result.ExitCode -ne 0) { return $false }
    $report = Get-JsonOutput -Text $result.Output
    if (
        $null -eq $report -or $report.status -ne 'PASS' -or
        $report.database -ne 'sciscope_test_005' -or
        $report.embedding_set_id -ne 115 -or
        $report.corpus_version -ne 'pilot17-xml-1fff1573b610' -or
        $report.transaction_read_only -ne $true -or
        $report.counts.papers -ne 17 -or $report.counts.sections -ne 319 -or
        $report.counts.chunks -ne 728 -or $report.counts.embeddings -ne 728
    ) {
        Add-Step -Name "$Name identity assertions" -Status 'FAIL' -ExitCode 1 `
            -Summary 'preflight did not match the frozen corpus/embedding identity'
        return $false
    }
    Add-Step -Name "$Name identity assertions" -Status 'PASS' `
        -Summary 'sciscope_test_005; PostgreSQL 17; embedding set 115; frozen pilot counts'
    return $true
}

try {
    $env:PYTHONPATH = "$repoRoot;$repoRoot/src"
    Add-Content -LiteralPath $logPath -Value "SciScope Phase D manual verification $runId UTC" -Encoding UTF8
    $windows = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
    if ($windows) {
        Add-Step -Name 'Windows platform' -Status 'PASS' -Summary 'native Windows PowerShell'
    }
    else {
        Add-Step -Name 'Windows platform' -Status 'FAIL' -ExitCode 1 -Summary 'native Windows is required'
    }

    if ($windows -and (Test-Path -LiteralPath $python -PathType Leaf)) {
        $pythonVersion = & $python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $pythonVersion -match '^3\.12\.') {
            $pythonReady = $true
            Add-Step -Name 'Python 3.12 environment' -Status 'PASS' `
                -Summary ".venv Python $pythonVersion"
        }
        else {
            Add-Step -Name 'Python 3.12 environment' -Status 'FAIL' -ExitCode 1 `
                -Summary 'existing .venv must use Python 3.12'
        }
    }
    else {
        Add-Step -Name 'Python 3.12 environment' -Status 'FAIL' -ExitCode 1 `
            -Summary 'native Windows and the existing .venv Python executable are required'
    }

    $service = if ($windows) {
        Get-Service -Name 'postgresql-x64-17' -ErrorAction SilentlyContinue
    }
    else { $null }
    if ($null -ne $service -and $service.Status -eq 'Running') {
        Add-Step -Name 'PostgreSQL 17 Windows service' -Status 'PASS' -Summary 'service is running'
    }
    else {
        Add-Step -Name 'PostgreSQL 17 Windows service' -Status 'FAIL' -ExitCode 1 `
            -Summary 'postgresql-x64-17 is missing or not running'
    }

    if ($pythonReady) {
        $deriveCode = "from scripts.phase_d_readonly_db_preflight import _load_source_url, derive_test_database_url; print(derive_test_database_url(_load_source_url()), end='')"
        $deriveOutput = @(& $python -c $deriveCode 2>&1)
        $deriveExitCode = $LASTEXITCODE
        $derivedUrl = ($deriveOutput | Out-String).Trim()
        if ($deriveExitCode -eq 0 -and $derivedUrl) {
            $env:SCISCOPE_TEST_DATABASE_URL = $derivedUrl
            Add-Step -Name 'In-memory test database target derivation' -Status 'PASS' `
                -Summary 'local source guarded and target fixed to sciscope_test_005; URL withheld' `
                -Command 'python -c derive_test_database_url(_load_source_url())'
            $dbReady = Invoke-DbPreflight -Name 'Read-only database preflight'
        }
        else {
            Add-Step -Name 'Read-only database preflight' -Status 'FAIL' -ExitCode 1 `
                -Summary 'approved local database URL source is unavailable or invalid; details withheld'
        }

        $offlineArgs = @(
            '-m', 'pytest', 'tests/evaluation', 'tests/retrieval',
            '-q', '-p', 'no:cacheprovider',
            '--ignore=tests/retrieval/test_postgres_core.py',
            '--ignore=tests/retrieval/test_postgres_lookup.py',
            '--deselect=tests/retrieval/test_phase_c_pipeline.py::test_lookup_ranking_and_context_keep_exact_snapshot_evidence'
        )
        $offline = Invoke-Captured -Name 'Offline evaluation/retrieval pytest' `
            -FilePath $python -Arguments $offlineArgs `
            -SuccessSummary 'offline evaluation/retrieval tests'

        $focus = Invoke-Captured -Name 'Focused lexical/RRF regression pytest' `
            -FilePath $python -Arguments @(
                '-m', 'pytest', 'tests/retrieval/test_ranking.py',
                'tests/retrieval/test_core_offline.py',
                '-q', '-p', 'no:cacheprovider'
            ) -SuccessSummary 'RRF and offline retrieval focused checks'

        $ruff = Invoke-Captured -Name 'Ruff check' -FilePath $python `
            -Arguments @('-m', 'ruff', 'check', 'src', 'tests', 'scripts') `
            -SuccessSummary 'Ruff check passed'
        $format = Invoke-Captured -Name 'Ruff format check' -FilePath $python `
            -Arguments @('-m', 'ruff', 'format', '--check', 'src', 'tests', 'scripts') `
            -SuccessSummary 'Ruff format check passed'
        $mypy = Invoke-Captured -Name 'Mypy' -FilePath $python `
            -Arguments @('-m', 'mypy', 'src/sciscope') `
            -SuccessSummary 'Mypy passed for src/sciscope'
        $diffCheck = Invoke-Captured -Name 'Git whitespace check' `
            -FilePath 'git' -Arguments @('diff', '--check') `
            -SuccessSummary 'git diff --check passed'

        $audit = Invoke-Captured -Name 'Saved evidence/hash/metric audit' `
            -FilePath $python -Arguments @(
                'scripts/phase_d_manual_verification_audit.py', '--saved-evidence'
            ) -SuccessSummary 'saved T006 metrics, manifests, and delivery hashes verified'
        if ($audit.ExitCode -eq 0) {
            $auditObject = Get-JsonOutput -Text $audit.Output
            if ($null -ne $auditObject) {
                $safeAudit = $auditObject.saved_evidence
                Add-Step -Name 'Saved evidence audit assertions' -Status 'PASS' `
                    -Summary ("{0} T006 artifacts; {1} reports; {2} delivery payloads; {3} cache manifests" -f `
                        $safeAudit.t006_artifacts_verified, $safeAudit.t006_reports_verified,
                        $safeAudit.delivery_payloads_verified,
                        $safeAudit.query_cache_manifests_verified)
            }
        }

        $rrf = Invoke-Captured -Name 'Synthetic RRF expected/observed diagnostic' `
            -FilePath $python -Arguments @(
                'scripts/phase_d_manual_verification_audit.py', '--rrf-diagnostic'
            ) -SuccessSummary 'synthetic branches fused against independent arithmetic oracle'
        if ($rrf.ExitCode -eq 0) {
            $rrfObject = Get-JsonOutput -Text $rrf.Output
            if ($null -ne $rrfObject) {
                $rrfResult = $rrfObject.rrf_diagnostic
                Add-Step -Name 'Synthetic RRF order comparison' `
                    -Status $(if ($rrfResult.status -eq 'PASS') { 'PASS' } else { 'FAIL' }) `
                    -ExitCode $(if ($rrfResult.status -eq 'PASS') { 0 } else { 1 }) `
                    -Summary ("expected={0}; observed={1}; unique candidates={2}/{3}" -f `
                        ($rrfResult.expected_order -join ','),
                        ($rrfResult.observed_order -join ','),
                        $rrfResult.observed_unique_union_count,
                        $rrfResult.expected_unique_union_count)
            }
        }

        if ($dbReady) {
            $pg = Invoke-Captured -Name 'Read-only PostgreSQL retrieval integration pytest' `
                -FilePath $python -Arguments @(
                    '-m', 'pytest', 'tests/retrieval/test_postgres_core.py',
                    'tests/retrieval/test_postgres_lookup.py',
                    'tests/retrieval/test_phase_c_pipeline.py',
                    '-q', '-p', 'no:cacheprovider'
                ) -SuccessSummary 'read-only PostgreSQL retrieval integration tests'

            $lexical = Invoke-Captured -Name 'Read-only lexical source-grounded probes' `
                -FilePath $python -Arguments @(
                    'scripts/phase_d_manual_verification_audit.py', '--lexical-probes'
                ) -SuccessSummary '8 controlled lexical probes; no Golden questions used'
            if ($lexical.ExitCode -eq 0) {
                $lexicalObject = Get-JsonOutput -Text $lexical.Output
                if ($null -ne $lexicalObject) {
                    foreach ($probe in $lexicalObject.lexical_probes.probes) {
                        $targetMapping = if ($null -eq $probe.target_doi_locator_verified) {
                            'n/a'
                        }
                        else { [string]$probe.target_doi_locator_verified }
                        $queryTreeNote = ''
                        if ($probe.label -eq 'long_cross_source') {
                            $queryTreeNote = "; querytree=$($probe.querytree)"
                        }
                        Add-Step -Name "Lexical probe $($probe.label)" `
                            -Status $(if ($probe.pass) { 'PASS' } else { 'FAIL' }) `
                            -ExitCode $(if ($probe.pass) { 0 } else { 1 }) `
                            -Summary ("candidates expected={0} observed={1}; target rank expected={2} observed={3}; DOI/locator={4}{5}" -f `
                                $probe.expected_candidates, $probe.observed_candidates,
                                $probe.expected_target_rank, $probe.observed_target_rank,
                                $targetMapping, $queryTreeNote)
                    }
                }
            }

            $postflight = Invoke-DbPreflight -Name 'Read-only database postflight'
        }
        else {
            Add-Step -Name 'Read-only PostgreSQL retrieval integration pytest' -Status 'SKIP' `
                -ExitCode 1 -Summary 'database preflight failed; no integration test was started'
            Add-Step -Name 'Read-only lexical source-grounded probes' -Status 'SKIP' `
                -ExitCode 1 -Summary 'database preflight failed; no diagnostic query was started'
            Add-Step -Name 'Read-only database postflight' -Status 'SKIP' `
                -ExitCode 1 -Summary 'database preflight did not pass'
        }
    }
    else {
        foreach ($name in @(
            'Offline evaluation/retrieval pytest', 'Focused lexical/RRF regression pytest',
            'Ruff check', 'Ruff format check', 'Mypy', 'Git whitespace check',
            'Saved evidence/hash/metric audit', 'Synthetic RRF expected/observed diagnostic',
            'Synthetic RRF order comparison', 'Read-only PostgreSQL retrieval integration pytest',
            'Read-only lexical source-grounded probes', 'Read-only database postflight'
        )) {
            Add-Step -Name $name -Status 'SKIP' -ExitCode 1 `
                -Summary 'required .venv Python 3.12 prerequisite is unavailable'
        }
    }
}
catch {
    Add-Step -Name 'Manual verification script execution' -Status 'FAIL' `
        -ExitCode 1 -Summary 'unexpected error; detailed output withheld'
}
finally {
    if ($testUrlWasSet) { $env:SCISCOPE_TEST_DATABASE_URL = $originalTestUrl }
    else { Remove-Item Env:SCISCOPE_TEST_DATABASE_URL -ErrorAction SilentlyContinue }
    if ($pythonPathWasSet) { $env:PYTHONPATH = $originalPythonPath }
    else { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
    $failed = @($script:steps | Where-Object { $_.status -eq 'FAIL' }).Count
    $skipped = @($script:steps | Where-Object { $_.status -eq 'SKIP' }).Count
    $overall = if ($failed -eq 0 -and $skipped -eq 0) { 'PASS' } else { 'FAIL' }
    $summary = [ordered]@{
        run_id_utc = $runId
        overall_status = $overall
        failed_step_count = $failed
        skipped_step_count = $skipped
        environment = [ordered]@{
            powershell_version = $PSVersionTable.PSVersion.ToString()
            windows_version = [Environment]::OSVersion.Version.ToString()
            python_executable = '.venv/Scripts/python.exe'
            python_version = $pythonVersion
            native_windows = ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
            postgres_service = 'postgresql-x64-17'
        }
        database_mutations = $false
        migrations_run = $false
        paid_api_calls = $false
        protected_question_text_emitted = $false
        protected_retrieval_rerun = $false
        steps = @($script:steps)
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
    Write-Host "Log: evals/protected/phase_d_final_review/manual_verification/$runId/verification.log"
    Write-Host "Summary: evals/protected/phase_d_final_review/manual_verification/$runId/summary.json"
    if ($overall -ne 'PASS') { exit 1 }
}
