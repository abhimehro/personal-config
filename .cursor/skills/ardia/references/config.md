# Config and themes

When the user wants a setting changed for good, or set up from their dotfiles,
edit `~/.config/ardia/config.json` (on Linux
`~/.config/ardia/config/config.json`; `ardia config path` prints the folder)
with `ardia config` instead of clicking through Settings. Ardia reads the file
at launch and whenever it changes, and never writes it; these commands don't
need Ardia running.

```sh
ardia config init
ardia config list
ardia config set tabLayout top
ardia config set shortcuts.newTab cmd+shift+n
ardia config unset tabLayout
ardia config check
```

`init` creates the folder, `config.json` and the schemas; `list` shows every
setting with its allowed values, default and file value; shortcuts are one per
command (`''` unbinds); `unset` leaves Ardia's current value in place; `check`
reports what Ardia would complain about.

To change how Ardia looks (colours, fonts, text sizes, row heights, corners,
which sidebar parts show, icons), use `ardia theme set`, one key at a time. It
edits the active theme and a running Ardia restyles at once, no restart; with no
active theme it creates `themes/custom.json` and makes it active.

```sh
ardia theme set dark.accent '#FF9F5A'
ardia theme set type.family "Avenir Next"
ardia theme set metrics.rowHeight 40
ardia theme set metrics.radius.row 14
ardia theme set layout.hide '["navButtons"]'
ardia theme set icons.plus plus.circle
ardia theme get metrics.rowHeight
ardia theme unset metrics.rowHeight
```

Themes live in `themes/NAME.json` in that folder: `dark` and `light` colour
roles, plus `type` (font `family`, `mono`, `scale`, `sizes`, `weights`),
`metrics` (`rowHeight`, `rowGap`, `pinnedHeight`, `sidebarWidth`, `radius`),
`layout` (`hide` sidebar parts, `addressField` and `newTab` top or bottom) and
`icons` (SF Symbol swaps). KEY is the dotted path (`type.sizes.body`,
`metrics.radius.row`); under `icons` the rest is one symbol name
(`icons.chevron.down`). Every key is optional; a block left out is Ardia's own
look. `set` checks the value first and refuses a bad one with the allowed range;
`get` prints Ardia's default for a key the theme doesn't set; `unset` gives the
key back to Ardia. `--theme NAME` works on another theme. `ardia theme new NAME`
writes every role and look key with Ardia's values; the ranges and defaults are
in `theme.schema.json`. `ardia theme use NAME` (or `none`) picks one, and
`ardia theme check` checks it in Ardia's words; a bad key is skipped on its own
and the rest applies. Ask before replacing the user's own theme or config
values. Settings that grant control or send data somewhere (`cliControl`, custom
search URLs, page engines) can't go in the file; tell the user where they are in
Settings instead.

To land on a new tab at launch while keeping the session, set `launchActions`:
`ardia config set launchActions '["newTab"]'`.
