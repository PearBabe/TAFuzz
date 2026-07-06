# MightyPPL Syntax Coverage Audit

This generated ledger maps the MightyPPL grammar surface to either hand-oracle runtime evidence, build/statistics-only evidence, or an explicit internal-form exclusion.
It is intended as the manual-review entry point for the claim that user-level MightyPPL syntax is covered without treating internal Count forms as ordinary MITL formulas.

## Coverage Counts

- `BUILD_STATS_ONLY`: 1
- `EXCLUDED_INTERNAL_FORM`: 8
- `VERIFIED_RUNTIME_FINITE_AND_INFINITE`: 36

## Family Counts

- `atom`: 4
- `boolean`: 5
- `formula`: 1
- `future_binary`: 4
- `future_unary`: 4
- `internal_count`: 8
- `interval`: 5
- `past_binary`: 4
- `past_unary`: 4
- `pnueli`: 4
- `regression_corpus`: 1
- `runtime_semantics`: 1

## Rows

| syntax_id | construct | status | evidence | review_action |
|---|---|---|---|---|
| `formula_atom` | `formula -> atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=6; finite=3; infinite=3 | Review matching semantic rows and prefix oracle rows. |
| `formula_not` | `! atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `formula_and` | `formula && formula` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `formula_or` | `formula \|\| formula` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `formula_iff` | `formula <-> formula` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `formula_implies` | `formula -> formula` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `atom_paren` | `( formula )` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=7; finite=3; infinite=4 | Review matching semantic rows and prefix oracle rows. |
| `atom_true` | `true` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `atom_false` | `false` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `atom_identifier` | `Idfr` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `interval_closed` | `[a,b]` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=10; finite=5; infinite=5 | Review matching semantic rows and prefix oracle rows. |
| `interval_left_open` | `(a,b]` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `interval_right_open` | `[a,b)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `interval_open` | `(a,b)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `interval_unbounded` | `[a,infty)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `future_F` | `F interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=4; finite=2; infinite=2 | Review matching semantic rows and prefix oracle rows. |
| `future_F_star` | `F* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `future_G` | `G interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=3; finite=1; infinite=2 | Review matching semantic rows and prefix oracle rows. |
| `future_G_star` | `G* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=3; finite=1; infinite=2 | Review matching semantic rows and prefix oracle rows. |
| `future_U` | `atom U interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=4; finite=2; infinite=2 | Review matching semantic rows and prefix oracle rows. |
| `future_U_star` | `atom U* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `future_R` | `atom R interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `future_R_star` | `atom R* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_O` | `O interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_O_star` | `O* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_H` | `H interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_H_star` | `H* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_S` | `atom S interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_S_star` | `atom S* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_T` | `atom T interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `past_T_star` | `atom T* interval? atom` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `pnueli_Fn` | `Fn interval (atom, atom, ...)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `pnueli_On` | `On interval (atom, atom, ...)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `pnueli_Gn` | `Gn interval (atom, atom, ...)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `pnueli_Hn` | `Hn interval (atom, atom, ...)` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=2; finite=1; infinite=1 | Review matching semantic rows and prefix oracle rows. |
| `word_modes` | `finite and infinite timed words` | `VERIFIED_RUNTIME_FINITE_AND_INFINITE` | verified_cases=70; finite=34; infinite=36 | Review matching semantic rows and prefix oracle rows. |
| `existing_mightyppl_testcases` | `tool/MightyPPL/testcases/**/*.mitl` | `BUILD_STATS_ONLY` | build_stats_cases=17 | Use this row only as construction/SAT/statistics evidence, not RV correctness evidence. |
| `internal_CFn` | `CFn` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_CFn_star` | `CFn*` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_COn` | `COn` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_COn_star` | `COn*` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_CGn` | `CGn` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_CGn_star` | `CGn*` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_CHn` | `CHn` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
| `internal_CHn_star` | `CHn*` | `EXCLUDED_INTERNAL_FORM` | exclusion_ledger_row=present | Do not create user-facing MITL runtime oracle formulas for this internal form. |
