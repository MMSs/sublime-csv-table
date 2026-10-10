// Decides and applies the version bump for a merged PR from its
// Conventional Commit title. Run by .github/workflows/release.yml as
//   node scripts/release/bump.mjs "$TITLE" "$BODY" "$PR"
// Plain Node (no deps) so it works for any project language.
import { readFileSync, writeFileSync } from "node:fs";

// Every file holding the version. The first is the source
// of truth. JSON files get their top-level "version"; others get their first
// `version = "x.y.z"` line (Cargo.toml [package], pyproject [project], toml
// manifests). Keep the list in sync with a test that they all match.
const VERSION_FILES = ["pyproject.toml"];

const TITLE = /^(\w+)(\([^)]*\))?(!)?: (.+)$/;

export function bumpFor(title, body) {
  const m = TITLE.exec(title);
  if (!m) return null;
  if (m[3] || /^BREAKING[ -]CHANGE:/m.test(body)) return "major";
  if (m[1] === "feat") return "minor";
  if (m[1] === "fix" || m[1] === "perf") return "patch";
  return null;
}

/** Semver bump; before 1.0 a breaking change bumps the minor version. */
export function nextVersion(current, bump) {
  const [major, minor, patch] = current.split(".").map(Number);
  if (bump === "major") return major === 0 ? `0.${minor + 1}.0` : `${major + 1}.0.0`;
  if (bump === "minor") return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}

const TOML_VERSION = /^version = "([^"]*)"$/m;

function readVersion(file) {
  const text = readFileSync(file, "utf8");
  if (file.endsWith(".json")) return JSON.parse(text).version;
  return TOML_VERSION.exec(text)?.[1];
}

function writeVersion(file, version) {
  const text = readFileSync(file, "utf8");
  if (file.endsWith(".json")) {
    const data = JSON.parse(text);
    data.version = version;
    writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`);
  } else {
    writeFileSync(file, text.replace(TOML_VERSION, `version = "${version}"`));
  }
}

export function releaseLine(title, pr) {
  return `- ${TITLE.exec(title)?.[4] ?? title} (#${pr})`;
}

/** Inserts a dated section above the first existing "## " heading. */
export function prependRelease(changelog, version, date, line) {
  const at = changelog.indexOf("\n## ");
  const section = `\n## [${version}] - ${date}\n\n${line}\n`;
  return at < 0
    ? `${changelog.trimEnd()}\n${section}`
    : `${changelog.slice(0, at)}${section}${changelog.slice(at)}`;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [title = "", body = "", pr = ""] = process.argv.slice(2);
  const bump = bumpFor(title, body);
  if (!bump) {
    console.log(`no release for "${title}"`);
    process.exit(0);
  }
  const version = nextVersion(readVersion(VERSION_FILES[0]), bump);
  for (const file of VERSION_FILES) writeVersion(file, version);
  const line = releaseLine(title, pr);
  const date = new Date().toISOString().slice(0, 10);
  writeFileSync(
    "CHANGELOG.md",
    prependRelease(readFileSync("CHANGELOG.md", "utf8"), version, date, line),
  );
  writeFileSync(process.env.GITHUB_OUTPUT ?? "/dev/null", `version=${version}\nnotes=${line}\n`, {
    flag: "a",
  });
  console.log(`release ${version}: ${line}`);
}
