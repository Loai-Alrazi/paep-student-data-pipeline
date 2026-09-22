# Project Overview

PAEP Student Data Pipeline is a group training project for the PAEP Data Engineering course. The team will build a multi-source ETL and data integration pipeline for student data while practicing source ownership, collaboration through GitHub, code review, and automated testing.

# Project Goal

The pipeline will collect student data from:

- CSV
- REST API
- SQLite

The planned data flow is:

Extract → Source Validation → Clean → Integrate → Transform → Final Validation → Load

The completed pipeline will produce:

- Processed dataset: `data/processed/final_dataset.csv`
- Rejected records: `data/rejected/rejected_records.csv`
- Pipeline logs: `logs/pipeline.log`

# Team Members and Responsibilities

## لؤي

### Ownership

- `app/utils/logger.py`
- `app/output/csv_writer.py`
- `app/transformation/integration.py`
- `main.py`
- Integration, end-to-end, and output tests when created

### Responsibilities

- Repository and GitHub Project coordination
- Logging
- Output writing
- Data integration
- End-to-end pipeline orchestration
- Final README coordination
- Integration/pipeline testing

## عمران

### Ownership

- `app/sources/csv_source.py`
- `app/transformation/cleaner.py`
- `data/raw/students.csv` when created
- CSV and cleaning tests

### Responsibilities

- CSV extraction
- CSV input handling
- Data cleaning
- Duplicate handling
- Text normalization
- Extra spaces/case normalization

## زياد

### Ownership

- `app/sources/api_source.py`
- `app/transformation/transformer.py`
- `mock_api/`
- API and transformation tests

### Responsibilities

- REST API extraction
- Mock API when needed
- API error handling
- Data transformation
- Data types
- Missing-value transformation strategy
- Derived columns

## العنسي

### Ownership

- `app/sources/database_source.py`
- `app/validation/quality.py`
- `database/`
- SQLite and validation tests

### Responsibilities

- SQLite database setup
- SQL extraction
- Source validation
- Final validation
- Quality rules
- Rejected-record classification and error reasons

# Data Contract

Each source module must return structured data that can be integrated using the shared `student_id` key.

## CSV

- `student_id`
- `student_name`
- `age`
- `major`
- `city`

## REST API

- `student_id`
- `gpa`
- `attendance`
- `status`

## SQLite

- `student_id`
- `course_name`
- `credit_hours`
- `semester`
- `score`

## Shared Key

`student_id`

# Ownership Boundaries

- Each team member works primarily on the files they own.
- A member should not modify another member's owned file within their issue unless there is a clear need and agreement.
- Cleaning logic does not belong in source modules.
- Validation logic does not belong in `integration.py`.
- CSV writing does not belong in `quality.py`.
- `main.py` is responsible for orchestration, not the implementation details of each stage.
- Keep every module focused on a single responsibility.

# Branch Strategy

`main` is the stable branch. Direct development on `main` is not allowed after the workflow setup is complete.

Every issue must use a separate branch created from the latest `main`. Branch names follow these patterns:

- `feature/<name>`
- `fix/<name>`
- `test/<name>`
- `docs/<name>`
- `chore/<name>`

# GitHub Workflow

Issue → Assign owner → Todo → Update local `main` → Create branch → In Progress → Implement issue scope → Tests → Commit → Push → Pull Request → In Review → Teammate review → Changes if requested → Approval → Merge → Delete branch → Done

# Pull Request Rules

Every pull request must:

- Link to a clear issue.
- Stay limited to the issue scope.
- Contain no unrelated changes.
- Explain the summary.
- Explain the testing performed.
- Request the designated reviewer.
- Remain unmerged until reviewed.
- Be merged by someone other than its author.
- Delete its branch after merging when safe.

# Reviewer Rotation

- لؤي PR → عمران reviews, approves, and merges.
- عمران PR → زياد reviews, approves, and merges.
- زياد PR → العنسي reviews, approves, and merges.
- العنسي PR → لؤي reviews, approves, and merges.

If the primary reviewer is unavailable, a third team member may review and merge. A pull request author must never approve or merge their own work.

# Code Review Checklist

The reviewer verifies:

- Issue requirements fulfilled
- Scope respected
- No unrelated changes
- Ownership boundaries respected
- Readable code
- Sensible naming
- Expected error handling
- Appropriate tests
- Tests pass
- No secrets or machine-specific paths
- No unnecessary dependencies

# Commit Convention

Use Conventional Commits with these types:

- `feat:`
- `fix:`
- `test:`
- `docs:`
- `refactor:`
- `chore:`

Examples:

- `feat: add csv source extraction`
- `feat: add api student source`
- `feat: add sqlite extraction`
- `feat: add data cleaning rules`
- `feat: add data quality validation`
- `test: add csv source tests`
- `docs: document team workflow`
- `chore: configure project workflow`

# Testing Strategy

Each member is responsible for testing the part they own. Future tests should cover the core assignment requirements:

- CSV loading
- API extraction
- SQLite extraction
- Duplicate removal
- Missing-value handling
- Invalid-record rejection
- Source integration
- `final_dataset.csv` creation

These tests are part of later implementation work and are not included in the workflow setup.

# Error Handling

Expected errors must be handled explicitly. Avoid unnecessary catch-all exception handling that hides the original failure or makes diagnosis difficult.

The API source should later handle:

- Connection errors
- Timeouts
- HTTP errors
- Invalid JSON
- Empty responses

The CSV and SQLite sources must also handle the expected errors specific to their input and connection operations.

# Definition of Done

An issue becomes Done only when:

- Scope is complete.
- Required tests exist and pass.
- There are no unrelated changes.
- The branch is published.
- A pull request is open.
- Another team member has reviewed it.
- Review comments are resolved.
- The pull request is approved.
- The work is merged into `main`.
- The branch is deleted when safe.
- GitHub Project status is Done.

# GitHub Project Status Meaning

## Backlog

A planned task that is not ready for implementation.

## Todo

A task that is ready to start.

## In Progress

Active work has started on a branch.

## In Review

A pull request is open and under review.

## Done

The work has been approved and merged into `main`.

# Final Deliverables

The completed project will include:

- `final_dataset.csv`
- `rejected_records.csv`
- `pipeline.log`
- `README.md`
- Tests
- Source code
