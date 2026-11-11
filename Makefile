SHELL := /bin/bash
PREFIX ?= $(HOME)/.local
BIN_DIR ?= $(PREFIX)/bin
APPS_DIR ?= $(PREFIX)/share/applications
ICONS_DIR ?= $(PREFIX)/share/icons/hicolor
CURRENT_DIR := $(shell pwd)

.PHONY: all install uninstall run clean help

all: build

build:
	@echo "Checking dependencies..."
	@which node >/dev/null || (echo "Node.js is required but not installed." && exit 1)
	@which npm >/dev/null || (echo "npm is required but not installed." && exit 1)
	@if [ ! -d "node_modules/electron" ]; then \
		echo "Installing Electron dependencies..."; \
		npm install; \
	fi
	@chmod +x sim-companies
	@echo "Build complete."

install: build
	@echo "Installing Sim Companies to $(PREFIX)..."
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(APPS_DIR)
	@ln -sf $(CURRENT_DIR)/sim-companies $(BIN_DIR)/sim-companies
	@echo "Linked binary to $(BIN_DIR)/sim-companies"
	@if [ -f scripts/generate_icons.py ]; then \
		python3 scripts/generate_icons.py; \
	fi
	@cp -f sim-companies.desktop $(APPS_DIR)/sim-companies.desktop
	@echo "Installed desktop file to $(APPS_DIR)/sim-companies.desktop"
	@if which update-desktop-database >/dev/null 2>&1; then \
		update-desktop-database $(APPS_DIR); \
	fi
	@if which gtk-update-icon-cache >/dev/null 2>&1; then \
		gtk-update-icon-cache -f -t $(ICONS_DIR) 2>/dev/null || true; \
	fi
	@echo "Installation successful! You can now launch Sim Companies via:"
	@echo "  1. Running 'sim-companies' from terminal"
	@echo "  2. Your desktop application launcher / Crystal Dock / Hyprland menu"

uninstall:
	@echo "Uninstalling Sim Companies..."
	@rm -f $(BIN_DIR)/sim-companies
	@rm -f $(APPS_DIR)/sim-companies.desktop
	@rm -f $(ICONS_DIR)/*/apps/sim-companies.png
	@if which update-desktop-database >/dev/null 2>&1; then \
		update-desktop-database $(APPS_DIR); \
	fi
	@if which gtk-update-icon-cache >/dev/null 2>&1; then \
		gtk-update-icon-cache -f -t $(ICONS_DIR) 2>/dev/null || true; \
	fi
	@echo "Sim Companies uninstalled."

run:
	@./sim-companies

clean:
	@echo "Cleaning node_modules..."
	@rm -rf node_modules package-lock.json
	@echo "Clean finished."

help:
	@echo "Sim Companies Linux Makefile targets:"
	@echo "  make          - Build/prepare Sim Companies client"
	@echo "  make install  - Install desktop entry, icons, and command-line shortcut"
	@echo "  make run      - Run Sim Companies"
	@echo "  make uninstall- Remove desktop entry and command-line shortcut"
	@echo "  make clean    - Remove installed dependencies and build cache"
