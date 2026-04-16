# WorkForce Portal — Deployment Guide

A full-stack HR & Employee Management Portal built with React + Supabase.

---

## ✅ What's included

- Login / Signup with Supabase Auth
- Employee directory (add, edit, delete, filter)
- Attendance management (daily marking, logs)
- Leave management (apply, approve, reject)
- Payroll register (auto PF + TDS calculation)
- Expense claims (submit, approve, reject)
- Performance reviews (ratings, goals, notes)
- Notifications (with unread badges)
- Company settings

All data is stored in your Supabase PostgreSQL database — fully persistent.

---

## 🚀 Step 1: Set up Supabase (FREE)

1. Go to **https://supabase.com** and click **Start your project**
2. Sign up (free) → Click **New project**
3. Give it a name (e.g. `workforce-portal`) and a strong database password
4. Wait ~2 minutes for the project to be ready
5. Go to **SQL Editor** (left sidebar)
6. Click **New query**
7. Copy the entire contents of `supabase_schema.sql` and paste it → click **Run**
8. You should see: "Success. No rows returned"

Now go to **Settings → API**:
- Copy **Project URL** (looks like `https://abcdef.supabase.co`)
- Copy **anon public** key (a long JWT string)

---

## ⚙️ Step 2: Configure the app

1. Rename `.env.example` to `.env`
2. Open `.env` and fill in your values:

```
REACT_APP_SUPABASE_URL=https://your-project-id.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-public-key-here
```

---

## 💻 Step 3: Run locally

Make sure you have **Node.js 16+** installed (https://nodejs.org).

```bash
# Install dependencies
npm install

# Start the app
npm start
```

Open http://localhost:3000 in your browser.

**First time:** Click "Sign up" to create your admin account using your email + password.
Supabase will send a confirmation email — click the link, then sign in.

---

## 🌐 Step 4: Deploy to Vercel (FREE, takes 2 minutes)

1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   # Create a repo on github.com, then:
   git remote add origin https://github.com/YOUR_USERNAME/workforce-portal.git
   git push -u origin main
   ```

2. Go to **https://vercel.com** → Sign up with GitHub → **New Project**
3. Import your GitHub repository
4. Under **Environment Variables**, add:
   - `REACT_APP_SUPABASE_URL` = your Supabase URL
   - `REACT_APP_SUPABASE_ANON_KEY` = your anon key
5. Click **Deploy** → Done!

Vercel gives you a free URL like `https://workforce-portal.vercel.app`

---

## 🔒 Step 5: Allow your site URL in Supabase

1. In Supabase → **Authentication → URL Configuration**
2. Under **Site URL**, add your Vercel URL: `https://workforce-portal.vercel.app`
3. Under **Redirect URLs**, add: `https://workforce-portal.vercel.app/**`

---

## 💰 Cost summary

| Service | Free tier | Paid |
|---------|-----------|------|
| Supabase | 500MB DB, unlimited auth | $25/mo |
| Vercel | Unlimited deploys, custom domain | $20/mo |
| Domain | — | ~₹800/year |

**For a small company (~50 employees), the free tier is plenty.**

---

## 📁 File structure

```
workforce-portal/
├── public/
│   └── index.html
├── src/
│   ├── lib/
│   │   └── supabase.js       ← Supabase client
│   ├── App.js                ← All pages & components
│   ├── App.css               ← All styles
│   └── index.js              ← React entry point
├── supabase_schema.sql       ← Run this in Supabase SQL Editor
├── .env.example              ← Rename to .env and fill in keys
├── package.json
└── README.md
```

---

## 🛠 Need help?

Common issues:
- **"relation does not exist"** → Run the SQL schema in Supabase again
- **Blank screen** → Check `.env` file has correct keys, no extra spaces
- **Can't sign in** → Check Supabase Auth → Confirm email in your inbox
