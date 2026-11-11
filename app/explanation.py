"""Plain-language explanation of optimization results."""


def recommendation_explanation(
    recommended: dict, ranked_routes: list[dict], pareto_ids: set[str]
) -> str:
    """Explain the winning route using the user's selected priorities and runner-up."""
    runner_up = next(route for route in ranked_routes if route["route_id"] != recommended["route_id"])
    advantages = []
    if recommended["cost_inr"] < runner_up["cost_inr"]:
        advantages.append(f"INR {runner_up['cost_inr'] - recommended['cost_inr']:,.0f} lower cost")
    if recommended["transit_days"] < runner_up["transit_days"]:
        advantages.append(f"{runner_up['transit_days'] - recommended['transit_days']:.1f} fewer transit days")
    if recommended["risk_score"] < runner_up["risk_score"]:
        advantages.append(f"{runner_up['risk_score'] - recommended['risk_score']:.2f} lower combined risk")
    tradeoff = "; ".join(advantages) if advantages else "the best overall balance under the selected weights"
    pareto_note = " It is also Pareto-optimal." if recommended["route_id"] in pareto_ids else ""
    return (
        f"Route {recommended['route_id']} is recommended because it has the highest weighted score "
        f"({recommended['weighted_score']:.4f}). Compared with runner-up {runner_up['route_id']}, "
        f"it provides {tradeoff}. Its estimated cost is INR {recommended['cost_inr']:,.0f}, "
        f"transit time is {recommended['transit_days']} days, and combined risk is "
        f"{recommended['risk_score']:.2f}." + pareto_note
    )


def pareto_explanation(routes: list[dict]) -> str:
    if len(routes) == 1:
        return f"{routes[0]['route_id']} dominates every other available route."
    return "Pareto routes are alternatives where improving cost, time, or risk requires a trade-off in at least one other objective."
