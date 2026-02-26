# Quantsail Bot — Setup Guide (Windows)

This guide will walk you through setting up and running the Quantsail trading bot dashboard on your Windows computer **from scratch**. No prior programming experience is needed — just follow each step carefully.

---

## What You'll Be Installing

| Tool | What It Does |
|------|-------------|
| **Git** | Downloads the project code from GitHub |
| **VS Code** | A text editor where you'll run commands |
| **Node.js** | Runs the dashboard (the website you'll see in your browser) |
| **pnpm** | Installs the dashboard's dependencies |
| **Python** | Runs the trading engine and API server |
| **uv** | Installs Python dependencies quickly |
| **Docker Desktop** | Runs the database and cache (Postgres & Redis) |

---

## Step 1: Install Git

Git lets you download ("clone") the project code from GitHub.

1. Go to: **https://git-scm.com/download/win**
2. Click the **"Click here to download"** button for the latest version.
3. Run the installer. **Use all the default options** — just keep clicking "Next" and then "Install".
4. Once installed, open the **Start Menu**, type `PowerShell`, and click **Windows PowerShell**.
5. Type the following command and press **Enter**:

```
git --version
```

You should see something like `git version 2.47.1`. If you see this, Git is installed correctly. You can close this window.

---

## Step 2: Install VS Code

VS Code is where you'll open the project and run commands.

1. Go to: **https://code.visualstudio.com/download**
2. Click the big blue **"Download for Windows"** button.
3. Run the installer. **Check all the boxes** during installation, especially:
   - ✅ "Add to PATH"
   - ✅ "Register Code as an editor for supported file types"
   - ✅ "Add Open with Code action to Windows Explorer"
4. Click "Install", then "Finish".

---

## Step 3: Install Node.js

Node.js runs the dashboard website.

1. Go to: **https://nodejs.org/en/download**
2. Download the **LTS** version (the one that says "Recommended For Most Users").
3. Run the installer. **Use all the default options**. Make sure to leave the checkbox checked that says **"Automatically install the necessary tools"**.
4. To verify it worked, open a **new PowerShell** window (important — must be a new window) and type:

```
node --version
```

You should see something like `v22.14.0` or higher.

---

## Step 4: Install pnpm

pnpm installs the dashboard's code libraries.

1. Open PowerShell (or reuse the one from Step 3).
2. Type the following command and press **Enter**:

```
npm install -g pnpm
```

3. Wait for it to finish. Then verify by typing:

```
pnpm --version
```

You should see a version number like `9.15.0` or higher.

---

## Step 5: Install Python

Python runs the trading engine and the API backend.

1. Go to: **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python 3.1x.x"** button.
3. **IMPORTANT**: On the first screen of the installer, check the box at the bottom that says:
   ✅ **"Add Python to PATH"**
4. Then click **"Install Now"**.
5. Once installed, open a **new PowerShell** window and type:

```
python --version
```

You should see something like `Python 3.13.2` or higher.

---

## Step 6: Install uv

uv is a fast Python package manager that installs the backend dependencies.

1. Open PowerShell and run:

```
pip install uv
```

2. Wait for it to finish. Then verify:

```
uv --version
```

You should see a version number.

---

## Step 7: Install Docker Desktop

Docker runs the database (Postgres) and cache (Redis) that the bot uses.

1. Go to: **https://www.docker.com/products/docker-desktop/**
2. Click **"Download for Windows"**.
3. Run the installer. Use all default options.
4. **Restart your computer** when prompted.
5. After restart, Docker Desktop should start automatically. Look for the **whale icon** 🐳 in your system tray (bottom-right corner of your screen, near the clock).
6. If Docker asks you to enable WSL 2, click **"Yes"** and follow the prompts.
7. Wait until the Docker Desktop window shows **"Docker Desktop is running"** (the whale icon should stop animating).

> **Note:** Docker may take 1-2 minutes to fully start up after your computer restarts. Wait for the whale icon to be steady before proceeding.

---

## Step 8: Download the Project Code

Now you'll download the Quantsail project from GitHub.

1. Open **VS Code**.
2. Click **Terminal** in the top menu bar, then click **New Terminal**. A terminal panel will appear at the bottom of VS Code.
3. In the terminal, type the following command to navigate to your Desktop:

```
cd "$HOME\Desktop"
```

4. Now clone (download) the project by typing:

```
git clone https://github.com/riverahendrick/quantsail-bot.git
```

5. Wait for the download to complete. You should see a new folder called `quantsail-bot` on your Desktop.

6. Now navigate into the project folder:

```
cd quantsail-bot
```

---

## Step 9: Install Dashboard Dependencies

Before running the dashboard, you need to install its code libraries.

1. In the same VS Code terminal, navigate to the dashboard folder:

```
cd apps\dashboard
```

2. Install the dependencies:

```
pnpm install
```

3. Wait for the installation to finish (this may take 1-2 minutes). You'll see a progress bar.

4. Go back to the main project folder:

```
cd ..\..
```

---

## Step 10: Start Everything

Now you're ready to start all the services! Make sure **Docker Desktop is running** (check for the whale icon 🐳 in your system tray).

1. In the VS Code terminal (make sure you're in the `quantsail-bot` folder), run:

```
powershell -ExecutionPolicy Bypass -File .\start-all.ps1 -SkipInfraCheck
```

> **What does this do?** This script starts three things:
> - The **FastAPI Backend** (the API server)
> - The **Trading Engine** (the bot logic)
> - The **Next.js Dashboard** (the website you'll see)

2. Three new PowerShell windows will pop up — this is normal! Each one runs a different service.

3. Wait about 30 seconds for everything to start up.

---

## Step 11: Open the Dashboards

Once everything is running, open your web browser (Chrome, Edge, etc.) and visit these URLs:

### 🔒 Private Operator Dashboard (Admin View)

```
http://localhost:3000/app/overview
```

This is the **admin panel** where the operator monitors and controls the trading bot. Pages include:
- **Overview** — live status, equity, P&L, open positions
- **Strategy** — current trading strategies and parameters
- **Risk** — circuit breakers, drawdown limits, safety controls
- **Exchange** — exchange connection status
- **Events** — event log / journal
- **Users** — user management

To see all private pages, use the **sidebar navigation** on the left.

---

### 🌐 Public Transparency Dashboard (Investor/User View)

```
http://localhost:3000/public/overview
```

This is the **public-facing dashboard** that investors or users would see. It shows sanitized, transparent performance data without exposing any sensitive information. Pages include:
- **Overview** — live bot status, KPIs, equity chart
- **Trades** — recent trade history
- **Transparency** — security and transparency information

---

## Stopping the Services

When you're done looking at the dashboards and want to stop everything:

1. Close the three PowerShell windows that opened when you started the services.
2. To stop Docker's database and cache, open a PowerShell window and run:

```
cd "$HOME\Desktop\quantsail-bot\infra\docker"
```

```
docker compose down
```

---

## Troubleshooting

### "The term 'pnpm' is not recognized"
Close all PowerShell/VS Code windows and reopen them. The PATH needs to refresh after installing Node.js and pnpm.

### "Docker is not running"
Make sure Docker Desktop is open and the whale icon (🐳) in your system tray is steady (not animating). If Docker asks about WSL 2, accept and follow the prompts.

### "Port 3000 is already in use"
Another program is using port 3000. Close any other dev servers or applications, then try again.

### Dashboard shows "Connection refused" or blank data
The backend API may still be starting. Wait 30 seconds and refresh the page. Make sure the FastAPI window shows it's running (you should see log output).

### "Execution policy" error when running the startup script
Run this command first to allow the script:
```
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```
Then try running the startup script again.

---

## Quick Reference

| Service | URL |
|---------|-----|
| Admin Dashboard | http://localhost:3000/app/overview |
| Public Dashboard | http://localhost:3000/public/overview |
| API Documentation | http://localhost:8000/docs |
| API Health Check | http://localhost:8000/v1/health |
