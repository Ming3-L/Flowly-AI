---
name: tmux-terminal
description: Tmux terminal multiplexer for managing persistent sessions, split panes, and remote work. Use when user mentions tmux, terminal sessions, split panes, window management, remote SSH sessions, or needs to manage multiple terminal processes.
---

# Tmux Terminal Multiplexer

Tmux manages persistent terminal sessions with split panes, windows, and detachable sessions.

## Core Concepts

| Concept | Description |
|---------|-------------|
| Session | A collection of windows |
| Window | A single terminal (tabs in other terms) |
| Pane | A split section of a window |
| Client | Attaches to a session |

## Essential Commands

```bash
# Start new session
tmux new -s mysession

# List sessions
tmux ls

# Attach to session
tmux attach -t mysession

# Detach from session (inside tmux)
Ctrl+b d

# Kill session
tmux kill-session -t mysession
```

## Pane Management

| Command | Action |
|---------|--------|
| `Ctrl+b %` | Split vertically (left/right) |
| `Ctrl+b "` | Split horizontally (top/bottom) |
| `Ctrl+b o` | Switch to next pane |
| `Ctrl+b x` | Close current pane |
| `Ctrl+b z` | Zoom pane (toggle) |
| `Ctrl+b {` | Move pane left |
| `Ctrl+b }` | Move pane right |

## Window Management

| Command | Action |
|---------|--------|
| `Ctrl+b c` | Create new window |
| `Ctrl+b n` | Next window |
| `Ctrl+b p` | Previous window |
| `Ctrl+b 0-9` | Go to window by number |
| `Ctrl+b w` | List windows |
| `Ctrl+b ,` | Rename window |
| `Ctrl+b &` | Close window |

## Navigation

| Command | Action |
|---------|--------|
| `Ctrl+b ;` | Last active pane |
| `Ctrl+b l` | Last window |
| `Ctrl+b t` | Show time |
| `Ctrl+b [` | Copy mode (scroll) |
| `q` | Exit copy mode |

## Copy Mode (Scrolling History)

```bash
# Enter copy mode
Ctrl+b [

# Navigation
j/k       # Line down/up
g/G       # Go top/bottom
Ctrl+b /  # Search forward
n/N       # Next/prev search

# Copy
Space     # Start selection
Enter     # Copy selection

# Paste
Ctrl+b ]  # Paste
```

## Configuration (~/.tmux.conf)

```bash
# Modern prefix
set -g prefix C-a
unbind C-b

# Reload config
bind r source-file ~/.tmux.conf

# Better colors
set -g default-terminal "tmux-256color"
set -ag terminal-overrides ",xterm-256color:RGB"

# Mouse support
set -g mouse on

# Vim-like pane navigation
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Better pane numbering
set -g pane-base-index 1
set -g base-index 1

# Start windows at 1
set -g base-index 1
setw -g pane-base-index 1

# Don't rename windows automatically
set -g allow-rename off
```

## Useful Plugins (TPM)

```bash
# Install TPM first
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm

# Add to ~/.tmux.conf:
set -g @plugin 'tmux-plugins/tmux-resurrect'   # Persist sessions
set -g @plugin 'tmux-plugins/tmux-continuum'   # Auto-save
set -g @plugin 'tmux-plugins/tmux-sensible'

# Install: Ctrl+b I
```

## Remote Session Workflow

```bash
# On remote server
ssh user@host
tmux new -s work

# Work as usual, detach when done: Ctrl+b d

# Later, reattach
ssh user@host
tmux attach -t work

# If connection drops, tmux keeps running!
```

## Scripts

### Session Launcher

```bash
#!/bin/bash
session="dev"

tmux has-session -t "$session" 2>/dev/null
if [ $? -eq 0 ]; then
    tmux attach -t "$session"
else
    tmux new-session -s "$session" -d
    tmux send-keys "cd ~/projects" C-m
    tmux splitw -v -p 30 -t "$session"
    tmux send-keys "htop" C-m -t "$session:0.1"
    tmux attach -t "$session"
fi
```

## Quick Reference

```
Prefix: Ctrl+b

Panes:  % | " o x z { }
Windows: c n p 0-9 w , &
Navigate: ; l t [ ]
```
