# CSV Table

Sublime Text 4 plugin with one command: **Format CSV Table**.

It reads the current buffer, detects the delimiter (or uses the one you pick), and rewrites the buffer as an aligned CSV table. Text stays left-aligned. Numbers stay right-aligned on the last digit. Quoted cells stay quoted. It then sets the syntax to CSV.

## Install

Sublime Text 4. The package folder must be named `CSV Table`.

Symlink this repository. Sublime loads it as soon as the folder is there. If the command is missing, restart Sublime.

macOS:

```bash
ln -s /path/to/sublime-csv-table "$HOME/Library/Application Support/Sublime Text/Packages/CSV Table"
```

Linux:

```bash
ln -s /path/to/sublime-csv-table "$HOME/.config/sublime-text/Packages/CSV Table"
```

Windows, from an elevated command prompt:

```bat
mklink /D "%APPDATA%\Sublime Text\Packages\CSV Table" "C:\path\to\sublime-csv-table"
```

## Use

1. Open a CSV buffer.
2. Open the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Linux and Windows).
3. Run **Format CSV Table**.
4. Choose **Auto-detect**, or pick comma, semicolon, tab, or pipe when detection is wrong.
5. Save the buffer when the result looks right.

Undo once restores the previous text. The syntax name in the status bar is CSV. Word wrap is turned off for that view so the aligned rows stay on one line.

Nothing changes when the buffer is empty, is not a table, has an unclosed quote, or you dismiss the panel.

## Tests

```bash
uv run pytest
```
