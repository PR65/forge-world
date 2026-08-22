import type { ObjectiveConfig, PackDetail, SolveResponse } from "./types";

export async function fetchPacks(): Promise<{ pack_id: string; title: string; variants: string[] }[]> {
  const r = await fetch("/api/packs");
  if (!r.ok) throw new Error(`packs: ${r.status}`);
  return r.json();
}

export async function fetchPackDetail(id: string): Promise<PackDetail> {
  const r = await fetch(`/api/packs/${id}`);
  if (!r.ok) throw new Error(`pack: ${r.status}`);
  return r.json();
}

export async function solveObjective(cfg: ObjectiveConfig): Promise<SolveResponse> {
  const body = {
    pack_id: cfg.packId,
    variant_id: cfg.variantId,
    annual_units: cfg.annualUnits,
    geography: cfg.geography,
    deadline_year: cfg.deadlineYear,
    min_dva: cfg.minDva,
    budget_usd: cfg.budgetUsd,
    funded_projects: cfg.fundedProjects,
    shocks: cfg.shocks,
    analyst_capacity_assumptions: Object.fromEntries(
      Object.entries(cfg.assumptions).map(([k, v]) => [k, v])
    ),
    include_deep: true,
  };
  const r = await fetch("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`solve failed: ${r.status} ${t.slice(0, 200)}`);
  }
  return r.json();
}
