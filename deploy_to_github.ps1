# PowerShell script to help deploy the project to GitHub
Write-Host "🚀 Starting GitHub Deployment Script..." -ForegroundColor Cyan

# Check if Git is installed
try {
    $gitVersion = git --version
    Write-Host "✅ Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git is not installed. Please install Git first: https://git-scm.com/downloads" -ForegroundColor Red
    exit 1
}

# Initialize Git repository if not already done
if (-not (Test-Path ".git")) {
    Write-Host "🔨 Initializing Git repository..." -ForegroundColor Cyan
    git init
} else {
    Write-Host "✅ Git repository already initialized" -ForegroundColor Green
}

# Add all files to staging
Write-Host "📦 Adding files to Git staging..." -ForegroundColor Cyan
git add .

# Check if there are any changes to commit
$status = git status --porcelain
if (-not $status) {
    Write-Host "ℹ️ No changes to commit" -ForegroundColor Yellow
} else {
    # Commit changes
    $commitMessage = Read-Host "💬 Enter your commit message (or press Enter to use default)"
    if ([string]::IsNullOrWhiteSpace($commitMessage)) {
        $commitMessage = "Initial commit: Air Quality Dashboard"
    }
    
    Write-Host "💾 Committing changes with message: $commitMessage" -ForegroundColor Cyan
    git commit -m $commitMessage
}

# Ask for GitHub repository URL
$repoUrl = Read-Host "🔗 Enter your GitHub repository URL (e.g., https://github.com/username/air-quality-dashboard.git)"

# Add remote origin if not already added
$remoteUrl = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🔗 Adding remote origin: $repoUrl" -ForegroundColor Cyan
    git remote add origin $repoUrl
} else {
    Write-Host "✅ Remote origin already set to: $remoteUrl" -ForegroundColor Green
    
    # Ask if user wants to change the remote URL
    $changeRemote = Read-Host "🔄 Do you want to change the remote URL? (y/n)"
    if ($changeRemote -eq 'y') {
        git remote set-url origin $repoUrl
        Write-Host "✅ Updated remote origin to: $repoUrl" -ForegroundColor Green
    }
}

# Push to GitHub
Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Cyan
$branch = git branch --show-current
if (-not $branch) {
    $branch = "main"
    git branch -M $branch
}

git push -u origin $branch

# Check if push was successful
if ($LASTEXITCODE -eq 0) {
    Write-Host "🎉 Successfully deployed to GitHub!" -ForegroundColor Green
    Write-Host "🌍 Your repository is now available at: $($repoUrl -replace '\.git$', '')" -ForegroundColor Cyan
    
    # Provide next steps
    Write-Host "\nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Go to https://share.streamlit.io/" -ForegroundColor Cyan
    Write-Host "2. Click 'New app' and select your repository" -ForegroundColor Cyan
    Write-Host "3. Set the branch to '$branch' and the main file to 'app.py'" -ForegroundColor Cyan
    Write-Host "4. Add your OPENWEATHER_API_KEY in the 'Advanced settings'" -ForegroundColor Cyan
    Write-Host "5. Click 'Deploy!'" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to push to GitHub. Please check the error above." -ForegroundColor Red
}
