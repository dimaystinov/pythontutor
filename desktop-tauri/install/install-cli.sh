#!/bin/sh
# Register the bundled CLI for the current user; never replace another installation.
set -eu
source_cli=$1
user_home=$2
cli_dir="$user_home/.local/share/pythontutor/bin"
mkdir -p "$cli_dir"
if ! cmp -s "$source_cli" "$cli_dir/opencode"; then
  cp "$source_cli" "$cli_dir/opencode.new"
  chmod 755 "$cli_dir/opencode.new"
  mv -f "$cli_dir/opencode.new" "$cli_dir/opencode"
fi
marker='# PythonTutor OpenCode CLI'
for profile in .zprofile .zshrc .bash_profile .bashrc .profile; do
  profile_path="$user_home/$profile"
  if ! grep -qF "$marker" "$profile_path" 2>/dev/null; then
    cat >> "$profile_path" <<'PROFILE'

# PythonTutor OpenCode CLI
case ":$PATH:" in
  *":$HOME/.local/share/pythontutor/bin:"*) ;;
  *) export PATH="$PATH:$HOME/.local/share/pythontutor/bin" ;;
esac
PROFILE
  fi
done
