import Link from "next/link";
import { ExplorerShell } from "@/components/ExplorerShell";
import DebtNav from "@/components/DebtNav";

// Migrated onto the generic, registry-driven shell (item 6.3). The
// jurisdiction-mix disclosure and source_breakdown that used to be
// bespoke to this page now come from the shell reading the "contracts"
// family's registry entry (config/explorers/families.yaml) generically -
// see ops/reports/contracts-jurisdiction-disclosure-20260812T061849Z.md
// for why that disclosure exists. DebtNav and the GFS liabilities
// cross-link are contracts-specific supplementary navigation the generic
// shell has no reason to know about, so they're passed in as extraContent
// rather than hard-coded into the shell itself.
export default function ContractsExplorerPage() {
  return (
    <ExplorerShell
      familyId="contracts"
      extraContent={
        <>
          <DebtNav />
          <p className="mt-2 text-sm opacity-80">
            For GFS liability stocks use{" "}
            <Link className="underline" href="/explorers/gfs?view=liabilities">
              GFS explorer → Liabilities
            </Link>{" "}
            or the Debt mode on Breakdown / Combined / Timeline.
          </p>
        </>
      }
    />
  );
}
