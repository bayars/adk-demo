#!/bin/bash
# GitHub Setup Script for ADK Demo Project

echo "🚀 ADK Demo GitHub Setup Script"
echo "================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please run this script from the project root."
    exit 1
fi

# Get GitHub username
echo "Enter your GitHub username:"
read GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ GitHub username is required."
    exit 1
fi

# Add remote origin
echo "📡 Adding GitHub remote origin..."
git remote add origin https://github.com/$GITHUB_USERNAME/adk_demo.git

# Check if remote was added successfully
if git remote -v | grep -q "origin"; then
    echo "✅ Remote origin added successfully"
else
    echo "❌ Failed to add remote origin"
    exit 1
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "🎉 Successfully pushed to GitHub!"
    echo "📋 Repository URL: https://github.com/$GITHUB_USERNAME/adk_demo"
    echo ""
    echo "Next steps:"
    echo "1. Visit https://github.com/$GITHUB_USERNAME/adk_demo"
    echo "2. Verify all files are uploaded correctly"
    echo "3. Share the repository with others"
    echo ""
    echo "To clone the repository:"
    echo "git clone https://github.com/$GITHUB_USERNAME/adk_demo.git"
else
    echo "❌ Failed to push to GitHub"
    echo "Please check:"
    echo "1. GitHub repository exists"
    echo "2. You have push permissions"
    echo "3. GitHub credentials are configured"
    exit 1
fi
