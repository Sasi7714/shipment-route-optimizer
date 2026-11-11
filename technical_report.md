# Technical Report: Shipment Route Optimization System

## Problem and objective

Logistics operators often need to choose between lower shipping cost, faster arrival, and more reliable transport. This project implements a Python decision-support API that evaluates these competing objectives and recommends a shipment route in Indian Rupees (INR). The aim is not to replace operational planning: it is a transparent demonstration of weighted and multi-objective optimization.

## Dataset and architecture

The dataset is entirely simulated and must not be interpreted as real carrier data. It contains 20 Indian origin–destination shipments (SH001–SH020) and three realistic-looking road, rail/road, port, or air-oriented options per shipment. Each record has an origin, destination, intermediate hubs, INR cost, transit days, delay probability, congestion risk, and geopolitical risk. All risk fields are values from zero to one.

The application uses CSV/Pandas for initial data handling and SQLite/SQLAlchemy for persistence. On first startup, the dataset is loaded into SQLite. FastAPI exposes shipment and optimization endpoints. `scoring.py` owns numeric calculation, `optimizer.py` owns Pareto logic, and `explanation.py` produces a short human-readable decision rationale. This division keeps the system easy to test and extend.

## Weighted scoring method

First, a combined risk is calculated as `0.50 × delay probability + 0.30 × congestion risk + 0.20 × geopolitical risk`. Delay receives the largest weight because it directly affects delivery reliability. For every shipment, cost, transit days, and the combined risk are min–max normalized independently. They are inverted because lower is better:

`benefit score = 1 − (value − minimum) / (maximum − minimum)`.

When every option has the same value for a metric, all receive a score of one for that metric. The default overall score is `0.40 × cost benefit + 0.30 × time benefit + 0.30 × risk benefit`. The route with the highest result is recommended. API callers can submit alternative weights; the service normalizes them proportionally. For example, a cost-sensitive user may choose 0.70/0.15/0.15, while a time-sensitive user may increase time weight. This shows that an appropriate recommendation depends on business priorities.

## Pareto optimization and comparison

The second approach treats cost, transit time, and combined risk as separate objectives to minimize. A route is dominated if another route is no worse in every objective and better in at least one. Every non-dominated route forms the Pareto set. Unlike weighted scoring, Pareto optimization deliberately returns several options when none is universally best. A low-cost option can therefore coexist with a fast low-risk alternative, making the trade-off visible to a logistics operator.

The API includes the ordered weighted list, Pareto flags, Pareto-only list, default weights, and explanation in one response. A weighted winner is often Pareto-optimal, but this is not guaranteed for arbitrary priorities; that difference is useful information rather than an error.

## Results, limitations, and future work

For each shipment, the system provides an INR comparison, timing and risk metrics, a ranked recommendation, and alternative Pareto choices. Unit tests verify risk calculation, score ordering, changed-weight behavior, Pareto dominance, successful API output, and 404 handling for unknown shipment IDs.

The main limitation is simulated, static input. A production version should ingest live carrier quotes, GPS/traffic, weather, port congestion, capacity, and disruption data; estimate risk statistically; support constraints such as vehicle capacity or emissions; record decision history; and provide authentication, monitoring, migrations, and a user interface.
