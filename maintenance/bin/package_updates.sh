#!/usr/bin/env bash
set -euo pipefail

echo "📦 Starting Package Manager Updates..."
echo "======================================"

command_exists() { command -v "$1" >/dev/null 2>&1; }

safe_run() {
	local cmd="$1"
	local description="$2"
	local forbidden_chars='[;&|`$]'
	if [[ $cmd =~ $forbidden_chars ]]; then
		echo "   ❌ Invalid command detected, skipping"
		return 1
	fi
	echo "🔄 $description..."
	if bash -c "$cmd" >/dev/null 2>&1; then
		echo "   ✅ Success"
	else
		echo "   ⚠️  Failed or not needed"
	fi
}

# Homebrew
if command_exists brew; then
	echo "🍺 Updating Homebrew..."
	safe_run "brew update" "Updating Homebrew database"
	safe_run "brew upgrade" "Upgrading Homebrew packages"
	safe_run "brew cleanup --prune=7" "Cleaning Homebrew cache"
else
	echo "   ⚠️  Homebrew not found"
fi

echo ""

# npm
if command_exists npm; then
	echo "📗 Updating npm packages..."
	safe_run "npm update -g" "Updating global npm packages"
	safe_run "npm cache clean --force" "Cleaning npm cache"
else
	echo "   ⚠️  npm not found"
fi

echo ""

# pip
if command_exists pip3; then
	echo "🐍 Updating Python packages..."
	outdated_packages=$(pip3 list --outdated --format=json 2>/dev/null | python3 -c "import sys,json;
try:
    data=json.load(sys.stdin)
    [print(pkg['name']) for pkg in data]
except Exception:
    pass" 2>/dev/null)
	if [ -n "$outdated_packages" ]; then
		echo "$outdated_packages" | while read package; do
			[[ -n $package ]] && safe_run "pip3 install --upgrade '$package'" "Updating $package"
		done
	else
		echo "   ✅ All pip packages up to date"
	fi
	safe_run "pip3 cache purge" "Cleaning pip cache"
else
	echo "   ⚠️  pip3 not found"
fi

echo ""

# Ruby/gem
if command_exists gem; then
	echo "💎 Updating Ruby gems..."
	safe_run "gem update --system" "Updating RubyGems system"
	safe_run "gem update" "Updating installed gems"
	safe_run "gem cleanup" "Cleaning old gem versions"
else
	echo "   ⚠️  gem not found"
fi

echo ""

# Rust/cargo
if command_exists cargo; then
	echo "🦀 Updating Rust packages..."
	safe_run "rustup update" "Updating Rust toolchain"
	if command_exists cargo-install-update; then
		safe_run "cargo install-update -a" "Updating cargo packages"
	else
		echo "   💡 Install cargo-update for package updates: cargo install cargo-update"
	fi
else
	echo "   ⚠️  cargo not found"
fi

echo ""

# Go (informational)
if command_exists go; then
	echo "🐹 Checking Go installation..."
	go_version=$(go version 2>/dev/null | awk '{print $3}')
	echo "   📊 Go version: $go_version"
	echo "   💡 Go modules update per project"
else
	echo "   ⚠️  go not found"
fi

echo ""

# macOS App Store
echo "🍎 Checking App Store updates..."
if command_exists mas; then
	available_updates=$(mas outdated 2>/dev/null | wc -l | xargs)
	if [ "$available_updates" -gt 0 ]; then
		echo "   📱 $available_updates App Store updates available"
		safe_run "mas upgrade" "Installing App Store updates"
	else
		echo "   ✅ All App Store apps up to date"
	fi
else
	echo "   💡 Install 'mas' for App Store CLI: brew install mas"
fi

echo ""

# macOS software updates
echo "🔧 Checking system updates..."
system_updates=$(softwareupdate -l 2>/dev/null | grep -c "recommended" | head -1)
if [ -z "$system_updates" ] || ! [[ $system_updates =~ ^[0-9]+$ ]]; then
	system_updates=0
fi
if [ "$system_updates" -gt 0 ]; then
	echo "   🚨 $system_updates system updates available"
	echo "   💡 Run 'softwareupdate -ia' to install (requires admin)"
else
	echo "   ✅ System up to date"
fi

echo ""
echo "======================================"
echo "✅ Package manager updates complete!"
echo "🕐 Completed at: $(date)"
