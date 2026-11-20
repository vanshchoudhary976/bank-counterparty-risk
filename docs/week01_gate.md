# Week 1 gate

The blueprint says: do not start Week 2 until this gate is met.

**Gate to pass:** row counts reconcile to the source, and the failures list loads correctly.

## What you run

- [ ] `make test` passes on your machine.
- [ ] `export SEC_USER_AGENT="Your Name you@example.com"` (use your real email).
- [ ] `make fdic` completes and writes three files to `data/raw/fdic/`.
- [ ] `make sec CIKS="<cik>"` completes for the CIK numbers you choose.
- [ ] `make load` prints every check as PASS and ends with "N of N checks passed".
- [ ] Compare the `total` field in each raw FDIC file (`data/raw/fdic/fdic_*.json`) with the `source_total` and `rows_staged` columns in `load_log`. They must match.
- [ ] Open the three 2023 failures in `bank_failures` and confirm the names and dates against the FDIC failures list.

## Before Week 2

- [ ] Every field in `docs/data_dictionary.md` is marked VERIFIED with your initials and the date, or the unverified field is removed from `config.py`.
- [ ] You can explain in your own words what `TRY_CAST`, the staging layer and the checksum each protect against.

Attach the `make load` output and the `load_log` table to the build chat so the gate can be reviewed.
