# ☁️ QuantForge Telegram AI Bot — GitHub & Cloud Hosting Guide

This guide explains how your Telegram Two-Way Interactive AI Quant Bot (`@bamquantforgebot`) is hosted and run directly via GitHub so you don't need your laptop open.

---

## 1. 🚀 GitHub Actions Cloud Runner (Automated)

We have created an automated GitHub Actions workflow:
- **Path:** `.github/workflows/telegram_ai_bot.yml`
- **What it does:** Runs the Telegram AI assistant in the GitHub Cloud runner for up to 6 hours per job cycle, restarting automatically.
- **How to trigger manually:**
  1. Open your repository on GitHub: `https://github.com/BamBosco/quantforge`
  2. Click on the **Actions** tab.
  3. Select **"Telegram AI Bot Cloud Runner"** on the left menu.
  4. Click **"Run workflow"** → **"Run workflow"**.

---

## 2. 🔐 Adding GitHub Secrets (Optional / Recommended)

To securely configure your credentials in GitHub:
1. Go to your repo **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret**:
   - `TELEGRAM_BOT_TOKEN`: `8610958249:AAE7U8peL4WPVBiz95nBZiw2aGIAT0Fw31o`
   - `TELEGRAM_CHAT_ID`: `5386759666`

---

## 3. 🌐 24/7 Dedicated Cloud Hosting (1-Click via GitHub)

If you want a 100% free, 24/7/365 always-on container connected directly to this GitHub repo:

### Option A: Railway (Free / Cheap Cloud)
1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub repo"** → Select `BamBosco/quantforge`.
3. In settings, set Dockerfile path to `Dockerfile.telegram_bot`.
4. Add environment variables `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
5. Click **Deploy**! It will stay online 24/7.

### Option B: Render.com
1. Go to [render.com](https://render.com) and create a free **Background Worker**.
2. Connect your `quantforge` GitHub repository.
3. Select `Dockerfile.telegram_bot` and deploy.
