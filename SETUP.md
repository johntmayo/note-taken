# Note Taken — Setup Guide

## 1. Supabase Setup

1. Go to [supabase.com](https://supabase.com) and open your project (or create one).
2. In the left sidebar, click **SQL Editor**.
3. Create a new query and paste this:

```sql
CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  content TEXT NOT NULL
);

-- Optional: disable RLS for this personal app (no auth)
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for notes" ON notes
  FOR ALL
  USING (true)
  WITH CHECK (true);
```

4. Click **Run**.

5. Get your credentials:
   - Go to **Project Settings** → **API**
   - Copy **Project URL**
   - Copy **service_role** key (under "Project API keys") — this stays server-side only

---

## 2. Local Development

1. Install dependencies:
   ```
   python -m pip install -r requirements.txt
   ```

2. Create `.streamlit/secrets.toml` (copy from `secrets.toml.example` and fill in your values):

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_SERVICE_KEY = "eyJ..."
   ```

3. Run the app:
   ```
   streamlit run app.py
   ```

---

## 3. Deploy to Streamlit Cloud

1. Push this repo to GitHub (make sure `.gitignore` excludes `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. Create a new app → select this repo, main branch, `app.py`.
4. Before deploying, click **Advanced settings** and add Secrets:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   SUPABASE_URL = "https://xxxxx.supabase.co"
   SUPABASE_SERVICE_KEY = "eyJ..."
   ```

5. Deploy.

---

## Workflow

- **Phone**: Open the app URL → take a photo → transcribe → note is saved.
- **Computer**: Open the same URL → see your notes list → copy into docs, AI agents, etc.
