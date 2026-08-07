# Older Queensland RSF corpus inventory

Generated: 2026-08-07T15:09:11Z. Full per-file fields and hashes are in
the companion CSV.

All 16 editions are PDFs with a real six-numeric-column summary table:
General Government Sector, Public Non-financial Corporations Sector, and
Non-financial Public Sector, each with estimated-actual and outcome/actual
columns. Only the first GGS pair is published. Units are `$ million` and
are converted once to AUD.

Three bounded shapes were confirmed:

- 2002-03 to 2010-11: revenue, expenses and net operating balance plus a
  changing mix of fiscal balance/net lending-borrowing, cash balance,
  capital, net worth, net debt, net borrowing and borrowing.
- 2011-12 to 2012-13: the stable six-row modern core begins (revenue,
  expenses, net operating balance, capital purchases, fiscal balance,
  borrowing).
- 2013-14 to 2017-18: the same six-row core, with the table moving from
  page 9 to pages 12/8 in the last two editions.

Risks and controls: 2002-03 to 2004-05 contain split-thousands extraction
artefacts, so layout mode is edition-bounded to those PDFs. Later ordinary
text extraction is cleaner. Four nearby narrative/heading lines in the
older cluster resemble selected labels but do not have the table's numeric
shape; they are quarantined. The 2017-18 `revised` file is the only acquired
RSF edition for that year and therefore has explicit precedence. No older
facts or quarantines existed before this load; expected publishable output
is 234 facts (117 source rows x two vintages) and four extractor quarantine
records.
