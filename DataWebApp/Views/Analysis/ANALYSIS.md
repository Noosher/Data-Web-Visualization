# Daily Analysis - Technical Documentation

## Overview

The Daily Analysis page (`DailyAspNetAnalysis.cshtml`) is a comprehensive crypto asset performance dashboard that displays KPI (Key Performance Indicator) cards for all active cryptocurrency assets. Each card provides visual analytics including performance scoring, trend analysis, and predictive forecasting.

## Architecture & Design Pattern

### Template-Based OOP Approach

The system follows an **Object-Oriented Template Pattern** where:
- **One reusable template** (`_AssetKpiCard.cshtml`) renders all KPI cards
- **Data-driven design**: Each asset's data is passed to the template as a `AssetKpiCardViewModel`
- **Separation of concerns**: Business logic (AnalyticsService) → Controllers → ViewModels → Views

```
AnalyticsService.cs
    ↓ (calculates metrics)
AssetKpiCardViewModel
    ↓ (passes data)
_AssetKpiCard.cshtml Template
    ↓ (renders with data)
Individual KPI Card (displayed in grid)
```

### Key Components

1. **AnalyticsService.cs** - Core business logic service
   - Calculates performance scores
   - Performs linear regression
   - Aggregates volume data
   - Generates explanations

2. **AnalysisController.cs** - MVC controller
   - Handles HTTP requests
   - Applies sorting and filtering
   - Prepares ViewModels

3. **ViewModels** (`AssetKpiCardViewModel.cs`, `DailyAnalysisViewModel.cs`)
   - Data transfer objects
   - No business logic
   - Clean interface between controller and view

4. **View Template** (`_AssetKpiCard.cshtml`)
   - Reusable partial view
   - Accepts `AssetKpiCardViewModel`
   - Renders charts via JavaScript

5. **JavaScript** (`analysis-daily.js`)
   - Initializes ApexCharts
   - Handles chart rendering
   - Manages theme adaptation

---

## Performance Score Algorithm

### Purpose
Evaluate asset performance considering both **recent trend** and **overall position** relative to historical data.

### Algorithm Details

The score is calculated using **three weighted components**:

#### Component 1: Position in Historical Range (70% weight)
```
positionInRange = (currentPrice - historicalMin) / (historicalMax - historicalMin)
positionScore = positionInRange × 100
```

**Purpose**: Prevents overly optimistic scores when price is still low overall.

**Example**:
- Historical range: $10,000 - $50,000
- Current price: $20,000
- Position: (20,000 - 10,000) / (50,000 - 10,000) = 0.25 (25%)
- Position Score: 25

This means even if trending up recently, if we're at 25% of historical range, the score reflects that reality.

#### Component 2: Recent Trend (30% weight)
```
trendPercent = ((recent30DayAvg - historicalAvg) / historicalAvg) × 100
trendScore = 50 + trendPercent (clamped to 0-100)
```

**Purpose**: Rewards improvement but doesn't dominate the score.

**Example**:
- Recent 30-day average: $21,000
- Historical average: $20,000
- Trend: ((21,000 - 20,000) / 20,000) × 100 = +5%
- Trend Score: 50 + 5 = 55

#### Component 3: Momentum Adjustment (±10% max)
```
momentumPercent = ((currentPrice - recent30DayAvg) / recent30DayAvg) × 100
momentumAdjustment = momentumPercent × 0.1
```

**Purpose**: Small bonus/penalty for current momentum direction.

**Example**:
- Current price: $22,000
- Recent 30-day average: $21,000
- Momentum: ((22,000 - 21,000) / 21,000) × 100 = +4.76%
- Adjustment: 4.76 × 0.1 = +0.48

#### Final Score Calculation
```
finalScore = (positionScore × 0.7) + (trendScore × 0.3) + momentumAdjustment
finalScore = clamped to [0, 100]
```

**Full Example**:
```
Final Score = (25 × 0.7) + (55 × 0.3) + 0.48
            = 17.5 + 16.5 + 0.48
            = 34.48
```

**Interpretation**:
- **0-40**: Weak performance (low position + poor trend)
- **40-70**: Moderate performance (mid-range or mixed signals)
- **70-100**: Strong performance (high position + good trend)

### Why This Algorithm is Less Forgiving

**Old Algorithm** (single factor):
- Only looked at: Recent 30d avg vs Historical avg
- Problem: If asset crashed 80% but recovered 10%, score would be decent
- Example: Peak $50K → Crash to $10K → Recover to $12K = Score ~60 (misleading!)

**New Algorithm** (multi-factor):
- Primarily looks at: Where are we in the historical range? (70% weight)
- Same example: Peak $50K → Current $12K = Position 5% of range
- Final Score: ~20 (accurately reflects we're still way down despite recent bounce)

---

## Linear Regression Forecast

### Purpose
Predict future price using linear regression (best-fit line through historical data).

### Mathematical Model

**Equation**: `y = mx + b`
- y = predicted price
- x = days from start
- m = slope (rate of price change per day)
- b = y-intercept (starting price)

### Calculation Steps

1. **Data Preparation**
   - Use most recent 90 days (or all available if less)
   - Convert dates to numeric days from first observation
   - Extract prices as y-values

2. **Calculate Slope (m)**
   ```
   m = (n×Σxy - Σx×Σy) / (n×Σx² - (Σx)²)
   ```
   Where:
   - n = number of data points
   - Σxy = sum of (day × price) products
   - Σx = sum of day values
   - Σy = sum of prices
   - Σx² = sum of squared day values

3. **Calculate Intercept (b)**
   ```
   b = (Σy - m×Σx) / n
   ```

4. **Calculate Confidence (R²)**
   ```
   R² = 1 - (SS_residual / SS_total)

   SS_total = Σ(y - ȳ)²     (total variance)
   SS_residual = Σ(y - ŷ)²   (unexplained variance)
   ```

   R² ranges from 0-1 (0% - 100%):
   - **R² > 0.7**: High confidence - data fits line well
   - **R² 0.4-0.7**: Medium confidence - moderate fit
   - **R² < 0.4**: Low confidence - poor fit

5. **Determine Forecast Horizon**
   Dynamic based on data quality:
   ```
   Base forecast days:
   - 90+ days of data → 30 days ahead
   - 60-89 days → 14 days ahead
   - 30-59 days → 7 days ahead
   - <30 days → 3 days ahead

   Adjusted by R²:
   - R² < 0.3 → divide by 3 (low confidence = short forecast)
   - R² 0.3-0.6 → divide by 2
   - R² > 0.6 → full forecast (high confidence)
   ```

6. **Make Prediction**
   ```
   futureDay = currentDay + forecastDays
   predictedPrice = m × futureDay + b
   ```

### Example Calculation

**Given**:
- 90 days of data
- Current price: $42,158.25
- Data produces: m = 125.46, b = 34,356.13
- R² = 0.7245 (72.45% confidence)

**Forecast**:
- Horizon: 90 days + High R² → 30 days ahead
- Future day value: 89 + 30 = 119
- Prediction: 125.46 × 119 + 34,356.13 = **$49,281.80**
- Confidence: **HIGH** (72.45%)

### Limitations
- Assumes linear trend continues (may not capture market volatility)
- Less reliable further into future
- Should be used as guidance, not absolute prediction
- External events (news, regulation) not factored in

---

## Charts & Visualizations

### 1. Radial Gauge Chart (Performance Score)

**Library**: ApexCharts (Radial Bar type)

**Purpose**: Visual representation of performance score (0-100)

**Features**:
- Color-coded by score:
  - **Green** (#22c55e): Score ≥ 70 (strong)
  - **Amber** (#f59e0b): Score 40-70 (moderate)
  - **Red** (#ef4444): Score < 40 (weak)
- Semi-circle layout (startAngle: -90°, endAngle: 90°)
- Score overlaid at center with perfect centering (flexbox)
- Theme-aware track background

**Implementation**:
```javascript
// Gauge centered score overlay
.kpi-score-overlay {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}
```

### 2. Area Chart (Price Trend)

**Library**: ApexCharts (Area type)

**Purpose**: Visualize price movement over selected time period

**Features**:
- Smooth curve (`curve: 'smooth'`)
- Gradient fill (opacity 0.5 → 0.1)
- Accent color (#38bdf8)
- Responsive to light/dark theme
- Tooltip shows date and price
- No toolbar (cleaner look)

**Data Format**:
```javascript
{
    x: timestamp,  // Date as milliseconds
    y: price       // Decimal price value
}
```

### 3. Bar Chart (Volume by Period)

**Library**: ApexCharts (Bar type)

**Purpose**: Show trading volume aggregated by date ranges

**Features**:
- **Dynamic period sizing** based on data range:
  - ≤30 days: 5-day periods
  - 31-60 days: Weekly (7 days)
  - 61-180 days: Bi-weekly (14 days)
  - 180+ days: Monthly (30 days)
- **Date range labels**: "Dec 01 - Dec 07" (not "Week 52")
- **Wider bars**: 85% column width
- Gradient fill (blue → purple)
- **Collapsible**: Click header to show/hide
- Rotated labels for readability

**Label Format Example**:
```
30-day view:  "Dec 01 - Dec 05", "Dec 06 - Dec 10"
90-day view:  "Oct 01 - Oct 14", "Oct 15 - Oct 28"
365-day view: "Jan 01 - Jan 31", "Feb 01 - Feb 28"
```

**Calculation Logic**:
```csharp
// Group prices into periods
foreach (price in prices) {
    if (periodStart == null) {
        periodStart = price.Date;
    }
    else if ((price.Date - periodStart).Days < periodDays) {
        // Add to current period
    }
    else {
        // Finalize period with date range label
        Label = $"{periodStart:MMM dd} - {periodEnd:MMM dd}"
        Value = sum of volumes

        // Start new period
    }
}
```

---

## Filtering & Sorting

### Sorting

**Location**: Top of page, next to title

**Options**:
- Symbol (A-Z alphabetical)
- Current Price ($ low → high or high → low)
- Market Cap ($ low → high or high → low)
- Performance Score (0-100 low → high or high → low)

**Implementation**:
- Server-side sorting (efficient for large datasets)
- Preserves all filter states
- Toggle button for ascending/descending (↑/↓)

### Group Filtering

**Location**: Right sidebar under "Filter by Group"

**Features**:
- Multi-select checkboxes
- Shows assets in ANY selected group (OR logic)
- Groups loaded from database dynamically:
  - TOP15
  - MEME_TOP5
  - L1_BLUECHIP
  - DEFI_BLUECHIP
- State preserved in URL parameters

**SQL Logic**:
```csharp
// Filter assets that belong to selected groups
var assetsInGroups = db.CryptoAssets
    .Where(a => a.IsActive && a.Groups.Any(g => selectedTags.Contains(g.Tag)))
    .Select(a => a.Id);

// Then filter KPI cards
assetKpis = assetKpis.Where(kpi => assetsInGroups.Contains(kpi.AssetId));
```

---

## Responsive Design

### Grid Layout

**CSS Grid** with dynamic columns:

```css
.kpi-cards-grid[data-cols="3"] {
    grid-template-columns: repeat(3, 1fr);
}
```

**Breakpoints**:
- **Ultra-wide (1920px+)**: 3 cols = 450px min, 4 cols = 400px min
- **Large (1400-1919px)**: 3 cols = 380px min, 4 cols = 350px min
- **Medium (1024-1399px)**: Max 3 columns
- **Tablet (768-1023px)**: 2 columns
- **Mobile (<768px)**: 1 column

**User Control**:
- Layout toggle buttons (2/3/4 columns) on large screens
- Preference saved to localStorage

### Theme Adaptation

**Light/Dark Mode**:
- Chart text color: `#1f2937` (dark) for light mode contrast
- Grid opacity: `0.15` (darker) for visibility
- Gauge track: `rgba(15, 23, 42, 0.15)` in light mode
- Automatic theme detection via `data-theme` attribute

---

## Data Flow

### Request Lifecycle

1. **User navigates** to `/Analysis/DailyAspNetAnalysis`
   - Optional params: `days`, `sortBy`, `sortOrder`, `groups[]`

2. **Controller** (`AnalysisController.DailyAspNetAnalysis`)
   - Calls `AnalyticsService.GetFilteredKpiDataAsync()`
   - Applies group filtering (if selected)
   - Sorts results
   - Loads available groups from database
   - Builds `DailyAnalysisViewModel`

3. **Service** (`AnalyticsService`)
   - For each active asset:
     - Loads price history from database
     - Calculates performance score (3-component algorithm)
     - Performs linear regression
     - Aggregates volume by periods
     - Generates tooltip explanations
   - Returns `List<AssetKpiCardViewModel>`

4. **View** (`DailyAspNetAnalysis.cshtml`)
   - Renders page header with sorting controls
   - Loops through `Model.AssetKpis`
   - For each KPI: renders `_AssetKpiCard.cshtml` partial

5. **Partial View** (`_AssetKpiCard.cshtml`)
   - Serializes chart data to JSON
   - Embeds data attributes on card element
   - Generates HTML structure

6. **JavaScript** (`analysis-daily.js`)
   - On `DOMContentLoaded`:
     - Finds all KPI cards
     - Parses JSON data attributes
     - Initializes 3 ApexCharts per card:
       - Gauge (performance score)
       - Line (price trend)
       - Bar (volume periods)

### Database Queries

**Main Query** (per asset):
```csharp
var allPrices = await db.CryptoAssetPriceDailies
    .Where(p => p.AssetId == assetId)
    .OrderBy(p => p.ObservedAt)
    .ToListAsync();
```

**Group Filter Query**:
```csharp
var assetsInGroups = await db.CryptoAssets
    .Where(a => a.IsActive && a.Groups.Any(g => groupTags.Contains(g.Tag)))
    .Select(a => a.Id)
    .ToListAsync();
```

**Available Groups Query**:
```csharp
var allGroups = await db.CryptoGroups
    .OrderBy(g => g.Tag)
    .Select(g => new GroupOption { Tag, DisplayName, IsSelected })
    .ToListAsync();
```

---

## Performance Considerations

### Optimizations

1. **Single query per asset**: All price data loaded once
2. **In-memory calculations**: Algorithms run on fetched data (no extra DB hits)
3. **Server-side sorting**: Efficient for large datasets
4. **Chart initialization**: Deferred to client-side JavaScript
5. **Collapsible sections**: Bar chart hidden by default to reduce initial render

### Scalability

**Current**: Handles 15-30 active assets efficiently

**If scaling to 100+ assets**:
- Consider pagination (10-20 cards per page)
- Add lazy loading for charts (render on scroll)
- Cache AnalyticsService results (Redis/MemoryCache)
- Consider background processing for heavy calculations

---

## File Structure

```
DataWebApp/
├── Controllers/
│   └── AnalysisController.cs          # Routes and orchestration
├── Services/
│   └── AnalyticsService.cs            # Core business logic
├── Models/
│   ├── DailyAnalysisViewModel.cs      # Page-level model
│   └── AssetKpiCardViewModel.cs       # Card-level model
├── Views/
│   └── Analysis/
│       ├── DailyAspNetAnalysis.cshtml # Main page view
│       ├── _AssetKpiCard.cshtml       # Reusable card template
│       ├── ComingSoon.cshtml          # Placeholder view
│       └── ANALYSIS.md                # This documentation
├── wwwroot/
│   ├── css/
│   │   └── kpi.css                    # KPI-specific styles
│   └── js/
│       ├── analysis-daily.js          # Chart initialization
│       └── sidebar-toggle.js          # Sidebar controls
└── Data/
    └── CryptoAssetPriceDaily.cs       # EF Core model
```

---

## Future Enhancements

### Potential Improvements

1. **Historical Breakdown Page**
   - Full detailed explanations with formulas
   - Step-by-step calculations
   - Educational content for understanding algorithms

2. **Export Functionality**
   - Download KPI data as CSV/JSON
   - Generate PDF reports

3. **Comparison Mode**
   - Select 2-3 assets for side-by-side comparison
   - Overlay price trends on single chart

4. **Custom Scoring**
   - User-adjustable weights for score components
   - Save custom scoring profiles

5. **Real-Time Updates**
   - WebSocket integration for live price updates
   - Auto-refresh charts

6. **Advanced Regression**
   - Polynomial regression (quadratic, cubic curves)
   - ARIMA time series models
   - Machine learning predictions

7. **Alerts & Notifications**
   - Score threshold alerts
   - Price target notifications

---

## Dependencies

### Backend
- **ASP.NET Core 10.0**: MVC framework
- **Entity Framework Core 10.0**: Database ORM
- **Npgsql 10.0**: PostgreSQL provider

### Frontend
- **ApexCharts 3.45.1**: Charting library
- **Tippy.js 6.3.7**: Tooltips
- **Bootstrap 5**: UI framework
- **jQuery**: DOM manipulation

### Database
- **PostgreSQL**: Primary data store (Neon cloud)
- **Tables**: `crypto_asset`, `crypto_asset_price_daily`, `crypto_group`

---

## Conclusion

The Daily Analysis page demonstrates:
- **Clean OOP architecture**: Template pattern with reusable components
- **Advanced algorithms**: Multi-factor scoring, linear regression with confidence
- **Responsive design**: Works on all screen sizes
- **User-centric features**: Sorting, filtering, collapsible sections
- **Professional polish**: Theme support, smooth animations, accessibility

This documentation serves as both a technical reference and a portfolio showcase of software engineering best practices.

---

**Last Updated**: December 2024
**Author**: Cloud Crypto Intelligence Platform
**Version**: 1.0
