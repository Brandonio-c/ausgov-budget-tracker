# Dashboard defect baseline — 20260803T193102Z

Base URL: `http://127.0.0.1:8000`

Total nodes visited across 3 paths: 15559

Nodes with a suspected defect: **13634**

## Defect class counts

- `cross_government_leak`: 12098
- `cross_year_silent_mismatch`: 11769
- `label_quality_header_or_financial_statement_line`: 3698
- `label_quality_concatenated_numeric_row`: 1677
- `additive_over_100pct`: 1015
- `cross_jurisdiction_leak`: 877

## Sample defect rows

- `federal_actuals_2024_25` fact_id=258429 (federal/Commonwealth) label="Assistance to the States for Healthcare Services" -> cross_year_silent_mismatch;additive_over_100pct:112.27%
- `federal_actuals_2024_25` fact_id=334638 (federal/Commonwealth) label="Aged Care (Accommodation Payment Security) Act 2006 - - - - - Total for Program" -> cross_year_silent_mismatch;additive_over_100pct:132.44%
- `federal_actuals_2024_25` fact_id=335111 (federal/Commonwealth) label="Aged Care (Accommodation Payment Security) Act 2006 2,180 - - - - Total for Program" -> cross_year_silent_mismatch;additive_over_100pct:103.40%
- `federal_actuals_2024_25` fact_id=334659 (federal/Commonwealth) label="Aged Care Act 1997 - residential and home care 11,496,300 40,039 10,010 - - Aged Care Act 2024 - Assistive Technology an" -> cross_year_silent_mismatch;label_quality_concatenated_numeric_row
- `federal_actuals_2024_25` fact_id=334660 (federal/Commonwealth) label="Aged Care Act 2024 - Residential Care Subsidies" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334661 (federal/Commonwealth) label="Aged Care Act 2024 - Specialist Aged Care Programs" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334662 (federal/Commonwealth) label="Aged Care Act 2024 - Support at Home" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334663 (federal/Commonwealth) label="Special account expenses SOETM Special Account 2021 Special account to support the National Disability Data Asset 9,729" -> cross_year_silent_mismatch;label_quality_header_or_financial_statement_line
- `federal_actuals_2024_25` fact_id=258154 (federal/Commonwealth) label="Dental services" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258149 (federal/Commonwealth) label="General medical consultations and services" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258169 (federal/Commonwealth) label="Immunisation" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258139 (federal/Commonwealth) label="Medical benefits" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=333417 (federal/Commonwealth) label="Medical Benefits" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258159 (federal/Commonwealth) label="Other" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258164 (federal/Commonwealth) label="Pharmaceutical benefits, services and supply" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258144 (federal/Commonwealth) label="Private health insurance" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258174 (federal/Commonwealth) label="Veterans' pharmaceutical benefits" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258194 (federal/Commonwealth) label="Dental services" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258189 (federal/Commonwealth) label="General medical consultations and services" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258209 (federal/Commonwealth) label="Immunisation" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258179 (federal/Commonwealth) label="Medical benefits" -> cross_year_silent_mismatch;additive_over_100pct:164.12%
- `federal_actuals_2024_25` fact_id=258199 (federal/Commonwealth) label="Other" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258204 (federal/Commonwealth) label="Pharmaceutical benefits, services and supply" -> cross_year_silent_mismatch;additive_over_100pct:103.33%
- `federal_actuals_2024_25` fact_id=258184 (federal/Commonwealth) label="Private health insurance" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258214 (federal/Commonwealth) label="Veterans' pharmaceutical benefits" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=258319 (federal/Commonwealth) label="Defence" -> cross_year_silent_mismatch;additive_over_100pct:110.61%
- `federal_actuals_2024_25` fact_id=334708 (federal/Commonwealth) label="Capability Acquisition Program" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334709 (federal/Commonwealth) label="Capability Sustainment Program" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334189 (federal/Commonwealth) label="Operating" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=334191 (federal/Commonwealth) label="Operations" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=333213 (federal/Commonwealth) label="Aggregate" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=333410 (federal/Commonwealth) label="Army History Research Grants Scheme" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331792 (federal/Commonwealth) label="ALFATRON PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331789 (federal/Commonwealth) label="AUSTRALIAN REMOTE OPERATIONS FOR SPACE AND EARTH LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331795 (federal/Commonwealth) label="CHEMRING AUSTRALIA PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331794 (federal/Commonwealth) label="FERRA ENGINEERING PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331787 (federal/Commonwealth) label="FLEET SPACE TECHNOLOGIES PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331788 (federal/Commonwealth) label="GREENBEAM SOFTWARE PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331793 (federal/Commonwealth) label="NU METRIC MANUFACTURING PTY LTD" -> cross_year_silent_mismatch
- `federal_actuals_2024_25` fact_id=331796 (federal/Commonwealth) label="Other recipients (87)" -> cross_year_silent_mismatch
