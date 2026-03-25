#!/usr/bin/env bash
set -euo pipefail

echo "⚙️ Starting Dev Environment Maintenance..."
echo "========================================"

echo "📦 Updating package managers..."

# npm
if command -v npm &>/dev/null; then
	echo "🟢 Updating npm and global packages..."
	npm update -g 2>/dev/null || true
	npm_outdated=$(npm outdated -g --depth=0 2>/dev/null | wc -l | xargs)
	echo "   npm: Updated global packages ($npm_outdated were outdated)"
else
	echo "   npm: Not installed"
fi

# yarn
if command -v yarn &>/dev/null; then
	echo "🧶 Updating yarn..."
	yarn global upgrade 2>/dev/null || true
	echo "   yarn: Global packages updated"
else
	echo "   yarn: Not installed"
fi

# pip
if command -v pip3 &>/dev/null; then
	echo "🐍 Updating pip packages..."
	pip3 list --outdated --format=freeze 2>/dev/null | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip3 install -U 2>/dev/null || true
	pip_outdated=$(pip3 list --outdated 2>/dev/null | wc -l | xargs)
	echo "   pip: Updated packages ($pip_outdated were outdated)"
else
	echo "   pip3: Not installed"
fi

# gems
if command -v gem &>/dev/null; then
	echo "💎 Updating Ruby gems..."
	gem update --system 2>/dev/null || true
	gem update 2>/dev/null || true
	echo "   gems: Updated"
else
	echo "   gem: Not installed"
fi

# rust
if command -v rustup &>/dev/null; then
	echo "🦀 Updating Rust..."
	rustup update 2>/dev/null || true
	echo "   Rust: Updated"
else
	echo "   rustup: Not installed"
fi

echo ""
echo "🔧 Cleaning development caches..."

# Go module cache
if command -v go &>/dev/null; then
	go clean -modcache 2>/dev/null || true
	echo "   Go module cache cleaned"
fi

# Xcode derived data
if [ -d "$HOME/Library/Developer/Xcode/DerivedData" ]; then
	rm -rf "$HOME/Library/Developer/Xcode/DerivedData"/* 2>/dev/null || true
	echo "   Xcode derived data cleaned"
fi

# VS Code extension logs
if [ -d "$HOME/.vscode/extensions" ]; then
	find "$HOME/.vscode/extensions" -name "*.log" -delete 2>/dev/null || true
	echo "   VS Code extension logs cleaned"
fi

echo ""
echo "🔍 Development environment health check..."
tools=("git" "node" "python3" "code" "docker")
for tool in "${tools[@]}"; do
	if command -v "$tool" &>/dev/null; then
		version=$(command "$tool" --version 2>/dev/null | head -1)
		echo "   ✅ $tool: $version"
	else
		echo "   ❌ $tool: Not installed"
	fi
done

echo ""
echo "========================================"
echo "✅ Dev environment maintenance complete!"
echo "🕐 Completed at: $(date)"
