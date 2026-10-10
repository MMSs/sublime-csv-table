"""Column scopes and colour scheme rules shared by the plugin and the syntaxes."""

from typing import Dict, List

# Scopes that common colour schemes give distinct foregrounds. Columns cycle
# through them, so column 8 looks like column 1.
COLUMN_SCOPES = [
    "variable.other",
    "keyword.control",
    "string.unquoted",
    "constant.numeric",
    "entity.name.function",
    "entity.name.tag",
    "support.type",
]

# Quote marks and doubled-quote escapes inside CSV cells.
QUOTE_SCOPES = [
    "text.csv punctuation.definition.string",
    "text.csv constant.character.escape",
]


def column_scope(number: int) -> str:
    """Return the scope the syntaxes give column `number` (1-based, 1..7)."""
    return f"{COLUMN_SCOPES[number - 1]}.column-{number}.csv"


def scheme_rules(
    foreground: str,
    stripe_scope: str,
    stripe_alpha: str,
    stripes: bool,
    color_columns: bool,
) -> List[Dict[str, str]]:
    """Return the rules merged into the active colour scheme.

    `foreground` is the scheme's #rrggbb foreground. Stripes are a faint
    tint of it. With column colours off, every column, and the quotes in
    it, is drawn in it.
    """
    rules = []
    if stripes:
        rules.append(
            {
                "name": "CSV Table stripe",
                "scope": stripe_scope,
                "background": foreground + stripe_alpha,
            }
        )
    if not color_columns:
        rules.append(
            {
                "name": "CSV Table plain columns",
                "scope": ", ".join(
                    [column_scope(n) for n in range(1, len(COLUMN_SCOPES) + 1)]
                    + QUOTE_SCOPES
                ),
                "foreground": foreground,
            }
        )
    return rules
