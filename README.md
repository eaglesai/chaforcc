# ccq CLI

A local command line tool for crawling, parsing, verifying, diffing and publishing
credit card agreement information to Supabase.

## Requirements

- Python 3.11+
- `pip install -r requirements.txt` (a requirements file is not provided, install
  dependencies manually or via Poetry)
- Optional: Playwright for JavaScript heavy pages

Environment variables should be stored in a `.env` file at the project root:

```
SUPABASE_URL=<your supabase project url>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
```

## Commands

All commands are executed via `python -m ccq <command> [options]`.

### Crawl

```
python -m ccq crawl --in seed.csv --out data/raw
```

Fetches agreement artifacts using the supplied seed file. Artifacts include the
response body, headers and metadata containing SHA256 hashes.

### Parse

```
python -m ccq parse --raw data/raw --out data/parsed
```

Normalises downloaded artifacts into the CardSchema v1 JSON format and produces a
manifest for subsequent steps.

### Verify

```
python -m ccq verify --in data/parsed --report data/parsed/verification_report.html
```

Performs URL reachability, keyword presence and schema sanity checks. Produces an
HTML report and a JSON summary that is required for publishing.

### Diff

```
python -m ccq diff --in data/parsed --report data/parsed/diff_report.html
```

Compares parsed cards against Supabase records and renders an HTML and JSON
summary highlighting new, changed, unchanged and failed entries.

### Publish

```
python -m ccq publish --in data/parsed --only-changed --promote
```

Upserts verified cards into Supabase staging, optionally promotes them to the
production table and records a run summary.

## Logging

Console logging defaults to INFO while detailed DEBUG logs are written to
`logs/ccq.log`.
