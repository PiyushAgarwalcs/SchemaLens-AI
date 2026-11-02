# SchemaLens AI — Auto-Generated Documentation

_Generated: 2026-07-08T11:18:08.549687+00:00_

## users

**Purpose:** This table records each system user. It tracks a unique internal node ID, a public user identifier, and the account scope (Margin, Spot, or Options).

**Columns:**
- `usersnode`: Internal numeric identifier for the user record.
- `userstamp`: External user code, shown with trailing spaces in the sample.
- `acctscope`: The type of account the user is associated with (e.g., Margin, Spot, Options).

**Relationships:** None (no foreign keys declared in this table).

**Business Value:** Allows the business to look up a user by code and see which account category they belong to, supporting user‑level reporting and segmentation.

**⚠️ Ambiguity Flags:**
- `usersnode`: It appears to be an internal surrogate key, but the sample does not explain whether it has meaning beyond uniqueness.
- `acctscope`: Values are Margin, Spot, and Options; it is unclear if these represent product types, permission levels, or something else.

## riskandmargin

**Purpose:** This table records risk and margin information linked to a specific order. It stores a JSON profile containing detailed risk, position, collateral, and margin rate metrics for that order.

**Columns:**
- `riskandmarginpivot`: Internal identifier for the risk‑and‑margin record.
- `ordervault`: Identifier of the order that this risk profile belongs to (matches orders.recordvault).
- `risk_margin_profile`: A JSON document with nested sections such as iceberg, leverage, position, collateral, margin_rates, price_levels, risk_factors, and margin_thresholds.

**Relationships:** ordervault links to orders.recordvault.

**Business Value:** Enables analysts to examine an individual order's risk exposure, margin requirements, and collateral composition, supporting margin‑call and risk‑management decisions.

**⚠️ Ambiguity Flags:**
- `risk_margin_profile`: The JSON fields are shown but the sample does not define the exact business meaning of each sub‑field or unit of measurement.
- `ordervault`: It can be null in the sample, so it is unclear whether every order always has an associated risk profile.

## orders

**Purpose:** This table records each trade order placed by a user. It tracks identifiers, timestamps, market pair, order type, side, price, quantity, notional amount, lifecycle status, and source information.

**Columns:**
- `orderspivot`: Internal sequential ID for the order row.
- `recordvault`: Unique order code used as a reference by other tables.
- `timecode`: Date‑time when the order record was created or last updated.
- `exchspot`: Code of the exchange where the order was sent (padded with spaces in the sample).
- `mktnote`: Market pair symbol, e.g., ETH‑USDT, BTC‑USDT.
- `orderstamp`: Another order identifier shown with trailing spaces.
- `userlink`: User code of the person who placed the order (links to users.userstamp).
- `ordertune`: Order execution style such as Stop, Market, or Limit.
- `dealedge`: Whether the order is a Buy or Sell.
- `dealquote`: Price per unit quoted for the order.
- `dealcount`: Quantity of the asset to trade.
- `notionsum`: Total notional value (price multiplied by quantity).
- `orderflow`: Current lifecycle state like New, Filled, PartiallyFilled, Cancelled.
- `timespan`: Time‑in‑force code such as IOC, GTC, GTD.
- `orderbase`: Source of the order, e.g., API, Web, Mobile.
- `clientmark`: Client‑supplied reference string.
- `createspot`: Timestamp when the order was originally created.
- `updatespot`: Timestamp of the most recent update to the order.

**Relationships:** userlink links to users.userstamp.

**Business Value:** Provides the foundation for measuring trading volume, revenue per market, order success rates, and user activity patterns across different execution venues and order types.

**⚠️ Ambiguity Flags:**
- `exchspot`: The sample shows padded strings like "EX203"; it is not clear whether the code represents a specific exchange, a venue region, or something else.
- `orderbase`: Values API, Web, Mobile suggest order origin, but the exact distinction (e.g., automated vs. manual) is not defined.
- `clientmark`: Purpose of this client‑supplied identifier is unclear from the sample.
- `timespan`: Codes IOC, GTC, GTD are shown but the sample does not explain their exact meaning.
- `ordertune`: Stop, Market, Limit appear to be order types, yet the business rules distinguishing them are not described.

## accountbalances

**Purpose:** This table records the balance snapshot for each user. It tracks total wallet value, amounts that are available, frozen, required for margin, and profit‑and‑loss figures.

**Columns:**
- `accountbalancesnode`: Internal ID for the balance record.
- `walletsum`: Total value of all assets held by the user.
- `availsum`: Portion of the wallet that is free to trade.
- `frozensum`: Amount that is locked or otherwise unavailable.
- `margsum`: Margin requirement amount for open positions.
- `unrealline`: Unrealized profit or loss (floating P/L).
- `realline`: Realized profit or loss (settled P/L).
- `usertag`: User code linking the balance to a user (matches users.userstamp).

**Relationships:** usertag links to users.userstamp.

**Business Value:** Enables calculation of net asset value per client, assessment of margin sufficiency, and performance reporting of realized vs. unrealized gains.

**⚠️ Ambiguity Flags:**
- `walletsum, availsum, frozensum, margsum`: The currency or unit (e.g., USD, USDC) is not specified in the sample.
- `unrealline, realline`: These appear to be profit‑and‑loss amounts, but the sign convention (positive vs. negative) is not explained.

## orderexecutions

**Purpose:** This table records the execution details of each order. It tracks how much of the order was filled, remaining quantity, fill price, total fill value, expiration time, cancellation reason, and execution side.

**Columns:**
- `orderexecmark`: Internal ID for the execution record.
- `fillcount`: Quantity that was actually filled.
- `remaincount`: Quantity still pending after this execution.
- `fillquote`: Price at which the fill occurred.
- `fillsum`: Total monetary value of the filled portion.
- `expirespot`: Timestamp when the order would expire if not filled.
- `cancelnote`: Reason given for cancellation, if any.
- `exectune`: Indicator of maker or taker execution; values seen are "Maker", "Taker" or null.
- `ordersmark`: Order code that this execution belongs to (matches orders.recordvault).

**Relationships:** ordersmark links to orders.recordvault.

**Business Value:** Provides the data needed to compute fill rates, slippage, and the effectiveness of order routing, as well as reasons for order cancellations.

**⚠️ Ambiguity Flags:**
- `exectune`: When null, it is unclear whether the execution side is unknown or not applicable.
- `cancelnote`: Only some rows have a value; the full list of possible reasons is not defined.
- `fillquote, fillsum`: Units (currency) are not stated in the sample.

## systemmonitoring

**Purpose:** This table records operational performance metrics of the trading platform. It tracks API usage, latency, websocket status, rate limits, slippage, execution time, queue length, market impact measures, and a link to analytics indicators.

**Columns:**
- `systemmonitoringpivot`: Internal ID for the monitoring snapshot.
- `apireqtotal`: Total number of API calls handled.
- `apierrtotal`: Total number of API errors encountered.
- `apilatmark`: Measured API latency (value masked in the sample).
- `wsstate`: Current state of the websocket connection (Connected or Disconnected).
- `rateremain`: Remaining API rate‑limit allowance.
- `lastupdnote`: Internal identifier for the last update event.
- `seqcode`: Sequence code associated with the snapshot.
- `slipratio`: Ratio indicating price slippage, shown with positive or negative sign.
- `exectimespan`: Execution time span value (units not specified).
- `queueline`: Length of the processing queue at snapshot time.
- `mkteffect`: Numeric factor representing market impact.
- `priceeffect`: Numeric factor representing price impact.
- `aitrack`: ID linking to a set of analytics indicators (matches analyticsindicators.analyticsindicatorsnode).

**Relationships:** aitrack links to analyticsindicators.analyticsindicatorsnode.

**Business Value:** Helps operations teams monitor system health, detect bottlenecks, and assess the impact of trading activity on market prices.

**⚠️ Ambiguity Flags:**
- `apilatmark`: The actual latency number is masked, so the unit (milliseconds, seconds) cannot be confirmed.
- `slipratio`: Both positive and negative values appear; the business meaning of the sign is not explained.
- `exectimespan`: Units for this time span are not defined in the sample.
- `mkteffect, priceeffect`: The meaning of these numeric factors (e.g., percentage, basis points) is unclear.

## fees

**Purpose:** This table records the fees and rebates applied to each order. It tracks the fee tier, rate, total fee amount, currency, rebate rate, and total rebate for a given order.

**Columns:**
- `feesnode`: Internal ID for the fee record.
- `feerange`: Label of the fee tier (e.g., Tier1, Tier2, etc.).
- `feerate`: Proportion charged as fee (e.g., 0.0015).
- `feetotal`: Total fee amount charged.
- `feecoin`: Currency in which the fee is denominated (e.g., USDC, USDT, USD).
- `rebrate`: Proportion given back as rebate.
- `rebtotal`: Total rebate amount returned.
- `orderslink`: Order code that this fee record is associated with (matches orders.recordvault).

**Relationships:** orderslink links to orders.recordvault.

**Business Value:** Allows calculation of total cost to clients per trade, assessment of revenue from fees, and evaluation of rebate programs.

**⚠️ Ambiguity Flags:**
- `feerange`: The tier names (Tier1‑Tier4) are shown but the business rules that assign a tier to an order are not defined.
- `feecoin`: Multiple currencies appear; it is unclear whether conversion is applied elsewhere.

## marketstats

**Purpose:** This table records daily market statistics for each instrument. It tracks funding rates, open interest, daily volume, trade counts, turnover, price changes, high/low prices, VWAP, market size, supply figures, and liquidity rankings.

**Columns:**
- `marketstatsmark`: Internal ID for the daily market stats row.
- `fundrate`: Funding rate applied to positions (value can be negative).
- `fundspot`: Timestamp when the funding rate was recorded.
- `openstake`: Open interest amount for the day.
- `volday`: Total trading volume for the day (units not specified).
- `tradeday`: Number of individual trades executed.
- `tnoverday`: Total turnover value for the day.
- `priceshiftday`: Percentage price change over the day.
- `highspotday`: Highest price reached during the day.
- `lowspotday`: Lowest price reached during the day.
- `vwapday`: Volume‑weighted average price for the day.
- `mktsize`: Overall market size (value not explicitly defined).
- `circtotal`: Total circulating supply of the asset.
- `totsupply`: Total supply of the asset.
- `maxsupply`: Maximum possible supply of the asset.
- `mkthold`: Proportion of market held (decimal fraction).
- `traderank`: Rank of the market based on trading activity.
- `liquidscore`: Liquidity score (higher indicates more liquid).
- `volmeter`: Additional volume metric (unit not explained).
- `mdlink`: Link to a market data snapshot (matches marketdata.marketdatanode).

**Relationships:** mdlink links to marketdata.marketdatanode.

**Business Value:** Supports market‑analysis teams in evaluating liquidity, price movement, funding cost, and supply dynamics for each trading pair.

**⚠️ Ambiguity Flags:**
- `volday, mktsize, circtotal, totsupply, maxsupply`: The units (e.g., contracts, dollars, tokens) are not indicated in the sample.
- `fundrate`: Both positive and negative values appear; the business interpretation of a negative funding rate is not described.
- `priceshiftday, liquidscore, volmeter`: The scale (percentage, points, index) is ambiguous from the sample alone.

## marketdata

**Purpose:** This table stores a snapshot of order‑book depth and quote information for a market at a specific moment. It includes ask/bid depth, price quotes, spread, and metadata about the exchange and market pair.

**Columns:**
- `marketdatanode`: Internal ID for the market data snapshot.
- `quote_depth_snapshot`: JSON document containing depth (askdepth, biddepth, etc.), quotes (askquote, bidquote, midquote, etc.), spread details, and metadata such as exchange code, market pair, and timestamp.

**Relationships:** None declared in this table (referenced by marketstats.mdlink and analyticsindicators.mdataref).

**Business Value:** Provides the raw market state needed for pricing, liquidity analysis, and feeding downstream sentiment calculations.

**⚠️ Ambiguity Flags:**
- `quote_depth_snapshot`: The JSON structure is shown, but the business meaning of each numeric field (e.g., askdepth vs. askunits) is not explained.

## analyticsindicators

**Purpose:** This table records calculated market sentiment indicators derived from market data and market statistics. It links to a specific market data snapshot and daily market stats and stores a JSON of various sentiment metrics.

**Columns:**
- `analyticsindicatorsnode`: Internal ID for the sentiment indicator record.
- `mdataref`: Reference to a market data snapshot (matches marketdata.marketdatanode).
- `mstatsref`: Reference to daily market stats (matches marketstats.marketstatsmark).
- `market_sentiment_indicators`: JSON object containing sub‑sections such as flow, walls, momentum, arbitrage, big_players, and oscillators with numeric and textual metrics.

**Relationships:** mdataref links to marketdata.marketdatanode; mstatsref links to marketstats.marketstatsmark.

**Business Value:** Enables traders and analysts to gauge market mood, potential price pressure, and trading dynamics using composite sentiment scores.

**⚠️ Ambiguity Flags:**
- `market_sentiment_indicators`: The JSON fields (e.g., instflow, buywallband, mktfeel) are shown but their precise business definitions and scales are not described in the sample.
