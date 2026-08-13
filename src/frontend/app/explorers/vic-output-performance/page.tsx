import { ExplorerShell } from "@/components/ExplorerShell";

// Migrated onto the generic, registry-driven shell (item 6.3). The
// "vic_output_performance" family's registry entry supplies the
// disclosure that these are output total-cost performance measures,
// not part of the additive expenditure tree.
export default function VicOutputPerformanceExplorerPage() {
  return <ExplorerShell familyId="vic_output_performance" />;
}
