# Data dictionary

Status key: **UNVERIFIED** means the field name is provisional and has not been checked against the FDIC data dictionary. Nothing may be used in a ratio until it reads **VERIFIED**.

Field names in the table below are present in the live API response (the Week 1 load read them). Their meaning and units are still to be checked against the FDIC data dictionary, so they stay UNVERIFIED. Fill in the "Verified by and date" column after you check each field yourself at https://banks.data.fdic.gov (BankFind Suite, data dictionary).

## FDIC institutions (`fdic_institutions`, staged as `stg_institutions`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | institutions.cert | FDIC certificate number, the bank's permanent ID | integer | UNVERIFIED | |
| NAME | institutions.bank_name | Institution name | text | UNVERIFIED | |
| STALP | institutions.state | State abbreviation of the main office | text | UNVERIFIED | |
| ACTIVE | institutions.active | 1 if the institution is still active | flag | UNVERIFIED | |

## FDIC financials (`fdic_financials`, staged as `stg_financials`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | bank_financials.cert | Bank ID, joins to institutions and failures | integer | UNVERIFIED | |
| REPDTE | bank_financials.report_date | Report date, expected format YYYYMMDD | date text | UNVERIFIED | |
| ASSET | bank_financials.total_assets | Total assets | USD thousands (confirm) | UNVERIFIED | |
| EQTOT | bank_financials.total_equity | Total equity capital | USD thousands (confirm) | UNVERIFIED | |
| LNLSNET | bank_financials.net_loans | Net loans and leases | USD thousands (confirm) | UNVERIFIED | |
| DEP | bank_financials.total_deposits | Total deposits | USD thousands (confirm) | UNVERIFIED | |
| NETINC | bank_financials.net_income | Net income | USD thousands (confirm) | UNVERIFIED | |

## FDIC failures (`fdic_failures`, staged as `stg_failures`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | bank_failures.cert | Bank ID of the failed institution. Empty for about 488 pre-insurance failures (1934 onward), so the column is nullable and the table has no primary key | integer, nullable | UNVERIFIED | |
| NAME | bank_failures.bank_name | Name at failure | text | UNVERIFIED | |
| FAILDATE | bank_failures.fail_date | Date of failure. The live API returns M/D/YYYY, which 02_load_fdic.sql parses. ISO YYYY-MM-DD is also accepted. Anything else fails the load | date | UNVERIFIED | |

## SEC company facts (`sec_companyfacts_cik*.json`, loaded to `sec_facts`)

Source fields are the standard EDGAR companyfacts keys: taxonomy, concept (XBRL tag), unit, end, val, fy, fp, form, filed, accn. The code flattens these keys in `SecClient.flatten_companyfacts`, and the tests use a synthetic payload. Status: **UNVERIFIED** against a live EDGAR file. Confirm the structure and each concept name against a real company file before using them in Module F.
