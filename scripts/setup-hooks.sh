#!/bin/bash

# Git Hooks Setup Script
# This script sets up git hooks for code quality

set -e

echo "🔧 Setting up git hooks..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository. Cannot set up hooks."
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Create pre-commit hook that runs our quality checks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# Pre-commit hook for code quality
echo "🚀 Running pre-commit code quality checks..."

# Run the pre-commit script
if [ -f "./scripts/pre-commit.sh" ]; then
    ./scripts/pre-commit.sh
else
    echo "⚠️  Pre-commit script not found at ./scripts/pre-commit.sh"
    echo "Skipping code quality checks..."
fi
EOF

# Make the pre-commit hook executable
chmod +x .git/hooks/pre-commit

echo "✅ Git hooks setup complete!"
echo "🎯 Pre-commit hook installed"
echo ""
echo "Now git will automatically run code quality checks before each commit."
echo "To bypass these checks temporarily, use: git commit --no-verify"