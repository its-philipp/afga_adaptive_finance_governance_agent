# AFGA Scripts Guide

## 🚀 **Main Script (Use This!)**

### `./restart.sh`
**The ONE script you need for everything.**

```bash
# Normal restart (preserves database & transactions)
./restart.sh

# Clean restart (deletes database, fresh start for demos)
./restart.sh --clean
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
./restart.sh --clean  # Fresh database, clean audit trails
```

---

## 📜 **Other Scripts (Legacy - Can Delete)**

### `start.sh`
❌ **Don't use** - Can create duplicate processes  
➡️ **Use `./restart.sh` instead**

### `restart_fresh.sh`  
❌ **Don't use** - Doesn't check for duplicates  
➡️ **Use `./restart.sh` instead**

### `force_restart.sh`
❌ **Don't use** - Overly aggressive, no verification  
➡️ **Use `./restart.sh` instead**

### `demo_restart.sh`
❌ **Don't use** - Incomplete database init  
➡️ **Use `./restart.sh --clean` instead**

---

## 🛑 **Manual Stop**

If you ever need to stop AFGA manually:

```bash
# Clean stop using saved PIDs
kill $(cat .backend.pid .frontend.pid 2>/dev/null)

# Or nuclear option
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
./restart.sh  # Preserves DB & transactions
```

**Before demo/presentation:**
```bash
./restart.sh --clean  # Fresh start, clean audit trails
```

**Check logs:**
```bash
tail -f afga_backend.log   # Backend logs
tail -f afga_frontend.log  # Frontend logs
```

---

## 🗑️ **Cleanup Old Scripts**

After testing the new `restart.sh`, you can safely delete:
- `start.sh`
- `restart_fresh.sh`  
- `force_restart.sh`
- `demo_restart.sh`

Keep only:
- ✅ `restart.sh` (the ONE script to rule them all!)

