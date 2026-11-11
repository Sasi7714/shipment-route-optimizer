import { useEffect, useMemo, useState } from "react";
import { api, type OptimizationResult, type Route, type Shipment } from "./api";

type Weights = { cost: number; time: number; risk: number };
const DEFAULT_WEIGHTS: Weights = { cost: 40, time: 30, risk: 30 };

const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const percent = (value: number) => `${Math.round(value * 100)}%`;

function Metric({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return <div className={`metric ${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}

function WeightControl({ label, value, onChange, color }: { label: string; value: number; onChange: (value: number) => void; color: string }) {
  return (
    <label className="weight-control">
      <span><i style={{ background: color }} />{label}<b>{value}%</b></span>
      <input type="range" min="0" max="100" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function RouteRow({ route, selected }: { route: Route; selected: boolean }) {
  return (
    <article className={`route-row ${selected ? "selected" : ""}`}>
      <div className="rank"><span>{route.rank}</span>{selected ? "Recommended" : route.pareto_optimal ? "Pareto option" : "Alternative"}</div>
      <div className="route-name"><strong>{route.route_id}</strong><span>{route.intermediate_hubs.split(";").join("  →  ")}</span></div>
      <Metric label="Cost" value={money.format(route.cost_inr)} />
      <Metric label="Transit" value={`${route.transit_days} days`} />
      <Metric label="Risk" value={percent(route.risk_score)} tone={route.risk_score < 0.2 ? "good" : "warning"} />
      <div className="score"><span>Fit score</span><strong>{Math.round(route.weighted_score * 100)}</strong><em>/100</em></div>
    </article>
  );
}

export default function App() {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [shipmentId, setShipmentId] = useState("");
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.shipments().then((items) => {
      setShipments(items);
      setShipmentId(items[0]?.shipment_id || "");
    }).catch((reason: Error) => setError(reason.message)).finally(() => setLoading(false));
  }, []);

  const totalWeight = useMemo(() => weights.cost + weights.time + weights.risk, [weights]);
  const selectedShipment = shipments.find((shipment) => shipment.shipment_id === shipmentId);
  const updateWeight = (key: keyof Weights, value: number) => setWeights((current) => ({ ...current, [key]: value }));

  async function optimize() {
    if (!shipmentId || totalWeight === 0) return;
    setOptimizing(true);
    setError("");
    try {
      setResult(await api.optimize(shipmentId, { cost: weights.cost / totalWeight, time: weights.time / totalWeight, risk: weights.risk / totalWeight }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to calculate a recommendation.");
    } finally {
      setOptimizing(false);
    }
  }

  return (
    <main>
      <header className="topbar"><a className="brand" href="/"><span>R</span>routewise</a><div className="live"><i /> Decision support system <b>•</b> Synthetic data</div></header>
      <section className="hero"><div><p className="eyebrow">MULTI-OBJECTIVE ROUTING</p><h1>Choose the route that<br /><em>fits the moment.</em></h1><p className="hero-copy">Balance price, speed, and operational risk with an explainable recommendation—not a black box.</p></div><div className="hero-stat"><span>AVAILABLE OPTIONS</span><strong>{result?.routes_ranked.length || "—"}</strong><small>per shipment</small></div></section>

      <section className="workspace">
        <aside className="control-panel">
          <div className="panel-heading"><p>01 / SHIPMENT</p><h2>Set the context</h2></div>
          <label className="select-label">Shipment
            <select value={shipmentId} disabled={loading} onChange={(event) => { setShipmentId(event.target.value); setResult(null); }}>
              {shipments.map((shipment) => <option value={shipment.shipment_id} key={shipment.shipment_id}>{shipment.shipment_id} · {shipment.origin} → {shipment.destination}</option>)}
            </select>
          </label>
          {selectedShipment && <div className="journey"><span>{selectedShipment.origin}</span><i>→</i><span>{selectedShipment.destination}</span></div>}
          <div className="panel-heading priorities"><p>02 / PRIORITIES</p><h2>What matters most?</h2><small>Weights are normalized automatically.</small></div>
          <WeightControl label="Cost efficiency" value={weights.cost} onChange={(value) => updateWeight("cost", value)} color="#45cfb0" />
          <WeightControl label="Transit speed" value={weights.time} onChange={(value) => updateWeight("time", value)} color="#84a6ff" />
          <WeightControl label="Reliability" value={weights.risk} onChange={(value) => updateWeight("risk", value)} color="#f6be62" />
          <div className={`weight-total ${totalWeight === 0 ? "invalid" : ""}`}>Total priority <b>{totalWeight}%</b></div>
          <button className="optimize-button" disabled={optimizing || loading || totalWeight === 0} onClick={optimize}>{optimizing ? "Calculating route…" : "Find best route  →"}</button>
        </aside>

        <section className="results-panel">
          {error && <div className="error"><strong>Could not complete request.</strong> {error}</div>}
          {!result && !loading && !error && <div className="empty"><div>↗</div><h2>Ready for a recommendation</h2><p>Select your priorities, then compare every available route in seconds.</p></div>}
          {loading && <div className="empty"><div className="spinner" /><h2>Loading shipments</h2></div>}
          {result && <>
            <div className="result-heading"><div><p className="eyebrow">RECOMMENDED FOR {result.shipment.shipment_id}</p><h2>{result.shipment.origin} <span>→</span> {result.shipment.destination}</h2></div><button className="reset" onClick={() => { setWeights(DEFAULT_WEIGHTS); setResult(null); }}>Reset view</button></div>
            <article className="recommendation"><div className="recommendation-tag">BEST FIT</div><div className="recommendation-main"><span>Route</span><h3>{result.recommended_route.route_id}</h3><p>{result.recommended_route.intermediate_hubs.split(";").join("  →  ")}</p></div><Metric label="Estimated cost" value={money.format(result.recommended_route.cost_inr)} /><Metric label="Transit time" value={`${result.recommended_route.transit_days} days`} /><Metric label="Combined risk" value={percent(result.recommended_route.risk_score)} tone="good" /></article>
            <div className="explanation"><span>✦</span><p>{result.explanation}</p></div>
            <div className="comparison-heading"><div><h3>Route comparison</h3><p>Ranked against your selected priorities</p></div><span className="legend"><i /> Pareto-optimal option</span></div>
            <div className="route-list">{result.routes_ranked.map((route) => <RouteRow key={route.route_id} route={route} selected={route.route_id === result.recommended_route.route_id} />)}</div>
            {result.pareto_tradeoff_explanation && <p className="pareto-note">{result.pareto_tradeoff_explanation}</p>}
          </>}
        </section>
      </section>
      <footer>ROUTEWISE / EXPLAINABLE LOGISTICS DECISION SUPPORT</footer>
    </main>
  );
}
