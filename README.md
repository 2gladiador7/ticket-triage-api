# Ticket Triage API

A production-ready REST API that classifies support tickets using Claude Haiku.

## Endpoint

### `POST /triage`

**Headers**
```
Authorization: Bearer <your-API_KEY>
Content-Type: application/json
```

**Request body**
```json
{
  "ticket": "I can't log in — my account is locked after a failed payment.",
  "categories": ["billing", "technical", "account", "feature-request", "general"]
}
```
`categories` is optional; defaults to the five values shown above.

**Response**
```json
{
  "category": "account",
  "priority": "high",
  "sentiment": "frustrated",
  "response_type": "account_access",
  "summary": "Customer locked out after failed payment and needs account restored."
}
```

**Error codes**

| Code | Meaning |
|------|---------|
| 400  | Malformed request body (missing `ticket`, wrong types) |
| 401  | Missing or invalid `Authorization` header |
| 502  | Anthropic API error |

---

## Local development

```bash
# 1. Clone / cd into the project
cp .env.example .env          # fill in your keys

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload

# 5. Test
curl -X POST http://localhost:8000/triage \
  -H "Authorization: Bearer your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"ticket": "My invoice is wrong and I was charged twice!"}'
```

Interactive docs available at `http://localhost:8000/docs`.

---

## Deploy to Railway

### Prerequisites
- [Railway account](https://railway.app)
- Railway CLI (`npm i -g @railway/cli`) **or** just use the Railway dashboard

### Steps

**1. Push your code to GitHub**

```bash
git init
git add .
git commit -m "Initial commit"
# create a GitHub repo, then:
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

**2. Create a new Railway project**

Go to [railway.app/new](https://railway.app/new) → **Deploy from GitHub repo** → select your repo.

Railway auto-detects Python and runs `pip install -r requirements.txt`.

**3. Set the start command**

In Railway → your service → **Settings** → **Deploy** → **Start Command**:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Railway injects `$PORT` automatically.

**4. Add environment variables**

Railway → your service → **Variables** → add:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | your Anthropic key (`sk-ant-…`) |
| `API_KEY` | any secret string callers must send as `Bearer` token |

**5. Deploy**

Railway triggers a deploy automatically on every `git push`. You'll see the public URL (e.g. `https://ticket-triage-api.up.railway.app`) in the Railway dashboard once it's live.

**6. Verify**

```bash
curl -X POST https://<your-railway-url>/triage \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"ticket": "I was billed twice this month."}'
```

---

## Environment variables reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `API_KEY` | Yes | Secret token callers use in `Authorization: Bearer` |
