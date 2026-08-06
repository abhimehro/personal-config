# Dev Environment Setup (Ghostty + fish + Neovim)

This document captures the steps to recreate the terminal and editor setup on a
new macOS machine. It assumes Apple Silicon, Homebrew, and fish as the primary
shell.

---

## 1. Install core tools

1. Install Homebrew (if needed) from https://brew.sh.
2. Install base tools:

```bash
brew install git fish neovim tree-sitter-cli lua-language-server
brew install python # Homebrew Python 3.x
npm install -g neovim # Node provider for Neovim
npm install -g pyright bash-language-server \
  vscode-langservers-extracted yaml-language-server \
  typescript typescript-language-server
```

3. Install Ghostty from the official site or Homebrew cask, then make it the
   main terminal.

---

## 2. Shell (fish) configuration

1. Clone the `personal-config` repo:

```bash
mkdir -p ~/Documents/dev
cd ~/Documents/dev
git clone git@github.com:<user>/personal-config.git
```

2. Symlink or copy fish config:

```bash
mkdir -p ~/.config/fish
ln -s ~/dev/personal-config/configs/.config/fish/config.fish \
  ~/.config/fish/config.fish
```

3. Ensure `fish_add_path` includes `/opt/homebrew/bin` plus user bin dirs, and
   that aliases/tools (eza, bat, rg, fd, etc.) match what is installed.

---

## 3. Ghostty configuration

1. Create/edit Ghostty config (macOS default):

```bash
mkdir -p ~/Library/Application\ Support/com.mitchellh.ghostty
$EDITOR ~/Library/Application\ Support/com.mitchellh.ghostty/config.ghostty
```

2. Key options (already tracked in this repo):

```text
theme = dracula # Dracula Ghostty theme file in ~/.config/ghostty/themes
background-opacity = 0.96
unfocused-split-opacity = 0.90

font-family = "Cutive Mono"
font-size = 14.0

window-save-state = always
window-inherit-working-directory = true
working-directory = inherit
window-new-tab-position = current
macos-option-as-alt = left

shell-integration = fish

keybind = global:cmd+backquote=toggle_quick_terminal
keybind = global:super+s=toggle_secure_input

keybind = super+enter=new_split:auto
keybind = super+shift+left=goto_split:left
keybind = super+shift+right=goto_split:right
keybind = super+shift+up=goto_split:up
keybind = super+shift+down=goto_split:down

scrollback-limit = 200000000
```

3. Install Dracula for Ghostty:

- Copy the `dracula` theme file into `~/.config/ghostty/themes/`.
- Confirm with `ghostty +list-themes` and set `theme = dracula`.

---

## 4. Neovim + Dracula + Treesitter

### 4.1 Python host (PEP 668-safe)

1. Create Neovim-specific venv and install `pynvim`:

```bash
mkdir -p ~/.local/share/nvim
/opt/homebrew/bin/python3 -m venv ~/.local/share/nvim/venv
~/.local/share/nvim/venv/bin/python3 -m pip install pynvim
```

### 4.2 Install plugins using native `pack`

1. Treesitter and LSP configs:

```bash
mkdir -p ~/.local/share/nvim/site/pack/nvim/start

git clone https://github.com/nvim-treesitter/nvim-treesitter \
  ~/.local/share/nvim/site/pack/nvim/start/nvim-treesitter

git clone https://github.com/neovim/nvim-lspconfig \
  ~/.local/share/nvim/site/pack/nvim/start/nvim-lspconfig
```

2. Dracula for Neovim:

```bash
mkdir -p ~/.config/nvim/pack/themes/start
git clone https://github.com/dracula/vim.git \
  ~/.config/nvim/pack/themes/start/dracula
```

### 4.3 `init.lua`

Create `~/.config/nvim/init.lua` (or overwrite) with:

```lua
vim.g.python3_host_prog = vim.fn.expand("~/.local/share/nvim/venv/bin/python3")

vim.cmd("packadd nvim-treesitter")
vim.cmd("packadd nvim-lspconfig")

-- Colors
vim.opt.termguicolors = true
vim.cmd.colorscheme("dracula")

-- UI / QoL
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.cursorline = true
vim.opt.signcolumn = "yes"

vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.smartindent = true

vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.incsearch = true
vim.opt.hlsearch = true

vim.opt.splitbelow = true
vim.opt.splitright = true
vim.opt.updatetime = 300
vim.opt.timeoutlen = 400

vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0

-- Treesitter
require("nvim-treesitter.configs").setup({
  ensure_installed = {
    "lua", "vim", "vimdoc", "python", "r", "bash",
    "javascript", "typescript", "tsx", "html", "css", "markdown", "markdown_inline",
    "swift",
  },
  highlight = { enable = true },
  indent = { enable = true },
})

-- LSP servers (require language servers to be installed)
vim.lsp.enable("pyright")
vim.lsp.enable("lua_ls")
vim.lsp.enable("bashls")
vim.lsp.enable("jsonls")
vim.lsp.enable("yamlls")
vim.lsp.enable("ts_ls")
vim.lsp.enable("html")
vim.lsp.enable("cssls")
vim.lsp.enable("r_language_server")
vim.lsp.enable("sourcekit")

local lsp_group = vim.api.nvim_create_augroup("UserLspConfig", {})

vim.api.nvim_create_autocmd("LspAttach", {
  group = lsp_group,
  callback = function(ev)
    local opts = { buffer = ev.buf, silent = true }
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
    vim.keymap.set("n", "gr", vim.lsp.buf.references, opts)
    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
    vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, opts)
    vim.keymap.set("n", "[d", vim.diagnostic.goto_prev, opts)
    vim.keymap.set("n", "]d", vim.diagnostic.goto_next, opts)
  end,
})
```

Then, inside Neovim:

```vim
:checkhealth
:TSUpdate
```

Everything should report OK for Treesitter, providers, and LSP.

---

## 5. Raycast + Ghostty launch configuration

1. Install the Ghostty Raycast extension from the Raycast Store.
2. In the extension's YAML textbox, define a launch config, for example:

```yaml
name: Ghostty – Two Window Dev
windows:
  - tabs:
      - title: personal-config
        color: Green
        layout:
          cwd: /Users/speedybee/dev/personal-config
      - title: dev-root
        color: Blue
        layout:
          cwd: /Users/speedybee/Documents/dev
      - title: downloads
        color: Cyan
        layout:
          cwd: /Users/speedybee/Downloads
  - tabs:
      - title: nvim
        color: Magenta
        layout:
          cwd: /Users/speedybee/dev/personal-config
          commands:
            - exec: nvim
```

3. Bind a Raycast hotkey to "Run Launch Configuration" for the Ghostty
   extension so it opens both windows on demand.

---

## 6. Backup & restore

- Track at least these paths in `personal-config` (or your dotfiles repo):

  - `~/Library/Application Support/com.mitchellh.ghostty/config.ghostty`
  - `~/.config/fish/config.fish`
  - `~/.config/nvim/init.lua`
  - `~/.config/nvim/pack/themes/start/dracula`
  - `~/.local/share/nvim/site/pack/nvim/start/` (Treesitter + LSP configs; can
    also be re-cloned on new machines)

- On a new machine, clone `personal-config`, re-create symlinks, then follow
  sections 1–5 above.
