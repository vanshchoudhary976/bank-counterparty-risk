# Data dictionary

Status key: **UNVERIFIED** means the field name is provisional and has not been checked against the FDIC data dictionary. Nothing may be used in a ratio until it reads **VERIFIED**.

Field names in the table below are present in the live API response (the Week 1 load read them). Their meaning and units are still to be checked against the FDIC data dictionary, so they stay UNVERIFIED. Fill in the "Verified by and date" column after you check each field yourself at https://banks.data.fdic.gov (BankFind Suite, data dictionary).

## Status summary (20 Nov 2026)

- Meaning checked in the FDIC RIS dictionary: ASSET, EQTOT, LNLSNET, DEP, NETINC.
- Units (thousands of dollars) confirmed on the Call Report pages ("Dollar amounts in thousands") for JPMorgan Chase Bank, N.A. (cert 628, 30 Jun 2026), Silicon Valley Bank (cert 24735, 31 Dec 2022), Goldman Sachs Bank USA (cert 33124, 30 Jun 2026) and Vision Bank (cert 4029, 30 Jun 2026).
- NETINC period confirmed as calendar year-to-date (Call Report Schedule RI heading). A June figure covers six months; ROA is annualised by 12 / months.
- Hand-checks against Call Reports, 20 Nov 2026: total assets, total equity, net loans, total deposits and net income matched the warehouse for all four banks.
- VERIFIED from the FDIC Institution API definitions: CERT, NAME, STALP, ACTIVE (read 20 Nov 2026).
- REPDTE and FAILDATE formats confirmed from raw samples (YYYYMMDD and M/D/YYYY). The FDIC definition for FAILDATE says date-time, which the live data does not match; the loader follows the live data.
- NETINCA is defined as annualised net income, which confirms that NETINC is the unannualised figure.
- The Institution definitions also confirm DEP covers domestic and foreign-office deposits, which matches the warehouse.
- Week 2 ratios use only the five checked fields.

## FDIC institutions (`fdic_institutions`, staged as `stg_institutions`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | institutions.cert | FDIC certificate number. FDIC definition: "A unique NUMBER assigned by the FDIC used to identify institutions and for the issuance of insurance certificates" | integer | VERIFIED | Institution API definitions (api.fdic.gov/banks/docs), read 20 Nov 2026 (VC) |
| NAME | institutions.bank_name | Institution name. FDIC definition: "The legal title or name of the institution" | text | VERIFIED | Institution API definitions, read 20 Nov 2026 (VC) |
| STALP | institutions.state | State abbreviation of the location of the institution's main office | text | VERIFIED | Institution API definitions, read 20 Nov 2026 (VC) |
| ACTIVE | institutions.active | FDIC definition: 1 = currently open and insured by the FDIC, 0 = closed or not insured. Stored as a boolean in the warehouse (TRUE = open), so 1 and TRUE mean the same thing | flag (number in API, boolean in warehouse) | VERIFIED | Institution API definitions, read 20 Nov 2026 (VC) |

## FDIC financials (`fdic_financials`, staged as `stg_financials`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | bank_financials.cert | FDIC certificate number, joins to institutions and failures. FDIC definition: "The certificate number assigned by the FDIC used to identify institutions" | integer | VERIFIED | Financial API definitions, read 20 Nov 2026 (VC) |
| REPDTE | bank_financials.report_date | Report date: "The last day of the financial reporting period selected". Live format is YYYYMMDD (raw sample, 20 Nov 2026: "REPDTE":"19840331"); the loader converts it to a date | date | VERIFIED | Financial API definitions and raw sample, 20 Nov 2026 (VC) |
| ASSET | bank_financials.total_assets | TOTAL ASSETS (RIS dictionary, balance sheet, FRB RCFD2170/RCON2170) | USD thousands (CONFIRMED on Call Report) | MEANING CHECKED; units CONFIRMED | Meaning checked against FDIC RIS dictionary, 20 Nov 2026 (initials VC). Units confirmed; Schedule RC item 12 matched for cert 628, 24735, 33124, 4029 |
| EQTOT | bank_financials.total_equity | TOTAL EQUITY CAPITAL (RIS dictionary, balance sheet, FRB RCFDG105/RCONG105) | USD thousands (CONFIRMED on Call Report) | MEANING CHECKED; units CONFIRMED | Meaning checked against FDIC RIS dictionary, 20 Nov 2026 (VC). Schedule RC item 28 matched for cert 628, 24735, 33124 (cert 4029 checked via Schedule RI-A item 12, which must equal RC item 27.a) |
| LNLSNET | bank_financials.net_loans | LOANS AND LEASES-NET, the warehouse value equals Schedule RC item 4.a (held for sale) plus item 4.d (held for investment, net of allowance) (RIS dictionary, FRB RCFD2125/RCON2125) | USD thousands (CONFIRMED on Call Report) | MEANING CHECKED; units CONFIRMED | Meaning checked against FDIC RIS dictionary, 20 Nov 2026 (VC). Sum of items 4.a and 4.d matched for cert 628, 24735, 33124, 4029 |
| DEP | bank_financials.total_deposits | TOTAL DEPOSITS, both offices: domestic offices (Call Report RCON2200) plus foreign offices, Edge/Agreement subsidiaries and IBFs (RCFN2200). The FDIC RIS code for the combined figure is to be confirmed; the warehouse value equals RCON2200 + RCFN2200 for the banks checked | USD thousands (CONFIRMED on Call Report) | MEANING CHECKED; units CONFIRMED | Meaning checked against FDIC RIS dictionary, 20 Nov 2026 (VC). Sum checked against Call Reports for cert 628, 24735, 33124, 4029 |
| NETINC | bank_financials.net_income | NET INCOME ATTRIBUTABLE TO BANK (Call Report Schedule RI, item 14, RIAD4340). Calendar year-to-date: a June report covers six months, a December report twelve | USD thousands (CONFIRMED on Call Report) | MEANING CHECKED; units and period CONFIRMED | Period confirmed from the Schedule RI heading ("calendar year-to-date basis"), 20 Nov 2026 (VC). Item 14 checked against Call Reports for cert 628, 24735, 33124, 4029 |

## FDIC failures (`fdic_failures`, staged as `stg_failures`)

| API field | Typed column | Meaning | Units | Status | Verified by and date |
|---|---|---|---|---|---|
| CERT | bank_failures.cert | FDIC certificate number of the failed institution. FDIC definition: "The certificate number assigned by the FDIC used to identify institutions". Empty for about 488 pre-insurance failures (1934 onward), so the column is nullable and the table has no primary key | integer, nullable | VERIFIED (meaning) | Failure API definitions, read 20 Nov 2026 (VC). The definition does not mention empty values; the 488 empty CERTs were observed in the load |
| NAME | bank_failures.bank_name | Name of the failed institution. FDIC definition: "This is the legal name of the institution" | text | VERIFIED | Failure API definitions, read 20 Nov 2026 (VC) |
| FAILDATE | bank_failures.fail_date | FDIC definition ("Effective Date"): "The date that the failed / assisted institution ceased to exist as a privately held going concern". The live API returns M/D/YYYY (raw sample, 20 Nov 2026: "FAILDATE":"5/28/1934"), which 02_load_fdic.sql parses. The FDIC definition labels it date-time, which does not match the live data; the loader follows the live data. ISO YYYY-MM-DD is also accepted. Anything else fails the load | date | VERIFIED | Failure API definitions and raw sample, 20 Nov 2026 (VC). Definition label (date-time) differs from the live format (M/D/YYYY); the live format is what the loader reads |

## SEC company facts (`sec_companyfacts_cik*.json`, loaded to `sec_facts`)

Source fields are the standard EDGAR companyfacts keys: taxonomy, concept (XBRL tag), unit, end, val, fy, fp, form, filed, accn. The code flattens these keys in `SecClient.flatten_companyfacts`, and the tests use a synthetic payload. Status: **UNVERIFIED** against a live EDGAR file. Confirm the structure and each concept name against a real company file before using them in Module F.
