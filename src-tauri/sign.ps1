param (
  [string]$Target
)

# Check if AzureSignTool is available and credentials are configured
$hasAzureSign = Get-Command AzureSignTool.exe -ErrorAction SilentlyContinue
$hasCredentials = $env:AZURE_KEY_VAULT_URI -and $env:AZURE_CLIENT_ID -and $env:AZURE_TENANT_ID -and $env:AZURE_CLIENT_SECRET -and $env:AZURE_CERT_NAME

if ($hasAzureSign -and $hasCredentials) {
  Write-Host "Signing $Target with AzureSignTool..."
  AzureSignTool.exe sign `
    -tr http://timestamp.digicert.com `
    -kvu $env:AZURE_KEY_VAULT_URI `
    -kvi $env:AZURE_CLIENT_ID `
    -kvt $env:AZURE_TENANT_ID `
    -kvs $env:AZURE_CLIENT_SECRET `
    -kvc $env:AZURE_CERT_NAME `
    -v $Target
} else {
  Write-Host "Skipping code signing: AzureSignTool or credentials not available (local build)"
}
