# 🌱 CropWise

**Smart Markets. Better Prices. Stronger Farmers.**

CropWise is a market-linkage and price-discovery platform designed to help farmers make better selling decisions by connecting **market prices, selling opportunities, buyers, transportation, and profit analysis** in one platform.

Built for the **“Strengthening Market Linkages and Price Discovery for Farmers”** problem statement, CropWise goes beyond simply displaying mandi prices. It addresses the practical questions farmers face:

> **What should I sell? Where should I sell it? When should I sell it? To whom? And how much will I actually earn after costs?**

---

## 🚀 MVP Overview

CropWise is designed as a full-stack agricultural marketplace and decision-support platform.

The MVP combines:

- Market price comparison
- Net-profit calculation
- Farmer-buyer marketplace
- Smart buyer matching
- FarmPool shared transportation
- Group selling
- Price forecasting
- Explainable selling recommendations
- Multilingual interaction
- Alerts and notifications
- Admin impact monitoring
- Persistent cloud database using **PostgreSQL on Supabase**

---

# ✨ Core Features

| FeatureDescription           |                                                                          |
| ---------------------------- | ------------------------------------------------------------------------ |
| 🌐 **Multilingual Platform** | UI and assistant support for multiple Indian languages                   |
| 📊 **Market Intelligence**   | Compare market prices and calculate expected net realization after costs |
| 🤖 **AgriAdvisor**           | Explainable sell-now vs. hold recommendations                            |
| 📈 **Price Forecast**        | Short-term price trend and confidence analysis                           |
| 🌾 **AgriMarket**            | Farmers create listings and verified buyers submit offers                |
| ⭐ **Smart Buyer Matching**   | Buyers ranked using price, distance, reliability and crop interest       |
| 🚚 **FarmPool**              | Shared transportation to reduce logistics cost                           |
| 🧮 **Profit Calculator**     | Compare different selling scenarios                                      |
| 🤝 **Group Selling**         | Pool produce through FPO/cooperative-style groups                        |
| 🔔 **Alerts**                | Price, demand and harvest-related notifications                          |
| 🌐🎤 **Farm Assistant**      | Multilingual text assistant with browser voice support                   |
| 📷 **Quality Assessment**    | AI-ready quality grading architecture                                    |
| 📈 **Impact Dashboard**      | Monitor farmers, buyers, transactions and estimated impact               |
| 🕵️ **User Activity**        | Track login activity through an admin-protected dashboard                |

The feature set is based on the existing CropWise MVP documented in the previous implementation.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │       FARMER        │
                         │       / BUYER       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   React + Vite      │
                         │ Tailwind + Recharts │
                         │      Vercel         │
                         └──────────┬──────────┘
                                    │
                              HTTPS / REST
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI         │
                         │     Backend         │
                         │      Render         │
                         └──────────┬──────────┘
                                    │
                              SQLAlchemy ORM
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ PostgreSQL Database │
                         │      Supabase       │
                         └─────────────────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             ▼                      ▼                      ▼
         Farmers                 Buyers                Listings
         Offers             Market Prices           Transactions
         FarmPool           Price History           Login Events
         Groups              Notifications           User Data
```

---

# 🗄️ Database Architecture

The new CropWise MVP uses **PostgreSQL hosted on Supabase** as the persistent application database.

### Main database entities

```text
farmers
buyers
listings
offers
market_prices
price_history
groups
group_members
farmpools
notifications
login_events
transactions
```

The database layer uses **SQLAlchemy ORM**, allowing the FastAPI backend to communicate with PostgreSQL through a structured model layer.

### Why PostgreSQL + Supabase?

- Persistent cloud storage
- Production-oriented relational database
- Reliable multi-user access
- Better suited to deployed applications than a local database file
- Easy integration with Render through environment variables
- Centralized data for farmers, buyers, listings and transactions

---

# 🧩 Tech Stack

### Frontend

- React 18
- Vite
- Tailwind CSS
- Recharts

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic

### Database

- **PostgreSQL**
- **Supabase**

### Authentication

- JWT
- bcrypt password hashing
- Role-based authentication for Farmer, Buyer and Admin

### Deployment

```text
Frontend → Vercel
Backend  → Render
Database → Supabase PostgreSQL
```

The original implementation already uses React/Vite/Tailwind on the frontend and FastAPI/SQLAlchemy on the backend; the database layer is the part being moved from SQLite to PostgreSQL.

---

# 🌐 Multilingual Architecture

CropWise follows a **language-neutral business-logic architecture**.

```text
User Input
   │
   ▼
Language / Intent Detection
   │
   ▼
Crop + Quantity + Location Extraction
   │
   ▼
CropWise Business Logic
   │
   ├── Market Comparison
   ├── Recommendation Engine
   ├── Buyer Matching
   └── Profit Calculation
   │
   ▼
Localized Response
```

Language is treated as a **presentation and interaction layer**, so the core market and recommendation logic remains independent of the selected language.

The current architecture includes language-specific dictionaries, intent handling, response templates and frontend translation files.

---

# 📊 Market Intelligence

CropWise compares selling opportunities based on more than the displayed mandi price.

The platform considers:

```text
Expected Revenue
       -
Transportation Cost
       -
Mandi Charges
       -
Handling Cost
       =
Expected Net Realisation
```

This allows farmers to compare markets based on **actual expected earnings**, rather than simply choosing the market showing the highest quoted price.

The existing MVP already follows this net-profit approach.

---

# 🤖 Explainable AgriAdvisor

CropWise provides an explainable recommendation rather than presenting an unexplained prediction.

Example:

```text
Recommendation: SELL NOW

Why?

✓ Market price is increasing
✓ Demand is high
✓ Transport cost is manageable
✓ Supply pressure is moderate
✓ Current market provides higher expected net realisation
```

The recommendation engine evaluates factors such as:

- Demand
- Supply
- Price trend
- Transport cost
- Weather risk

The existing MVP is explicitly designed as an explainable rules-based engine rather than a black-box LLM.

---

# 📈 Price Forecast

CropWise provides short-term price forecasting with a visible confidence indicator.

```text
Historical Market Data
         │
         ▼
Trend Analysis
         │
         ▼
Volatility Analysis
         │
         ▼
7-Day Forecast
         │
         ▼
Confidence Score
```

The architecture is designed so the forecasting component can later be replaced with a trained ML model without redesigning the application APIs.

---

# 🌾 AgriMarket

Farmers can:

1. Create a harvest listing
2. Specify crop and quantity
3. Define an acceptable price
4. Add listing details
5. Receive buyer offers
6. Compare offers
7. Accept the most suitable offer

Buyers can:

1. Browse available produce
2. View listing information
3. Submit offers
4. Compete for farmer listings

Server-side validation protects the marketplace workflow.

---

# ⭐ Smart Buyer Matching

CropWise ranks buyers based on multiple factors:

```text
Buyer Match Score
        │
        ├── Offered Price
        ├── Distance
        ├── Reliability
        ├── Payment History
        └── Crop Interest
```

The system also provides reasons for the ranking instead of simply showing a score.

---

# 🚚 FarmPool

FarmPool enables farmers travelling toward the same market to share transportation.

Example:

```text
Farmer A ─────┐
              │
Farmer B ─────┼────► Shared Transport ───► Market
              │
Farmer C ─────┘
```

This can reduce:

- Per-farmer transportation cost
- Empty vehicle capacity
- Fuel consumption
- Carbon emissions

### Environmental Impact

Shared transportation can contribute to:

- **Lower CO₂ emissions**
- **Reduced fuel usage**
- **Better vehicle utilization**
- **More sustainable agricultural logistics**

---

# 🧮 Profit Calculator

Farmers can compare multiple selling scenarios.

### Example

```text
Option A → Local Mandi
Option B → Distant Mandi
Option C → Direct Buyer
Option D → FarmPool + Buyer
```

Each scenario can show:

```text
Gross Revenue
- Transport
- Mandi Charges
- Handling
= Expected Net Income
```

This helps farmers select the option with the highest expected realization rather than the highest raw price.

---

# 🤝 Group Selling

CropWise supports pooled selling through farmer groups, FPOs and cooperative-style structures.

Each farmer maintains an individual membership and quantity contribution.

The system avoids double-counting when a farmer rejoins an existing group.

---

# 🔔 Alerts & Notifications

CropWise can support notifications for:

- Price changes
- High-demand opportunities
- Market opportunities
- Harvest reminders
- Buyer activity

---

# 🌐 Multilingual Farm Assistant

The assistant supports natural farmer queries such as:

> “मेरे पास 10 क्विंटल धान है, कहाँ बेचने पर ज्यादा फायदा होगा?”

The system identifies:

```text
Intent
Crop
Quantity
Location
```

and then passes those entities to the same market and recommendation engine used by the rest of the application.

The assistant does not silently invent a crop or location when information is missing.

---

# 🔐 Security

CropWise includes:

- JWT authentication
- bcrypt password hashing
- Role-based authorization
- Admin-protected dashboard
- Server-side marketplace validation
- Protected user information
- Environment-variable based secrets
- Secure database credentials

The earlier implementation also introduced protections for admin routes, user contact information and marketplace offer validation.

---

# 🕵️ User Activity

The admin dashboard can monitor:

- Total registered farmers
- Total registered buyers
- Unique users logged in
- Successful login events
- Failed login attempts
- Recent login activity

Login events are stored without recording passwords, tokens or API keys.

---

# 📂 Project Structure

```text
cropwise/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth_utils.py
│   │   ├── seed_data.py
│   │   │
│   │   ├── services/
│   │   │   ├── recommendation_engine.py
│   │   │   ├── price_predictor.py
│   │   │   ├── buyer_matcher.py
│   │   │   ├── transport_optimizer.py
│   │   │   └── quality_grading.py
│   │   │
│   │   ├── routers/
│   │   └── i18n/
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── context/
│   │   ├── components/
│   │   ├── pages/
│   │   └── i18n/
│   │
│   ├── package.json
│   └── .env.example
│
└── README.md
```

The structure follows the existing CropWise organization documented in the previous MVP.

---

# ⚙️ Environment Variables

## Backend

```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<database>

SECRET_KEY=<strong-secret-key>

ADMIN_USERNAME=<admin-username>
ADMIN_PASSWORD=<admin-password>

DATA_GOV_IN_API_KEY=<api-key>

MARKET_DATA_SOURCE=live
```

## Frontend

```env
VITE_API_BASE_URL=<backend-url>
```

**Never commit** **`.env`** **files or database credentials to GitHub.**

---

# ▶️ Local Development

## 1. Clone the repository

```bash
git clone https://github.com/Abha153/cropwise.git
cd cropwise
```

## 2. Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

## 3. Frontend

Open another terminal:

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

# ☁️ Deployment Architecture

```text
                    INTERNET USERS
                          │
                          ▼
                 ┌─────────────────┐
                 │     Vercel      │
                 │ React Frontend  │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │     Render      │
                 │ FastAPI Backend │
                 └────────┬────────┘
                          │
                     SQLAlchemy
                          │
                          ▼
                 ┌─────────────────┐
                 │     Supabase    │
                 │   PostgreSQL    │
                 └─────────────────┘
```

This architecture separates the presentation layer, backend business logic and persistent database layer.

---

# 📡 External Data Integration

CropWise is designed to integrate government market-price data.

The existing implementation includes integration points for two government data resources and distinguishes between live and demo data.

The application should clearly label data as:

```text
LIVE
```

or

```text
DEMO
```

rather than presenting synthetic data as real market information.

---

# 🧠 AI / ML Roadmap

The current MVP uses explainable and deterministic decision logic in several areas.

Future AI/ML expansion can include:

```text
MVP
 │
 ├── Rules-based recommendations
 ├── Transparent forecasting
 └── Deterministic quality grading
        │
        ▼
DATA EXPANSION
        │
        ▼
AI / ML
        │
        ├── ML price forecasting
        ├── Demand prediction
        ├── Computer-vision crop grading
        ├── Intelligent buyer matching
        └── Personalized recommendations
        │
        ▼
SCALE
```

The previous implementation already defines service boundaries intended to allow trained ML/CV models to replace deterministic components later.

---

# 📈 Impact

CropWise aims to improve:

### Economic Impact

- Better price discovery
- Higher farmer net realization
- Direct access to buyers
- Lower transaction costs

### Social Impact

- Better farmer-buyer connectivity
- Support for cooperative/group selling
- Multilingual access

### Environmental Impact

- Shared transportation
- Lower fuel consumption
- Reduced empty trips
- Lower estimated CO₂ emissions

---

# 🛣️ Future Scope

### Phase 1 — Current MVP

- Market comparison
- Farmer-buyer marketplace
- FarmPool
- Profit analysis
- Explainable recommendations
- Supabase PostgreSQL backend

### Phase 2 — Data Expansion

- More states
- More commodities
- Larger historical price datasets
- More buyer networks

### Phase 3 — AI/ML

- ML-based price prediction
- Demand forecasting
- Computer-vision quality assessment
- Personalized selling recommendations

### Phase 4 — Scale

- FPO partnerships
- Institutional buyers
- B2B marketplace
- Premium analytics
- Large-scale logistics optimization

---

# 🎯 Suggested Demo Flow

```text
1. Farmer Login
        ↓
2. Market Intelligence
        ↓
3. Compare Net Realisation
        ↓
4. AgriAdvisor Recommendation
        ↓
5. Price Forecast
        ↓
6. Create / View AgriMarket Listing
        ↓
7. Smart Buyer Matching
        ↓
8. FarmPool Transport Savings
        ↓
9. Profit Calculator
        ↓
10. Multilingual Assistant
        ↓
11. Buyer Login + Offer
        ↓
12. Admin Impact Dashboard
```

This follows the existing recommended judging flow.

---

# 📌 Project Highlights

**Smart Markets. Better Prices. Stronger Farmers.**

CropWise brings together:

```text
Market Data
     +
Decision Intelligence
     +
Buyer Connectivity
     +
Transport Optimization
     +
Profit Analysis
     +
Cloud Database
     =
Integrated Farmer Market Platform
```

---

# 🔗 Links

**GitHub:**
https://github.com/Abha153/cropwise

**Live Application:**
[https://cropwise-alpha.vercel.app](https://cropwise-alpha.vercel.app/)

---

# 📜 Project Status

**Current Stage:** MVP

**Architecture:** Full-stack cloud deployment

**Database:** PostgreSQL on Supabase

**Frontend:** React + Vite + Tailwind CSS

**Backend:** FastAPI + SQLAlchemy

**Deployment:** Vercel + Render + Supabase

**Primary Goal:** Strengthen market linkages and improve farmer price discovery and net realization.

---
