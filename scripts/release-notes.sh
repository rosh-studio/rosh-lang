#!/bin/bash
#
# release-notes.sh - Generate release notes from git commits
#
# This script extracts commit messages and formats them for release notes.
# Output is designed to be human-readable or fed to AI for polishing.
#
# USAGE:
#   ./scripts/release-notes.sh [OPTIONS] [TAG]
#
# OPTIONS:
#   -h, --help      Show this help message
#   -a, --all       Show all commits (full history)
#   -t, --tags      List all available tags
#   -r, --raw       Raw commit format (no grouping)
#   -m, --markdown  Output in markdown format
#   --since TAG     Commits since TAG (default: latest tag)
#   --until TAG     Commits until TAG (default: HEAD)
#
# EXAMPLES:
#   ./scripts/release-notes.sh                    # Commits since last tag
#   ./scripts/release-notes.sh v0.1.11            # Commits since v0.1.11
#   ./scripts/release-notes.sh --since v0.1.10 --until v0.1.11
#   ./scripts/release-notes.sh --all              # Full commit history
#   ./scripts/release-notes.sh --tags             # List all tags
#   ./scripts/release-notes.sh -m > RELEASE.md    # Markdown output
#
# COMMIT TYPES (conventional commits):
#   feat:     New features
#   fix:      Bug fixes
#   docs:     Documentation changes
#   refactor: Code refactoring
#   test:     Test changes
#   chore:    Maintenance tasks
#
# TIP: Pipe output to Claude for polished release notes:
#   ./scripts/release-notes.sh v0.1.12 | pbcopy
#   Then ask Claude: "Turn these commits into user-friendly release notes"
#
# -----------------------------------------------------------------------------

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Defaults
SINCE_TAG=""
UNTIL_REF="HEAD"
RAW_MODE=false
MARKDOWN=false
SHOW_ALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            sed -n '3,40p' "$0" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        -t|--tags)
            echo "Available tags:"
            git tag -l --sort=-version:refname | head -20
            exit 0
            ;;
        -a|--all)
            SHOW_ALL=true
            shift
            ;;
        -r|--raw)
            RAW_MODE=true
            shift
            ;;
        -m|--markdown)
            MARKDOWN=true
            shift
            ;;
        --since)
            SINCE_TAG="$2"
            shift 2
            ;;
        --until)
            UNTIL_REF="$2"
            shift 2
            ;;
        v*)
            # Positional tag argument
            SINCE_TAG="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

# If no since tag specified, find the latest tag
if [[ -z "$SINCE_TAG" && "$SHOW_ALL" == false ]]; then
    SINCE_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [[ -z "$SINCE_TAG" ]]; then
        echo "No tags found. Use --all for full history."
        exit 1
    fi
fi

# Build git log range
if [[ "$SHOW_ALL" == true ]]; then
    RANGE="$UNTIL_REF"
    RANGE_DESC="all commits"
else
    RANGE="${SINCE_TAG}..${UNTIL_REF}"
    RANGE_DESC="commits since $SINCE_TAG"
fi

# Get commits
get_commits() {
    local type="$1"
    local pattern="^${type}:"
    git log "$RANGE" --oneline --pretty=format:"%s" 2>/dev/null | grep -E "$pattern" || true
}

get_all_commits() {
    git log "$RANGE" --oneline --pretty=format:"%h %s" 2>/dev/null
}

# Count commits
COMMIT_COUNT=$(git rev-list --count "$RANGE" 2>/dev/null || echo "0")

if [[ "$COMMIT_COUNT" == "0" ]]; then
    echo "No commits found in range: $RANGE"
    exit 0
fi

# Raw mode - just dump commits
if [[ "$RAW_MODE" == true ]]; then
    echo "# $RANGE_DESC ($COMMIT_COUNT commits)"
    echo ""
    get_all_commits
    exit 0
fi

# Markdown header
if [[ "$MARKDOWN" == true ]]; then
    echo "# Release Notes"
    echo ""
    echo "**Range:** $RANGE_DESC ($COMMIT_COUNT commits)"
    echo ""
else
    echo -e "${CYAN}=== Release Notes ===${NC}"
    echo -e "Range: ${YELLOW}$RANGE_DESC${NC} ($COMMIT_COUNT commits)"
    echo ""
fi

# Group by type
print_section() {
    local title="$1"
    local type="$2"
    local emoji="$3"

    local commits=$(get_commits "$type")
    if [[ -n "$commits" ]]; then
        if [[ "$MARKDOWN" == true ]]; then
            echo "## $emoji $title"
            echo ""
            echo "$commits" | sed "s/^${type}: //" | while read -r line; do
                echo "- $line"
            done
            echo ""
        else
            echo -e "${GREEN}$emoji $title${NC}"
            echo "$commits" | sed "s/^${type}: /  - /"
            echo ""
        fi
    fi
}

print_section "New Features" "feat" "✨"
print_section "Bug Fixes" "fix" "🐛"
print_section "Documentation" "docs" "📚"
print_section "Refactoring" "refactor" "♻️"
print_section "Tests" "test" "🧪"
print_section "Chores" "chore" "🔧"

# Other commits (don't match conventional format)
OTHER=$(git log "$RANGE" --oneline --pretty=format:"%s" 2>/dev/null | grep -vE "^(feat|fix|docs|refactor|test|chore):" || true)
if [[ -n "$OTHER" ]]; then
    if [[ "$MARKDOWN" == true ]]; then
        echo "## 📝 Other Changes"
        echo ""
        echo "$OTHER" | while read -r line; do
            echo "- $line"
        done
        echo ""
    else
        echo -e "${YELLOW}📝 Other Changes${NC}"
        echo "$OTHER" | sed 's/^/  - /'
        echo ""
    fi
fi

# Footer
if [[ "$MARKDOWN" == true ]]; then
    echo "---"
    echo "*Generated by release-notes.sh*"
else
    echo -e "${CYAN}---${NC}"
    echo "Tip: Use -m for markdown, or pipe to Claude for polishing"
fi
