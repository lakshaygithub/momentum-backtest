# Results

Test period: Jan 2010 to Oct 2026 (202 months), monthly rebalancing, 10 bps cost per unit of turnover. Total returns (dividends included).

| Strategy | CAGR | Volatility | Sharpe | Max drawdown | Worst month |
| --- | ---: | ---: | ---: | ---: | ---: |
| Momentum, walk-forward (honest) | 5.3% | 6.5% | 0.82 | -8.3% | -6.5% |
| Momentum, fixed 12-month | 5.6% | 7.0% | 0.81 | -11.2% | -6.6% |
| Momentum, best lookback in hindsight (3m) | 5.0% | 6.2% | 0.83 | -10.2% | -6.6% |
| Equal weight, same 4 ETFs | 8.2% | 9.2% | 0.91 | -19.1% | -6.6% |
| Equal weight at the same risk (71% invested) | 5.8% | 6.5% | 0.91 | -13.8% | -4.7% |
| SPY buy and hold | 14.0% | 14.3% | 0.99 | -23.9% | -12.5% |

Walk-forward turnover: 1.93x the portfolio per year.

## Lookback chosen each year (walk-forward)

| Year | Lookback (months) | Training months |
| --- | ---: | ---: |
| 2010 | 6 | 49 |
| 2011 | 6 | 61 |
| 2012 | 6 | 73 |
| 2013 | 6 | 85 |
| 2014 | 6 | 97 |
| 2015 | 6 | 109 |
| 2016 | 6 | 121 |
| 2017 | 6 | 133 |
| 2018 | 6 | 145 |
| 2019 | 6 | 157 |
| 2020 | 6 | 169 |
| 2021 | 6 | 181 |
| 2022 | 6 | 193 |
| 2023 | 6 | 205 |
| 2024 | 6 | 217 |
| 2025 | 6 | 229 |
| 2026 | 6 | 241 |

## Sensitivity to trading costs (walk-forward)

| Cost (bps) | CAGR | Sharpe | Max drawdown |
| ---: | ---: | ---: | ---: |
| 0 | 5.4% | 0.85 | -8.0% |
| 10 | 5.3% | 0.82 | -8.3% |
| 25 | 4.9% | 0.78 | -8.8% |
| 50 | 4.1% | 0.65 | -9.6% |

## Is the Sharpe difference real? (block bootstrap, 12-month blocks, 5,000 samples)

| Walk-forward vs | Share of samples it wins | 90% range of Sharpe difference |
| --- | ---: | ---: |
| Equal weight | 23.7% | -0.30 to +0.12 |
| SPY | 15.0% | -0.48 to +0.11 |
