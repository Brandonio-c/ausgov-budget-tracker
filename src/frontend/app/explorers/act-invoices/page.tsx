import { ExplorerShell } from "@/components/ExplorerShell";

// Migrated onto the generic, registry-driven shell (item 6.3). The
// cash-vs-accrual disclosure now comes from the "act_invoices" family's
// registry entry, not bespoke page copy.
export default function ActInvoicesExplorerPage() {
  return <ExplorerShell familyId="act_invoices" />;
}
