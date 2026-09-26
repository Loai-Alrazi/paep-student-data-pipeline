# Multi-Source Student Data Pipeline

A group project for the PAEP Data Engineering course: a Python ETL pipeline that collects student data from three sources (CSV file, REST API, and SQLite database), validates and cleans it, integrates it into one analysis-ready dataset, and produces both valid and rejected outputs with full logging, metrics, and lineage.

The pipeline follows this flow:

```text
Multiple Sources (CSV | REST API | SQLite)
                    |
                 Extract
                    |
                 Validate
                    |
                  Clean
                    |
                Integrate
                    |
                Transform
                    |
             Final Validation
                    |
        +-----------+-----------+
        |                       |
  Valid Records          Invalid Records
        |                       |
final_dataset.csv      rejected_records.csv
```

## Project Overview

The same student exists in three different systems: identity data in a CSV file, academic data behind a REST API, and course enrollments in a SQLite database. This project builds one automated pipeline that:

- Extracts all three sources (the API source always works over real HTTP requests).
- Validates each source against the data quality rules before anything is merged.
- Cleans recoverable problems (duplicates, whitespace, inconsistent case).
- Integrates the sources on the shared `student_id` key (one row per student).
- Transforms the data: type handling, missing-value imputation from raw-API medians, and derived columns.
- Runs a final validation and splits the result into valid and rejected records.
- Writes the outputs and records stage-by-stage logs and pipeline metrics.

On the canonical dataset the pipeline produces **8 valid records** and **6 rejected records**, and asserts this end-to-end in the test suite. The intended final order is documented in [PROJECT_PLAN.md](PROJECT_PLAN.md); field schemas, quality rules, and expected values are defined in [DATA_CONTRACT.md](DATA_CONTRACT.md).

## Architecture

The project is a Python package structure — no stage lives inside `main.py`:

```text
student_data_pipeline/
├── app/
│   ├── sources/        # CSVSource, APISource, DatabaseSource, BaseSource contract
│   ├── transformation/ # cleaner.py, transformer.py, integration.py
│   ├── validation/     # quality.py (source and final validation rules)
│   ├── output/         # csv_writer.py
│   └── utils/          # config_loader, logger, metrics, incremental, lineage
├── data/
│   ├── raw/            # canonical students.csv
│   ├── processed/      # final_dataset.csv (generated)
│   ├── rejected/       # rejected_records.csv (generated)
│   └── state/          # pipeline_state.json (incremental state, generated)
├── database/           # schema.sql, seed.sql, students.db
├── logs/               # pipeline.log (generated)
├── mock_api/           # local REST API serving the canonical seed data
├── tests/              # 283 tests
├── main.py             # orchestration only
├── config.json         # runtime configuration
└── requirements.txt    # pandas, requests, pytest
```

`main.py` composes reusable modules only — extraction, source validation, cleaning, integration, transformation, lineage, final validation, incremental processing, metrics, logging, and output writing. All configuration (paths, endpoint, timeout, incremental mode) is loaded at runtime from `config.json` through `app/utils/config_loader.py`; nothing is hard-coded.

## Data Sources

All three sources share the `student_id` key.

| Source | Location | Fields | Records |
| --- | --- | --- | --- |
| CSV | `data/raw/students.csv` | `student_id`, `student_name`, `age`, `major`, `city` | 14 |
| REST API | `http://localhost:8000/students` (served by `mock_api/server.py`) | `student_id`, `gpa`, `attendance`, `status` | 13 |
| SQLite | `database/students.db` (`courses` ⟕ `enrollments`) | `student_id`, `course_name`, `credit_hours`, `semester`, `score` | 12 joined |

- The CSV intentionally contains a blank ID, an extra exact duplicate, an out-of-range age, a missing major, and extra/inconsistent whitespace.
- The API source sends a real HTTP request, receives and parses JSON, and explicitly handles connection errors, timeouts, HTTP errors, invalid JSON, and empty responses. It never reads the seed file (`mock_api/students_academic.json`) directly.
- The SQLite source runs the integrated read-only JOIN query defined in `DATA_CONTRACT.md` and always closes the connection.

## ETL Pipeline

`main.py` executes the stages in the official order:

1. **Extract** — `load_data()` (CSV), `extract_api_data()` (HTTP), `extract_database()` (SQL JOIN), each returning a raw `DataFrame`.
2. **Validate** — source validation enforces the quality rules per record; failures (missing ID, out-of-range values, IDs incompatible with the canonical CSV IDs) are collected for the rejected output.
3. **Clean** — exact duplicates removed, leading/trailing whitespace stripped, multiple internal spaces collapsed, text case normalized.
4. **Integrate** — the three cleaned sources are merged on `student_id`; a student must be present in all three contributing sources, giving one row per student.
5. **Transform** — missing GPA/attendance imputed with medians computed from the complete raw API source (3.0 and 85), types normalized, and derived columns `performance_level` and `attendance_status` added from the rule tables in `DATA_CONTRACT.md`.
6. **Final Validation** — the same quality rules applied to the transformed dataset; anything still invalid is split off.
7. **Load** — valid records to `data/processed/final_dataset.csv`, rejected records with their reasons to `data/rejected/rejected_records.csv`.

## Data Quality

Validation rules (checked at source validation and again at final validation):

| Rule | Constraint |
| --- | --- |
| `student_id` | not null; unique after exact-duplicate removal |
| `age` | 16 ≤ age ≤ 80 |
| `gpa` | 0 ≤ gpa ≤ 4 |
| `attendance` | 0 ≤ attendance ≤ 100 |
| `score` | 0 ≤ score ≤ 100 |
| cross-source IDs | API/Database IDs must be compatible with the canonical CSV IDs |

Recoverable problems are repaired before the final split; unrecoverable problems are rejected with an explicit reason.

**Rejected records on the canonical dataset (6):**

| Student ID | Rejection reason |
| --- | --- |
| `1005` | Invalid Age (`15`) |
| `1003` | Invalid Attendance (`105`) |
| `1004` | Invalid GPA (`4.5`) |
| `1010` | Invalid Score (`105`) |
| `1099` | Incompatible student_id |
| *(blank)* | Missing student_id |

## Reference Results (Canonical Run)

These are the documented expected outcomes of running the pipeline on the canonical dataset — they are reference values verified by tests, not hard-coded values in the pipeline code.

| Metric | Value |
| --- | --- |
| CSV records | 14 |
| API records | 13 |
| Database records (joined) | 12 |
| Duplicate records (extra copies removed) | 1 |
| Missing values (raw, before recovery) | 4 |
| Integrated / final valid records | 8 |
| Rejected records | 6 |

Imputation reference values, computed from the full raw API source before any rejection:

- Valid GPA median = **3.0** → student `1002` GPA becomes **3.0**.
- Valid attendance median = **85** → student `1011` attendance becomes **85**.

Final valid students: `1001, 1002, 1006, 1007, 1008, 1009, 1011, 1012`.

## Installation

Requires Python 3.12+.

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `requests`, `pytest` (plus the Python standard library, including `sqlite3`).

## Running

1. **Start the mock REST API** (serves `GET /students` on port 8000):

   ```bash
   python mock_api/server.py
   ```

2. **Run the pipeline** in a second terminal:

   ```bash
   python main.py
   ```

   The pipeline reads `config.json` by default and writes `data/processed/final_dataset.csv`, `data/rejected/rejected_records.csv`, `data/state/pipeline_state.json`, and `logs/pipeline.log`.

3. **Run the tests**:

   ```bash
   python -m pytest -q
   ```

   The test suite (283 tests) spins up its own mock API on a free port, so it does not need the server from step 1.

## Output

| File | Contents |
| --- | --- |
| `data/processed/final_dataset.csv` | 8 valid records, 15 columns: `student_id`, `student_name`, `age`, `major`, `city`, `gpa`, `attendance`, `status`, `course_name`, `credit_hours`, `semester`, `score`, `performance_level`, `attendance_status`, `source` |
| `data/rejected/rejected_records.csv` | 6 rejected records with their `error_reason` values |
| `logs/pipeline.log` | INFO log for every stage plus the pipeline metrics summary |
| `data/state/pipeline_state.json` | incremental processing state from the last run |

## Configuration

`config.json` defines the source paths, the API endpoint and timeout, the output and log paths, and the incremental settings. The pipeline loads it at runtime; a different configuration file can be passed programmatically via `main(config_path=...)`.

## Incremental Processing

When `incremental.enabled` is `true`, each run fingerprints the integrated data against the saved state in `data/state/pipeline_state.json`. New or changed students are fully reprocessed; unchanged students are reused from the previous final output. A change in the raw-API imputation medians is part of the fingerprint, so affected rows are reprocessed instead of reusing stale values. If the previous final output is missing or unusable, the run falls back to full processing, and a failed state save rolls both the output and the state back to their previous versions.

## Data Lineage

The final `source` column records where each row came from. Records built from all three sources carry the value `CSV|API|DATABASE`, as defined in `DATA_CONTRACT.md`.

## Pipeline Metrics

Every run logs a summary with total records per source, integrated, valid, rejected, duplicate, and missing-value counts, plus the measured processing time, for example:

```text
---
## PIPELINE EXECUTION SUMMARY

CSV Records : 14
API Records : 13
Database Records : 12
Integrated Records : 8
Valid Records : 8
Rejected Records : 6
Duplicate Records : 1
Missing Values : 4
Processing Time : 2.20 seconds
-----------------------------------
```

## Reusable Source Architecture

All three sources implement one contract: `BaseSource` (abstract class in `app/sources/base_source.py`) with a single method `extract() -> pd.DataFrame`. `CSVSource`, `APISource`, and `DatabaseSource` subclass it, while the original module-level functions (`load_data`, `extract_api_data`, `extract_database`) remain as backward-compatible wrappers. A future source such as Excel, JSON, or MySQL can be added by implementing `BaseSource.extract()` without rewriting the pipeline — no factory, registry, or dependency injection.

## Testing

The suite has 283 tests covering the assignment's required checks and beyond:

- CSV loading, API extraction over real HTTP requests, and SQLite extraction (including error paths: connection errors, timeouts, HTTP errors, invalid JSON, empty responses).
- Duplicate removal, missing-value handling and imputation, invalid-record rejection with reasons, source integration, and `final_dataset.csv` creation.
- An end-to-end pipeline test that runs the full order against the canonical fixture data and asserts the expected 8 valid / 6 rejected result, plus tests for configuration loading, logging, metrics, incremental processing, lineage, cleaning, transformation, and output writing.

## Assignment Questions

Answers to the final student questions, based on this project.

### 1. Why do we need a data pipeline when dealing with multiple sources?

Because the same real-world entity is usually split across systems. In this project, one student's identity is in a CSV file, their GPA and attendance are behind a REST API, and their enrollments are in SQLite — with different formats, different quality problems, and no way to answer a question like "which at-risk students study which courses?" without combining them. The pipeline automates extraction, quality checks, and merging on `student_id` into one repeatable step, so every run produces the same trustworthy dataset instead of a fragile manual copy-paste merge.

### 2. What is the difference between raw data and processed data?

Raw data is exactly what the sources provide, problems included: our CSV has a blank `student_id`, an extra duplicate of student `1007`, age `15`, and names like `" Ahmed Ali "` with extra spaces; the API has `null` GPA, attendance `105`, and an incompatible ID `1099`. Processed data is what leaves the pipeline: `final_dataset.csv` has 8 rows, one per student, with cleaned text, imputed values, derived columns, and a `source` column — ready to load into analysis or a model without any further fixing.

### 3. What is the difference between Extract, Transform, and Load?

Extract reads data from the sources without changing it: `load_data()` reads the CSV, `extract_api_data()` performs the HTTP request, and `extract_database()` runs the SQL JOIN. Transform turns the extracted records into the analysis shape: cleaning, imputation, type normalization, and derived columns like `performance_level`. Load writes the result to its destination: `write_csv()` saves the valid records to `final_dataset.csv` and the failures to `rejected_records.csv`. In this project, validation wraps the transformation stages, per the official order Validate → Clean → Integrate → Transform → Final Validation → Load.

### 4. What problems did you face while integrating the data?

The three sources had different shapes and different problems for the same student: the API contained an ID (`1099`) that does not exist in the canonical CSV IDs, so it had to be rejected as incompatible; student `1006` had a missing major and the API was missing GPA for `1002` and attendance for `1011`, so the merge would have produced nulls without a recovery policy; and the blank CSV ID made pandas type the whole ID column as float, so the final snapshot normalizes IDs back to integers. The subtlest problem was that imputation medians must come from the full raw API source — computing them from the already-validated subset gave 2.9/80 instead of the correct 3.0/85.

### 5. How did you handle missing values?

With one explicit strategy per field, documented in `DATA_CONTRACT.md`: a missing `major` is a normal categorical absence and becomes `Unknown`; missing `gpa` and `attendance` are imputed with the median of the valid values of the complete raw API source (3.0 and 85) — the median because it is robust against the planted outliers (GPA 4.5, attendance 105) that a mean would absorb. A missing `student_id`, however, is never recoverable — the row cannot be keyed or trusted, so it is rejected with `Missing student_id`. Nothing is imputed silently: the transformer logs how many values it filled.

### 6. How did you handle duplicate records?

The pipeline distinguishes exact duplicates from conflicting ones. An extra row identical for the same `student_id` (our CSV has a duplicated `1007`) is a recoverable problem: `clean_data` removes the extra copy and keeps one, and the duplicate counter reports 1 for the canonical data. A duplicate ID with *different* data is treated as unrecoverable — it is rejected instead of being silently resolved, because the pipeline cannot know which version is correct. Duplicate removal happens at the assignment's granularity of one row per `student_id`.

### 7. How did you handle invalid records?

They are never deleted quietly. Each record passes source validation and final validation against the quality rules; anything that fails is written to `data/rejected/rejected_records.csv` together with an explicit `error_reason` — for example `Invalid Age` for student `1005`, `Invalid GPA` for `1004`, `Incompatible student_id` for `1099`, and `Missing student_id` for the blank row. Recoverable problems (missing major, missing GPA/attendance, exact duplicates, whitespace) are repaired before the final split, so the rejected file contains exactly the 6 unrecoverable records, and the rejected count appears in the run metrics.

### 8. Why should the extraction layer be separated from the transformation layer?

Because they change for different reasons and must stay independently testable and reusable. In this project each source module only extracts — the ownership rules even forbid cleaning logic inside source modules — while cleaning, imputation, and derived columns live in the transformation layer. That separation is what allowed all three sources to implement one contract (`BaseSource.extract()`), let the transformation context (raw-API medians) change without touching a single source file, and lets tests exercise extraction error handling (timeouts, invalid JSON, locked databases) without any transformation logic involved. `main.py` composes the stages, so the order can be rearranged in one place.

### 9. Why is data validation an essential part of data engineering?

Because downstream consumers assume the data is trustworthy, and validation is what makes that true instead of assumed. The canonical dataset deliberately contains age `15`, GPA `4.5`, attendance `105`, and score `105` — none of which would crash a naive pipeline, but all of which would silently corrupt any average, model, or report built on them. Validation converts those silent corruptions into explicit, reasoned rejections, protects the shared `student_id` join key (missing or incompatible IDs), and makes quality measurable: the pipeline reports valid versus rejected counts on every run instead of hoping the output is correct.

### 10. How can the pipeline be developed to run periodically and automatically?

The structure is already ready for it: `main(config_path=...)` is a single entry point, every path comes from configuration, and the run is idempotent. The remaining step is operational: schedule `python main.py` with cron, GitHub Actions, or Windows Task Scheduler, and monitor `logs/pipeline.log` plus the exit code for failures. Incremental processing is what makes frequent runs practical — the saved state means each scheduled run only reprocesses new or changed students instead of the whole dataset. A production version would add failure alerting and timestamped output snapshots.

### 11. How can the pipeline handle millions of records?

The current implementation is intentionally simple — pandas DataFrames in memory — which is right for this dataset but would not scale as-is. The scaling path keeps the same stages and changes the engines: extract in chunks or push the heavy JOIN down to the database in SQL; move the data to columnar/partitioned storage such as Parquet; replace in-memory pandas with an out-of-core or distributed engine (DuckDB, Polars, or Spark) that streams the validation and cleaning steps; and rely on the already-implemented incremental processing so each run touches only changed records. Validation rules themselves stay identical — they become predicates that run inside the scalable engine.

### 12. What is the difference between batch processing and streaming processing?

Batch processing runs over a finite, complete dataset and produces its output once per run — exactly what this pipeline does: each execution reads the full sources, compares against the saved state, and produces a new snapshot of `final_dataset.csv`. Streaming processing consumes continuous, unbounded events and updates results continuously with low latency — there is no "run finished", and the same quality rules must be applied record-by-record as events arrive. Batch is the right model when correctness and simplicity matter more than freshness (reports, training datasets like ours); streaming fits live dashboards, alerts, and real-time features.
