# CSV Table

A [Sublime Text 4](https://www.sublimetext.com/) plugin with one command, **Format CSV Table**, that rewrites a CSV buffer as an aligned, coloured table you can edit by hand.

It reads the current buffer, detects the delimiter (or uses the one you pick), and rewrites the buffer as an aligned CSV table. Text stays left-aligned. Numbers stay right-aligned on the last digit. Quoted cells stay quoted. Every row is padded with spaces to the width of the widest row. It then sets the syntax to CSV.

The output is still valid CSV, so you can save it and keep using it. It needs no third-party Python packages and makes no network requests.

## Requirements

- Sublime Text 4 (build 4107 or later) on macOS, Linux, or Windows.
- Nothing else. The plugin runs on Sublime's bundled Python 3.8.

## Install

The package folder must be named `CSV Table`, because the syntax paths include that name.

### Manual

Find your `Packages` folder with **Preferences → Browse Packages…**, then clone into it:

```bash
cd "<Packages folder>"
git clone https://github.com/MMSs/sublime-csv-table.git "CSV Table"
```

Sublime loads it as soon as the folder is there. If the command is missing, restart Sublime.

To update, run `git pull` in that folder. To uninstall, delete the `CSV Table` folder, and `Packages/User/CSV Table/` and `Packages/User/CSV Table.sublime-settings` if they exist.

## Use

1. Open a CSV buffer.
2. Open the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Linux and Windows).
3. Run **Format CSV Table**.
4. Choose **Auto-detect**, or pick comma, semicolon, tab, or pipe when detection is wrong.
5. Save the buffer when the result looks right.

## Colours

Each column gets its own colour, taken from your colour scheme, so it is easy to follow a column down the table. Seven colours repeat across wide tables. The header row is underlined and every other record is shaded with a faint tint of the scheme's foreground. A quoted cell that spans lines is shaded as one record.

The syntax matches the delimiter: `CSV`, `CSV (Semicolon)`, `CSV (Tab)`, or `CSV (Pipe)`. `.csv` files open as `CSV` and `.tsv` files open as `CSV (Tab)`.

To tint the stripes, the plugin writes a small rules-only scheme file to `Packages/User/CSV Table/`. Sublime merges it into the active colour scheme. To turn the header or stripes off, open **Preferences → Package Settings → CSV Table → Settings** (or **Preferences: CSV Table Settings** in the command palette) and set:

```json
{
    "underline_header": false,
    "stripe_rows": false
}
```

Highlighting stops after `max_highlight_lines` (default 20000) to keep large files fast.

Undo once restores the previous text. The syntax name in the status bar is CSV. Word wrap is turned off for that view so the aligned rows stay on one line.

Nothing changes when the buffer is empty, is not a table, has an unclosed quote, or you dismiss the panel.

## Limitations

- It formats the whole buffer, not a selection.
- Alignment assumes a monospace font. Wide characters (CJK, emoji) can push columns out of line.
- Highlighting stops after `max_highlight_lines`, so very large files are aligned but not coloured past that point.

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
