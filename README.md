# 🥗 CalorieTracker

> An LLM-powered calorie & macro tracking app tailored for **Indian foods**, with voice input, saved meals, workout tracking, and a sleek dark mode UI.

---

## 📸 Features at a Glance

- 🧠 **AI Macro Estimation** — Describe food naturally in plain English; Groq's LLaMA 3.3 70B estimates calories, protein, carbs, and fats per item
- 🎙️ **Voice Transcription** — Record your meal description using your mic; Groq Whisper transcribes it locally (no Google dependency)
- 🍱 **Saved Meals Library** — Pre-save frequently eaten meals with aliases; they bypass the LLM for instant, consistent results
- 🏋️ **Workout Calorie Estimation** — Describe your workout in plain text; the LLM estimates burn using MET values adjusted for your weight
- 📊 **Daily / Weekly / Monthly Tracking** — View deficits, macros, and fat loss estimates across time periods
- ⚖️ **Weight Logging** — Log daily weight and view history trends
- 🌙 **Dark Mode** — Toggle with a button; preference saved across sessions
- 📱 **Mobile-First UI** — Bottom tab navigation, responsive layouts, works great on phones
- 💻 **CLI Interface** — Full terminal interface for power users

---

## 🏗️ Architecture

```
calorie_tracker/
├── app.py              # Flask REST API (port 5000)
├── llm.py              # Groq API: food macros, workout calories, Whisper transcription
├── db.py               # ChromaDB layer: all data storage
├── meals.py            # Saved meals library logic
├── main.py             # CLI entry point
├── .env                # GROQ_API_KEY (not committed)
├── chroma_data/        # ChromaDB persistent storage
└── frontend/
    └── src/
        ├── App.js                  # Router, profile state, dark mode
        ├── App.css                 # Global styles + dark mode + mobile
        └── components/
            ├── Navbar.js           # Top nav (desktop) + bottom tab bar (mobile)
            ├── Home.js             # Dashboard: today's summary + deficit cards
            ├── LogFood.js          # 4-step food logging flow with voice input
            ├── Today.js            # Detailed today view
            ├── Week.js             # 7-day week view
            ├── Reports.js          # Weekly/monthly deficit reports
            ├── Meals.js            # Saved meals library CRUD
            └── Settings.js         # Profile setup (name, BMR)
```

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router v6 |
| Backend | Python Flask, Flask-CORS |
| Database | ChromaDB (vector DB used as key-value store) |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Transcription | Groq Whisper — `whisper-large-v3-turbo` |
| Styling | Vanilla CSS with CSS custom properties |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier is sufficient)

---

### 1. Clone the Repository

```bash
git clone https://github.com/PranavhShetty/Calorie_tracker.git
cd Calorie_tracker
```

---

### 2. Backend Setup

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install flask flask-cors chromadb groq python-dotenv
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Start the Flask server:

```bash
python app.py
```

The API will be available at `http://localhost:5000`.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

The React app will open at `http://localhost:3000`.

---

### 4. First-Time Setup

1. Open `http://localhost:3000` in your browser
2. You'll be redirected to **Settings**
3. Enter your name and **BMR** (Basal Metabolic Rate in kcal/day)
   - Use an online BMR calculator (Mifflin-St Jeor formula recommended)
   - Example: a 25-year-old, 70kg, 175cm male has a BMR of ~1750 kcal/day
4. Save your profile — you're ready to log!

---

## 📱 Using the App

### Logging Food (Step-by-Step)

**Step 1 — Describe what you ate**

Type or speak naturally:
> *"2 rotis with dal makhani and a bowl of curd"*
> *"chicken biryani, raita, and a gulab jamun"*

Press **🎙️ Transcribe** to use your microphone — it records audio locally and sends it to Groq Whisper for transcription. Press **Stop Recording** when done speaking.

**Step 2 — Review Macros**

The LLM breaks your description into individual items with estimated calories, protein, carbs, and fats. Saved meals are matched first (faster, consistent).

**Step 3 — Log Your Workout** *(optional)*

Describe your workout:
> *"gym - chest and triceps 60 min, 15 min treadmill"*

The LLM estimates calories burned using MET values adjusted for your body weight.

**Step 4 — Add Notes & Save**

Add any optional notes and save the day's log.

---

### Saved Meals Library

Pre-save your frequently eaten meals so they skip the LLM entirely:

1. Go to **Meals** tab
2. Click **Add New Meal**
3. Enter the meal name, macros, and **aliases** (alternative names you might use when logging)
4. When you type the meal name or any alias in the food log, it's matched automatically

Example: Save "Protein Shake" with alias "shake" — typing either will use the saved macros.

---

### Dark Mode

Click the **🌙** button in the top-right corner of the navbar. Your preference is saved and restored across sessions. The app also respects your OS dark mode setting on first visit.

---

## 🖥️ CLI Interface

The original command-line interface is still fully functional:

```bash
# Activate virtualenv first
python main.py setup      # Set up your profile
python main.py log        # Log today's food and workout
python main.py status     # View today's summary
python main.py weekly     # View this week's deficit
python main.py monthly    # View this month's deficit
python main.py meals      # Manage saved meals library
```

---

## 🔌 API Reference

All endpoints are prefixed with `/api/`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/profile` | Get user profile |
| `POST` | `/api/save-profile` | Create/update profile |
| `GET` | `/api/home-data` | Dashboard summary data |
| `GET` | `/api/today-data` | Today's food entries + summary |
| `GET` | `/api/week-data` | This week's 7-day data |
| `GET` | `/api/reports-data` | Weekly + monthly report data |
| `POST` | `/api/parse-food` | Parse food description → macros via LLM |
| `POST` | `/api/save-food-log` | Save confirmed food log + workout |
| `POST` | `/api/calculate-workout` | Estimate workout calories via LLM |
| `POST` | `/api/transcribe` | Transcribe audio file via Groq Whisper |
| `GET` | `/api/get-meals` | Get all saved meals |
| `POST` | `/api/save-meal` | Save a new custom meal |
| `POST` | `/api/delete-meal` | Delete a saved meal |
| `GET` | `/api/check-weight-today` | Check if weight was logged today |
| `GET` | `/api/weight-history` | Get weight history (default: 30 days) |

### Example: Parse Food

```bash
curl -X POST http://localhost:5000/api/parse-food \
  -H "Content-Type: application/json" \
  -d '{"food_description": "2 rotis and a bowl of dal"}'
```

```json
{
  "items": [
    {
      "food_name": "2 Rotis (80g)",
      "calories": 240,
      "protein": 8.0,
      "carbs": 48.0,
      "fats": 4.0,
      "notes": "Whole wheat rotis, standard size",
      "is_saved_meal": false
    },
    {
      "food_name": "Dal (1 katori, 150ml)",
      "calories": 150,
      "protein": 9.0,
      "carbs": 20.0,
      "fats": 4.0,
      "notes": "Toor dal, medium consistency",
      "is_saved_meal": false
    }
  ]
}
```

### Example: Transcribe Audio

```bash
curl -X POST http://localhost:5000/api/transcribe \
  -F "audio=@recording.webm"
```

```json
{
  "transcript": "two rotis with chicken curry and a glass of buttermilk"
}
```

---

## 🗃️ Data Model

### Profile
```json
{
  "name": "Pranav",
  "bmr": 1750
}
```

### Food Entry
```json
{
  "date": "2026-03-09",
  "food_name": "Chicken Biryani",
  "calories": 520,
  "protein": 28.5,
  "carbs": 62.0,
  "fats": 14.0,
  "meal_type": "meal",
  "is_saved_meal": false
}
```

### Daily Summary
```json
{
  "date": "2026-03-09",
  "total_calories_in": 1850,
  "total_protein": 120,
  "total_carbs": 210,
  "total_fats": 55,
  "workout_description": "gym - legs 60 min",
  "calories_burned": 320,
  "bmr": 1750,
  "total_burned": 2070,
  "deficit": 220
}
```

### Saved Meal
```json
{
  "label": "Protein Shake",
  "calories": 180,
  "protein": 30,
  "carbs": 8,
  "fats": 3,
  "description": "Whey protein with milk",
  "aliases": ["shake", "whey shake", "protein"]
}
```

---

## 🤖 LLM Details

### Food Macro Estimation
- **Model**: `llama-3.3-70b-versatile` via Groq
- Prompted as an expert Indian nutritionist
- Uses standard Indian portion sizes (katori, plate, piece)
- Returns structured JSON — no free-text parsing needed
- Temperature: 0.3 for consistent results

### Workout Calorie Estimation
- **Model**: `llama-3.3-70b-versatile` via Groq
- Uses MET (Metabolic Equivalent of Task) values
- Formula: `Calories = MET × weight_kg × duration_hours`
- Adjusts for user's body weight

### Voice Transcription
- **Model**: `whisper-large-v3-turbo` via Groq
- Audio captured in browser via `MediaRecorder` API (WebM format)
- Sent to Flask backend, forwarded to Groq's transcription endpoint
- No dependency on Google's servers — works even without Google access
- Free tier: 7,200 seconds/day (2 hours) — more than enough for daily use

---

## 🌙 Dark Mode

Dark mode uses CSS custom properties. Toggling sets `data-theme="dark"` on the `<html>` element:

```css
html[data-theme="dark"] {
  --bg-main: #121212;
  --bg-card: #1E1E1E;
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --border: #374151;
}
```

Preference is saved to `localStorage` and auto-detected from `prefers-color-scheme` on first visit.

---

## 📱 Mobile Support

- **Bottom tab bar** on screens ≤768px (Home, Log, Today, Meals, Settings)
- Safe area insets supported for iOS notch/home bar
- All layouts tested for 375px (iPhone SE) and up
- Touch-friendly button sizes throughout

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Your Groq API key from [console.groq.com](https://console.groq.com) |

---

## 🛠️ Known Limitations

- **No user authentication** — single-user app, designed for personal use
- **No offline mode** — requires internet for LLM and Whisper API calls
- **LLM estimates** — macro values are AI estimates, not nutritionally certified
- **Indian food focus** — LLM is prompted specifically for Indian cuisine; Western foods work but may be less accurate

---

## 📄 License

This project is for personal use. Feel free to fork and adapt it for your own tracking needs.

---

*Built with ❤️ for tracking Indian food macros the smart way.*
