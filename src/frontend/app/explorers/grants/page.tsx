import { ExplorerShell } from "@/components/ExplorerShell";

// Migrated onto the generic, registry-driven shell (item 6.3). The
// "never additive to expenditure" disclosure now comes from the
// "grants" family's registry entry, not bespoke page copy.
export default function GrantsExplorerPage() {
  return <ExplorerShell familyId="grants" />;
}
