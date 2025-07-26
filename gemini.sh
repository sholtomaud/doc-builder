#!/bin/bash

# A wrapper script for safely interacting with Gemini CLI on this project.
# It enforces the best practices outlined in GEMINI.md.

# --- Colors for emphasis ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Helper Functions ---

check_git_status() {
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}WARNING: You have uncommitted changes.${NC}"
        echo "It's highly recommended to commit your changes before starting a session."
        read -p "Do you want to continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborting."
            exit 1
        fi
    fi
}

run_preflight_checks() {
    echo -e "${GREEN}Running pre-flight checks (linting and testing)...${NC}"
    if ! make lint || ! make test; then
        echo -e "${YELLOW}Pre-flight checks failed. Please fix the issues before starting a session.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Pre-flight checks passed!${NC}"
}

start_session() {
    echo
    echo -e "${GREEN}Starting Gemini CLI session...${NC}"
    echo "--------------------------------------------------"
    echo -e "Safety Reminders (from Taylor Mullen):"
    echo -e "1. ${YELLOW}Review all permissions carefully before allowing.${NC}"
    echo -e "2. This session is running with ${GREEN}--sandbox${NC} and ${GREEN}--checkpointing${NC}."
    echo -e "3. Use ${YELLOW}/checkpoint 'message'${NC} to save your progress."
    echo -e "4. Use ${YELLOW}/restore${NC} to undo changes."
    echo "--------------------------------------------------"
    echo

    # Launch Gemini with our standard safety flags
    gemini --sandbox --checkpointing
}

# --- Main Script Logic ---

# Default action is to run the full, safe start-up procedure
if [[ -z "$1" ]] || [[ "$1" == "start" ]]; then
    check_git_status
    run_preflight_checks
    start_session
elif [[ "$1" == "lint" ]]; then
    make lint
elif [[ "$1" == "test" ]]; then
    make test
else
    echo "Usage: ./gemini.sh [command]"
    echo
    echo "Commands:"
    echo "  start   (default) Run pre-flight checks and start a safe Gemini session."
    echo "  lint              Just run the linter."
    echo "  test              Just run the test suite."
    echo
    echo "This script helps you follow the safety guidelines in GEMINI.md."
fi
