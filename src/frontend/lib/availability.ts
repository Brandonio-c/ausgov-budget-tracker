export type AvailabilityFact = { financial_year: string; estimate_status?: string };

/** Format the exact year/status coverage returned by a selected API series. */
export function formatApiAvailability(facts: AvailabilityFact[]): string {
  if (facts.length === 0) return "API availability: no facts returned for this measure";
  const years = [...new Set(facts.map((fact) => fact.financial_year))].sort((a, b) => {
    const start = (year: string) => Number.parseInt(year.slice(0, 4), 10) || 0;
    return start(a) - start(b);
  });
  const yearRange =
    years.length === 1 ? `FY${years[0]}` : `FY${years[0]} to FY${years[years.length - 1]}`;
  const statuses = [...new Set(facts.map((fact) => fact.estimate_status).filter(Boolean))]
    .map((status) => status?.replaceAll("_", " "))
    .join(", ");
  return `API availability: ${yearRange}${statuses ? `; ${statuses}` : ""}`;
}
