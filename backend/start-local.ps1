$ErrorActionPreference = "Stop"
$originalApiKey = $env:OPENAI_API_KEY
$secureApiKey = $null

try {
    if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
        $secureApiKey = Read-Host "Enter your OpenAI API key (input is hidden)" -AsSecureString
        $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $secureApiKey).Password
    }

    Set-Location $PSScriptRoot
    python -m uvicorn price_check_api.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
}
finally {
    if ($null -ne $secureApiKey) {
        $env:OPENAI_API_KEY = $originalApiKey
        $secureApiKey.Dispose()
    }
}
