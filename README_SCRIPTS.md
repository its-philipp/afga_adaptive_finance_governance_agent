# AFGA Scripts Guide

## 🚀 **Main Scripts**

### `./start.sh`
**Start or restart AFGA with smart process management.**

```bash
# Normal start (preserves database & transactions)
./start.sh

# Clean start (deletes database, fresh start for demos)
./start.sh --clean
```

**What it does:**
1. ✅ Detects and kills ALL existing AFGA processes
2. ✅ **Verifies only ONE instance of each service starts**
3. ✅ Clears Python bytecode cache
4. ✅ Initializes database
5. ✅ Starts backend WITHOUT --reload (prevents duplicate processes)
6. ✅ Starts frontend
7. ✅ Saves PIDs for clean shutdown later

**Before CTO Demo:**
```bash
./start.sh --clean  # Fresh database, clean audit trails
```

### `./stop.sh`
**Stop AFGA cleanly.**

```bash
./stop.sh
```

Stops both frontend and backend gracefully using saved PIDs. If PIDs are missing, searches for and kills AFGA processes.

---

## 📜 **Workflow Examples**

### Normal Development
```bash
./start.sh          # Start AFGA
# ... make code changes ...
./stop.sh           # Stop when done
./start.sh          # Restart with preserved data
```

### Demo/Presentation Prep
```bash
./start.sh --clean  # Fresh database, clean audit trails
# ... do demo ...
./stop.sh           # Clean shutdown
```

### Quick Restart
```bash
./stop.sh && ./start.sh  # Stop and restart
```

---

## 🛑 **Manual Stop (Emergency)**

If scripts don't work:

```bash
# Try PID-based stop first
kill $(cat .backend.pid .frontend.pid 2>/dev/null)

# Nuclear option (kills ALL Python processes!)
pkill -9 -f "streamlit run"
pkill -9 -f "uvicorn.*8000"
```

---

## 🐛 **Debugging**

Check if duplicate processes are running:

```bash
# Check Streamlit
pgrep -af "streamlit run"

# Check Uvicorn  
pgrep -af "uvicorn.*8000"

# Check port 8000
lsof -i :8000
```

If you see **more than ONE of each**, run `./restart.sh` to fix it!

---

## 🎯 **Why Multiple Processes Happened**

**Root Causes:**
1. **`uvicorn --reload`** creates parent + worker processes
2. **Background jobs (`&`)** without PID tracking
3. **Incomplete kills** - `pkill` doesn't always catch child processes
4. **Rapid restart attempts** - New processes started before old ones fully died

**Our Fix:**
- ✅ Remove `--reload` (not needed for production)
- ✅ Save PIDs to files for tracked shutdown
- ✅ Verify process counts before/after
- ✅ Force kill with -9 and wait for confirmation

---

## 💡 **Development Workflow**

**During development:**
```bash
# Make code changes...
./start.sh  # Preserves DB & transactions
```

**Before demo/presentation:**
```bash
./start.sh --clean  # Fresh start, clean audit trails
```

**Check logs:**
```bash
tail -f afga_backend.log   # Backend logs
tail -f afga_frontend.log  # Frontend logs
```

---

## ✅ **Current Scripts**

You have two simple scripts:
- ✅ `start.sh` - Start/restart AFGA
- ✅ `stop.sh` - Stop AFGA cleanly

All legacy scripts have been removed.

