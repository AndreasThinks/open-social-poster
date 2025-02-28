# Check if UV is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "UV not found. Installing UV..."
    # Install UV
    irm https://astral.sh/uv/install.ps1 | iex
    # Verify installation
    if ($?) {
        Write-Host "UV installed successfully"
    } else {
        Write-Host "UV installation failed"
        exit 1
    }
} else {
    Write-Host "UV already installed"
}

# Run the Python script using UV
Write-Host "Running social_poster.py..."
uv run social_poster.py