# 🚀 Legal Discovery Platform - Quick Start Guide

## **The Issue You're Experiencing**

If you can't access `http://localhost:3000`, here are the most common causes and solutions:

### **Quick Diagnosis**
```bash
# Check if anything is using port 3000
lsof -i :3000

# Check if Next.js is running
ps aux | grep "next dev"

# Test port connectivity
curl http://localhost:3000
```

---

## **🎯 Fastest Way to Get Running**

### **Option 1: Use the Automated Scripts**

```bash
# Terminal 1 - Start Backend
./start_backend.sh

# Terminal 2 - Start Frontend  
./start_frontend.sh
```

### **Option 2: Manual Step-by-Step**

#### **Backend (Terminal 1):**
```bash
cd legal_discovery_backend

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### **Frontend (Terminal 2):**
```bash
cd legal_discovery_frontend

# Install dependencies
pnpm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Try different approaches:

# Method 1: Standard start
pnpm dev

# Method 2: Different port if 3000 is busy
pnpm dev -p 3001

# Method 3: Bind to all interfaces
pnpm dev -H 0.0.0.0

# Method 4: Production build (more stable)
pnpm build && pnpm start
```

---

## **🔧 Common Issues & Solutions**

### **Issue 1: Port 3000 Already in Use**
```bash
# Find what's using the port
lsof -i :3000

# Kill the process (replace PID with actual process ID)
kill -9 <PID>

# Or use a different port
pnpm dev -p 3001
# Then access: http://localhost:3001
```

### **Issue 2: Node.js/pnpm Issues**
```bash
# Check versions
node --version  # Should be 18+
pnpm --version

# If pnpm not installed
npm install -g pnpm

# Clean and reinstall
rm -rf node_modules .next
pnpm install
```

### **Issue 3: Firewall/Network Issues**
- **macOS**: System Preferences > Security & Privacy > Firewall
- **Windows**: Windows Defender Firewall
- Try different browsers (Chrome, Firefox, Safari)
- Try incognito/private mode

### **Issue 4: Browser Cache Issues**
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Clear browser cache
- Try incognito/private mode

---

## **🧪 Test if Frontend is Working**

### **Method 1: Test Page**
If the main app doesn't load, try: `http://localhost:3000/test`

This should show a simple "Frontend Test Page" if Next.js is working.

### **Method 2: Check Build Process**
```bash
cd legal_discovery_frontend

# Test if build works
pnpm build

# If build succeeds, the frontend code is fine
# If build fails, there are code issues to fix
```

### **Method 3: Minimal Server Test**
```bash
# Create a super simple test
echo 'export default function() { return <h1>Hello World</h1> }' > src/app/simple/page.tsx

# Try accessing: http://localhost:3000/simple
```

---

## **📋 Verification Checklist**

When everything is working, you should see:

### **Backend (http://localhost:8000):**
- ✅ Health check responds: `{"status":"healthy"}`
- ✅ API docs load at: `/docs`
- ✅ No error messages in terminal

### **Frontend (http://localhost:3000):**
- ✅ Legal Discovery dashboard loads
- ✅ Professional UI with cases list
- ✅ "New Case" button visible
- ✅ No errors in browser console (F12)

---

## **🚨 If Still Not Working**

### **Last Resort Options:**

1. **Try Production Build:**
   ```bash
   cd legal_discovery_frontend
   pnpm build
   pnpm start
   ```

2. **Try Different Browsers:**
   - Chrome
   - Firefox  
   - Safari
   - Edge

3. **Network Debugging:**
   ```bash
   # Check network interfaces
   ifconfig | grep inet
   
   # Try binding to specific IP
   pnpm dev -H 127.0.0.1
   ```

4. **Alternative Access Methods:**
   - Try `http://127.0.0.1:3000`
   - Try your computer's IP address: `http://192.168.1.xxx:3000`

---

## **💡 Pro Tips**

### **For Development:**
- Keep both terminals open (backend + frontend)
- Backend must be running for frontend to work properly
- Check both terminal windows for error messages

### **For Testing:**
- Use `http://localhost:8000/docs` to test backend APIs directly
- Use browser dev tools (F12) to check for frontend errors
- Test the simple `/test` page first before the full app

---

## **🔄 Quick Restart Process**

If something breaks, here's the fastest recovery:

```bash
# Kill everything
pkill -f "next dev"
pkill -f "uvicorn"

# Restart backend
cd legal_discovery_backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 &

# Restart frontend
cd ../legal_discovery_frontend
pnpm dev &

# Check status
curl http://localhost:8000/health
curl http://localhost:3000/test
```

**The frontend should now be accessible! 🎉**