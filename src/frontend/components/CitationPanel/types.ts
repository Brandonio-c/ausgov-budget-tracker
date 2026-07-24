export type Citation = {
  fact_id: number;
  fact_key: string;
  landing_url: string;
  original_resource_url: string;
  cached_copy_url: string;
  locator: string;
  sha256?: string | null;
  retrieved_at?: string | null;
  amount_aud?: number | null;
  financial_year?: string;
  measure_type?: string;
};
