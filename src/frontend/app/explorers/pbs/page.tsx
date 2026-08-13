import { ExplorerShell } from "@/components/ExplorerShell";

// Migrated onto the generic, registry-driven shell (item 6.3). The
// "pbs" family's registry entry (source_key: federal_pbs_programs_all)
// supplies the quarantine-safe scoping and the portfolio-level,
// not-additive-to-whole-of-government disclosure that used to be
// bespoke page copy.
export default function PbsExplorerPage() {
  return <ExplorerShell familyId="pbs" />;
}
