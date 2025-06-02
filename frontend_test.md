# 🚀 Frontend Troubleshooting Guide

## Issue: Can't access http://localhost:3000

Here's a step-by-step guide to get the frontend running:

## **Step 1: Check Current Status**

```bash
# Check if the server is running
ps aux | grep "next dev"

# Check what's using port 3000
lsof -i :3000

# Check if you can connect
curl http://localhost:3000
```

## **Step 2: Clean Start**

```bash
cd legal_discovery_frontend

# Stop any existing processes
pkill -f "next dev"

# Clean everything
rm -rf .next node_modules

# Reinstall dependencies
pnpm install

# Start fresh
pnpm dev
```

## **Step 3: Alternative Port**

If port 3000 is busy, try a different port:

```bash
# Start on port 3001
pnpm dev -- -p 3001

# Then access: http://localhost:3001
```

## **Step 4: Check for Errors**

Look for these common issues:

### **Node.js Version**
```bash
node --version
# Should be 18+ or 20+
```

### **Network Issues**
```bash
# Try starting with specific host
pnpm dev -- --hostname 127.0.0.1

# Or try
pnpm dev -- --hostname 0.0.0.0
```

### **Firewall/Security**
- Check if your firewall is blocking port 3000
- Try disabling firewall temporarily
- On macOS: System Preferences > Security & Privacy > Firewall

## **Step 5: Simplified Test Version**

If still having issues, let's create a minimal test:

```bash
# Create a simple test page
echo 'export default function Test() { return <div>Hello World!</div> }' > src/app/test/page.tsx

# Try accessing: http://localhost:3000/test
```

## **Step 6: Browser Issues**

Try these:
- **Different browser** (Chrome, Firefox, Safari)
- **Incognito/Private mode**
- **Clear browser cache**
- **Disable browser extensions**

## **Step 7: System-specific Fixes**

### **macOS:**
```bash
# Reset DNS
sudo dscacheutil -flushcache

# Check hosts file
cat /etc/hosts | grep localhost
```

### **Network Reset:**
```bash
# Restart network (if needed)
sudo ifconfig en0 down && sudo ifconfig en0 up
```

## **Expected Output When Working**

When `pnpm dev` is successful, you should see:

```
▲ Next.js 15.0.0
- Local:        http://localhost:3000

✓ Starting...
✓ Ready in 1051ms
```

And the browser should show the Legal Discovery dashboard.

## **Alternative: Direct File Access**

If network access fails, you can build and serve statically:

```bash
pnpm build
pnpm start
# This serves on http://localhost:3000
```

## **Last Resort: Manual Check**

```bash
# Check if the files exist
ls -la src/app/
ls -la src/components/

# Verify build works
pnpm build
```

Try these steps in order and let me know where it fails!