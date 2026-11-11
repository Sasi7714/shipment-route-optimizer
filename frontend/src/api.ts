export type Shipment = { shipment_id: string; origin: string; destination: string };

export type Route = {
  route_id: string;
  intermediate_hubs: string;
  cost_inr: number;
  transit_days: number;
  delay_probability: number;
  congestion_risk: number;
  geopolitical_risk: number;
  risk_score: number;
  weighted_score: number;
  rank: number;
  pareto_optimal?: boolean;
};

export type OptimizationResult = {
  shipment: Shipment;
  weights_used: { cost: number; time: number; risk: number };
  routes_ranked: Route[];
  pareto_optimal_routes?: Route[];
  recommended_route: Route;
  explanation: string;
  pareto_tradeoff_explanation?: string;
};

type ApiError = { error?: { message?: string } };

const baseUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiError;
    throw new Error(body.error?.message || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  shipments: () => request<Shipment[]>("/shipments"),
  optimize: (shipmentId: string, weights: { cost: number; time: number; risk: number }) =>
    request<OptimizationResult>(`/optimize/${encodeURIComponent(shipmentId)}`, {
      method: "POST",
      body: JSON.stringify({ cost_weight: weights.cost, time_weight: weights.time, risk_weight: weights.risk }),
    }),
};
