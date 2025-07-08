# Deployment Guide

This guide will walk you through deploying the Air Quality Dashboard to GitHub and Streamlit Cloud.

## Prerequisites

- A GitHub account
- A Streamlit Cloud account (free tier available)
- Git installed on your local machine
- Python 3.8+ installed

## Step 1: Initialize Git Repository

1. Open a terminal in your project directory
2. Initialize a new Git repository:
   ```bash
   git init
   ```
3. Add all files to Git:
   ```bash
   git add .
   ```
4. Make your first commit:
   ```bash
   git commit -m "Initial commit"
   ```

## Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Name your repository (e.g., "air-quality-dashboard")
3. Choose "Public" or "Private"
4. Click "Create repository"
5. Follow the instructions to push your existing repository:
   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY-NAME.git
   git branch -M main
   git push -u origin main
   ```

## Step 3: Deploy to Streamlit Cloud

1. Go to [Streamlit Cloud](https://share.streamlit.io/)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository and branch (usually `main`)
5. Set the main file path to `app.py`
6. Click "Advanced settings" and add your environment variable:
   - `OPENWEATHER_API_KEY`: Your OpenWeatherMap API key
7. Click "Deploy!"

## Step 4: Update Your Repository (When Making Changes)

1. Make your changes to the code
2. Stage your changes:
   ```bash
   git add .
   ```
3. Commit your changes:
   ```bash
   git commit -m "Your commit message"
   ```
4. Push to GitHub:
   ```bash
   git push origin main
   ```
5. Streamlit Cloud will automatically redeploy your app

## Troubleshooting

- If the app fails to deploy, check the logs in Streamlit Cloud
- Make sure all dependencies are listed in `requirements.txt`
- Ensure your API key is correctly set in the environment variables
- Check that your `app.py` file is in the root directory

## Custom Domain (Optional)

To use a custom domain with Streamlit Cloud:

1. Go to your app's settings in Streamlit Cloud
2. Click on "Advanced settings"
3. Under "Custom domain", enter your domain
4. Follow the instructions to verify domain ownership
5. Update your DNS settings as instructed

## Need Help?

If you encounter any issues, feel free to open an issue on the GitHub repository or check Streamlit's [documentation](https://docs.streamlit.io/).
