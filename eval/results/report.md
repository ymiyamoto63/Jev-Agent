## Per-task results (pass / cost USD)

| task | kind | lang | haiku | sonnet | opus | label (cheapest pass) |
|---|---|---|---|---|---|---|
| 01-search-env | search | en | ✅ $0.018 | ✅ $0.148 | ✅ $0.285 | **haiku** |
| 02-search-callers | search | ja | ❌ $0.017 | ✅ $0.061 | ✅ $0.128 | **sonnet** |
| 03-search-exception | search | en | ✅ $0.023 | ✅ $0.057 | ✅ $0.093 | **haiku** |
| 04-run-tests | test_run | ja | ✅ $0.016 | ✅ $0.047 | ✅ $0.084 | **haiku** |
| 05-run-cli | test_run | en | ✅ $0.014 | ✅ $0.043 | ✅ $0.076 | **haiku** |
| 06-rename | mechanical_edit | en | ✅ $0.031 | ✅ $0.066 | ✅ $0.131 | **haiku** |
| 07-typo | mechanical_edit | ja | ✅ $0.019 | ✅ $0.053 | ✅ $0.118 | **haiku** |
| 08-page-size | mechanical_edit | en | ✅ $0.042 | ✅ $0.057 | ✅ $0.125 | **haiku** |
| 09-cli-json | feature | en | ✅ $0.036 | ✅ $0.071 | ✅ $0.159 | **haiku** |
| 10-validation | feature | ja | ✅ $0.023 | ✅ $0.066 | ✅ $0.171 | **haiku** |
| 11-pricing | feature | en | ✅ $0.038 | ✅ $0.057 | ✅ $0.217 | **haiku** |
| 12-ttl-cache | feature | ja | ✅ $0.087 | ✅ $0.092 | ✅ $0.232 | **haiku** |
| 13-paginate | debug | en | ✅ $0.069 | ✅ $0.065 | ✅ $0.176 | **haiku** |
| 14-add-months | debug | ja | ✅ $0.054 | ✅ $0.073 | ✅ $0.144 | **haiku** |
| 15-rounding | debug | en | ✅ $0.083 | ✅ $0.099 | ✅ $0.165 | **haiku** |
| 16-race | debug | ja | ✅ $0.047 | ✅ $0.092 | ✅ $0.230 | **haiku** |
| 17-double-discount | debug | en | ✅ $0.059 | ✅ $0.082 | ✅ $0.167 | **haiku** |
| 18-security-review | review | ja | ✅ $0.042 | ✅ $0.084 | ✅ $0.188 | **haiku** |
| 19-diff-review | review | en | ✅ $0.016 | ✅ $0.040 | ✅ $0.076 | **haiku** |
| 20-event-bus | design | ja | ✅ $0.108 | ✅ $0.125 | ✅ $0.264 | **haiku** |

## Labels by kind

- search: haiku, sonnet, haiku
- test_run: haiku, haiku
- mechanical_edit: haiku, haiku, haiku
- feature: haiku, haiku, haiku, haiku
- debug: haiku, haiku, haiku, haiku, haiku
- review: haiku, haiku
- design: haiku

## Router comparison

| router | success | total cost | cost / success | under-routed | over-routed | choices |
|---|---|---|---|---|---|---|
| all-haiku | 19/20 | $0.84 | $0.044 | 1 | 0 | H20 S0 O0 |
| all-haiku +esc | 20/20 | $0.91 | $0.045 | 1 | 0 | H20 S0 O0 |
| all-sonnet | 20/20 | $1.48 | $0.074 | 0 | 19 | H0 S20 O0 |
| all-sonnet +esc | 20/20 | $1.48 | $0.074 | 0 | 19 | H0 S20 O0 |
| all-opus | 20/20 | $3.23 | $0.161 | 0 | 20 | H0 S0 O20 |
| oracle | 20/20 | $0.89 | $0.044 | 0 | 0 | H19 S1 O0 |
| keyword (PoC-1) | 20/20 | $1.31 | $0.066 | 0 | 14 | H5 S14 O1 |
| keyword (PoC-1) +esc | 20/20 | $1.31 | $0.066 | 0 | 14 | H5 S14 O1 |
| jevroute (mock) | 20/20 | $1.78 | $0.089 | 0 | 16 | H3 S12 O5 |
| jevroute (mock) +esc | 20/20 | $1.78 | $0.089 | 0 | 16 | H3 S12 O5 |

## jevroute (mock): per-task decisions

| task | label | chosen | passed | +esc tried |
|---|---|---|---|---|
| 01-search-env | haiku | haiku | ✅ | haiku |
| 02-search-callers | sonnet | sonnet | ✅ | sonnet |
| 03-search-exception | haiku | sonnet | ✅ | sonnet |
| 04-run-tests | haiku | sonnet | ✅ | sonnet |
| 05-run-cli | haiku | sonnet | ✅ | sonnet |
| 06-rename | haiku | haiku | ✅ | haiku |
| 07-typo | haiku | sonnet | ✅ | sonnet |
| 08-page-size | haiku | sonnet | ✅ | sonnet |
| 09-cli-json | haiku | haiku | ✅ | haiku |
| 10-validation | haiku | sonnet | ✅ | sonnet |
| 11-pricing | haiku | sonnet | ✅ | sonnet |
| 12-ttl-cache | haiku | sonnet | ✅ | sonnet |
| 13-paginate | haiku | sonnet | ✅ | sonnet |
| 14-add-months | haiku | sonnet | ✅ | sonnet |
| 15-rounding | haiku | sonnet | ✅ | sonnet |
| 16-race | haiku | opus | ✅ | opus |
| 17-double-discount | haiku | opus | ✅ | opus |
| 18-security-review | haiku | opus | ✅ | opus |
| 19-diff-review | haiku | opus | ✅ | opus |
| 20-event-bus | haiku | opus | ✅ | opus |
