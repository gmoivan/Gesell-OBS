# Gesell Skill: obs_recording_hash_sha256

## Purpose
Generate a SHA-256 cryptographic hash for each newly created OBS recording file.

Designed for:
- forensic integrity workflows
- evidentiary chain-of-custody
- compliance logging
- automated archival verification

## Execution Model
External Python process that:
1. Monitors a recording directory
2. Detects new files
3. Waits until file write completes
4. Computes SHA-256 digest
5. Writes a .sha256 sidecar file and/or logs result

## Inputs
- recording_directory (path)
- poll_interval_seconds
- optional log_file_path
- optional create_sidecar_file (bool)

## Outputs
- SHA-256 hex digest
- Optional: <filename>.sha256 file
- Optional: append-only CSV log

## Standard
- SHA-256 (hashlib)
