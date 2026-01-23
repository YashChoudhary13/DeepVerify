# 🔧 CORS Configuration Fix

## Problem
Frontend cannot connect to backend - likely CORS issue.

## Solution: Update Railway Environment Variables

Go to **Railway Dashboard** → Your Project → **Variables** tab

### Required Variables:

```env
FRONTEND_URL=https://frontend-tau-sage-99.vercel.app
FRONTEND_ORIGINS=https://frontend-tau-sage-99.vercel.app,http://localhost:3000
```

⚠️ **IMPORTANT:** 
- NO trailing slashes in URLs
- Use comma-separated values (no spaces)
- Include BOTH production and localhost

### After updating:
1. Railway will auto-redeploy (~2 minutes)
2. Visit: https://frontend-tau-sage-99.vercel.app/diagnostic
3. Should show "Backend Connection: success"

## Verify CORS is Working

### Test 1: Direct Backend Health Check
```bash
curl https://deepfakedetection-production-ab9b.up.railway.app/health
```
Should return: `{"status":"healthy",...}`

### Test 2: From Browser Console
1. Visit: https://frontend-tau-sage-99.vercel.app
2. Open browser DevTools (F12)
3. Go to Console tab
4. Run:
```javascript
fetch('https://deepfakedetection-production-ab9b.up.railway.app/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

**If you see CORS error:**
- Check Railway `FRONTEND_ORIGINS` includes your Vercel URL
- Restart Railway deployment after updating

**If you see network error:**
- Backend might be down - check Railway logs
- Check API URL in Vercel environment variables

## Quick Fix Commands

### Redeploy Frontend with Diagnostic Page:
```bash
cd frontend
vercel --prod
```

Then visit: https://frontend-tau-sage-99.vercel.app/diagnostic

### Check Railway Logs:
Go to Railway Dashboard → Your Project → Deployments → View Logs

Look for:
```
allow_origins=['https://frontend-tau-sage-99.vercel.app', 'http://localhost:3000']
```

---

## Current Configuration

**Frontend (Vercel):**
- URL: https://frontend-tau-sage-99.vercel.app
- Env: `NEXT_PUBLIC_API_URL=https://deepfakedetection-production-ab9b.up.railway.app`

**Backend (Railway):**
- URL: https://deepfakedetection-production-ab9b.up.railway.app
- Needs: `FRONTEND_ORIGINS=https://frontend-tau-sage-99.vercel.app,http://localhost:3000`

---

## Still Not Working?

1. **Check Railway Variables are EXACTLY:**
   ```
   FRONTEND_ORIGINS=https://frontend-tau-sage-99.vercel.app,http://localhost:3000
   ```
   (No quotes, no spaces around comma)

2. **Verify Vercel Env Var:**
   ```bash
   vercel env pull
   cat .env.local
   ```

3. **Force Redeploy Both:**
   ```bash
   # Redeploy backend
   git commit --allow-empty -m "Force Railway redeploy"
   git push origin main
   
   # Redeploy frontend
   cd frontend
   vercel --prod
   ```
