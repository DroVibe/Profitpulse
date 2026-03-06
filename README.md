# ProfitPulse

AI-powered business analytics dashboard built with Streamlit + Venice AI.

![ProfitPulse](https://via.placeholder.com/800x400?text=ProfitPulse)

## Features

- 📊 **P&L Dashboard** — Real-time profit & loss visualization
- 🤖 **AI Advisor** — Chat with an AI CFO for actionable insights
- 🔮 **What-If Simulator** — Model business scenarios
- 📤 **Export** — Download data as CSV or professional PDF
- 📈 **Interactive Charts** — Revenue trends, category breakdown, labor costs

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/DroVibe/Profitpulse.git
cd Profitpulse

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your Venice API key

# 5. Run the app
streamlit run profitpulse.py
```

## Environment Variables

Create a `.env` file:

```env
VENICE_API_KEY=your_venice_api_key_here
APP_USER=admin
APP_PASS=pilot2026
```

## Demo Credentials

- Username: `admin`
- Password: `pilot2026`

## Business Types Supported

- Auto Repair
- Coffee Shop
- Retail Clothing
- Restaurant
- Freelance/Service

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your GitHub account
4. Select this repo and deploy

## Tech Stack

- **Frontend:** Streamlit
- **AI:** Venice AI (Llama 3.3 70B)
- **Charts:** Plotly
- **PDF:** FPDF
- **Data:** Pandas, NumPy

## License

MIT