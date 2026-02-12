# Future Wallet - Financial Simulation Engine

High-fidelity financial projection and simulation engine for DATAFEST'26. Models complex user financial trajectories with daily granularity, multi-currency support, and deterministic reproducibility.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Run the Application

```bash
# Activate virtual environment (if using)
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Run Streamlit app
streamlit run app.py

# App will open at http://localhost:8501
```

## ✨ Features

- **🔒 Deterministic Simulation**: Bit-exact reproducibility with seeded random generation
- **🌍 Multi-Currency Support**: USD, EUR, GBP, PKR with daily exchange rate volatility
- **💎 Asset Portfolio Management**: Liquid, Illiquid, Yield-generating, and Volatile assets
- **💳 Liability Tracking**: Loans with interest accrual and payment schedules
- **📊 Credit Score Evolution**: Dynamic credit scoring based on debt ratios and payment history
- **💰 Progressive Taxation**: Configurable tax brackets with capital gains tracking
- **📈 Comprehensive Analytics**: Balance trajectories, bankruptcy risk, NAV, liquidity ratios
- **🎨 Interactive Visualization**: Plotly charts with real-time parameter adjustment

## 🏗️ Architecture

```
VibeCode/
├── app.py                      # Main Streamlit application
├── config/
│   └── config.yaml            # Configuration (currencies, tax brackets, etc.)
├── src/
│   ├── core/
│   │   ├── engine.py          # Main simulation engine
│   │   ├── state.py           # State management with snapshots
│   │   └── dag.py             # Dependency graph resolution
│   ├── components/
│   │   ├── currency.py        # Multi-currency exchange system
│   │   ├── assets.py          # Asset portfolio manager
│   │   ├── credit.py          # Credit scoring calculator
│   │   ├── taxation.py        # Progressive taxation engine
│   │   └── liabilities.py     # Debt/liability manager
│   ├── models/
│   │   └── models.py          # Pydantic data models
│   └── visualization/
│       └── charts.py          # Plotly chart generators
├── tests/                      # Unit and integration tests
└── requirements.txt           # Python dependencies
```

## 📊 Simulation Outputs

The engine produces comprehensive metrics:

| Category | Metrics |
|----------|---------|
| **Finality** | Final Balance (Expected, 5th, 95th percentiles) |
| **Risk** | Bankruptcy Probability & Timing |
| **Health** | Financial Vibe & Credit Score |
| **Assets** | Net Asset Value (NAV) & Liquidity Ratio |

## 🎯 Demo Scenarios

### Scenario 1: Stable Growth
- Monthly income: $5,000
- Monthly expenses: $3,000
- Initial assets: $10,000
- Horizon: 5 years
- **Expected**: Steady growth, low bankruptcy risk

### Scenario 2: High Risk
- Monthly income: $3,000
- Monthly expenses: $4,500
- Liabilities: $50,000 loan
- Horizon: 3 years
- **Expected**: High bankruptcy probability, asset liquidation

### Scenario 3: Multi-Currency
- Income in USD, expenses in EUR
- Assets in PKR and GBP
- Exchange rate volatility enabled
- **Expected**: Currency risk impact on final balance

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src
```

## 📝 Configuration

Edit `config/config.yaml` to customize:
- Supported currencies
- Tax brackets
- Asset volatility ranges
- Default simulation parameters

## 🔧 Technology Stack

- **Backend**: Python 3.12+
- **Core Libraries**: NumPy, Pandas, SciPy, Pydantic
- **UI**: Streamlit
- **Visualization**: Plotly
- **Storage**: SQLite (for snapshots)

## 📄 License

MIT License - DATAFEST'26 Project

## 👥 Contributors

Built for DATAFEST'26 Hackathon
