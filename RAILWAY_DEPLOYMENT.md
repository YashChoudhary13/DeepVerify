# 🚂 Railway Deployment Guide

## Prerequisites
- ✅ Railway account (https://railway.app)
- ✅ GitHub account with your code pushed
- ✅ Models uploaded to Cloudflare R2 (or accessible URL)

---

## 📋 Step-by-Step Deployment

### **Step 1: Upload Models to Cloudflare R2**

1. Go to Cloudflare R2 Dashboard
2. Create a folder called `models` in your bucket
3. Upload these 4 files:
   - `efficientnet_b0_deepfake.h5`
   - `mobilenetv2_deepfake.h5`
   - `resnet50_deepfake.h5`
   - `xception_deepfake.h5`

4. Make them publicly accessible:
   - Bucket Settings → Public Access → Enable
   - Or use R2 Custom Domain

5. Get the URLs (example):
   ```
   https://pub-xxxx.r2.dev/models/efficientnet_b0_deepfake.h5
   https://pub-xxxx.r2.dev/models/mobilenetv2_deepfake.h5
   https://pub-xxxx.r2.dev/models/resnet50_deepfake.h5
   https://pub-xxxx.r2.dev/models/xception_deepfake.h5
   ```

---

### **Step 2: Push to GitHub**

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

---

### **Step 3: Create Railway Project**

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize GitHub if needed
5. Select your `DeepFakeDetection` repository
6. Railway will detect the Dockerfile automatically

---

### **Step 4: Configure Environment Variables**

In Railway Project → Variables tab, add these:

#### **Required:**
```env
DATABASE_URL=postgresql+psycopg2://postgres.xxx@xxx.supabase.co:5432/postgres?sslmode=require
SUPABASE_URL=https://xxx.supabase.co
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=(leave empty for now)
```

#### **Model URLs (from Step 1):**
```env
MODEL_EFFICIENTNET_URL=https://your-r2-url.r2.dev/models/efficientnet_b0_deepfake.h5
MODEL_MOBILENET_URL=https://your-r2-url.r2.dev/models/mobilenetv2_deepfake.h5
MODEL_RESNET_URL=https://your-r2-url.r2.dev/models/resnet50_deepfake.h5
MODEL_XCEPTION_URL=https://your-r2-url.r2.dev/models/xception_deepfake.h5
```

#### **Cloudflare R2:**
```env
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=deepfake-images
R2_PUBLIC_URL=https://pub-xxxx.r2.dev
```

#### **CORS & Frontend:**
```env
FRONTEND_URL=https://your-app.vercel.app
FRONTEND_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

#### **Storage (Optional - adjust retention):**
```env
UPLOAD_RETENTION_HOURS=6
HEATMAP_RETENTION_HOURS=24
REVERSE_IMAGE_RETENTION_HOURS=2
```

---

### **Step 5: Configure Railway Settings**

1. Go to **Settings** tab
2. **Root Directory**: Set to `backend` (or leave empty if backend is at root)
3. **Start Command**: Should auto-detect from railway.toml
4. **Health Check Path**: `/health`
5. **Port**: Railway auto-assigns (uses $PORT)

---

### **Step 6: Deploy**

1. Railway will start building automatically
2. Watch the logs in **Deployments** tab
3. Look for:
   ```
   ⬇️  Downloading models...
   ✅ Downloaded: efficientnet_b0_deepfake.h5
   ✅ Downloaded: mobilenetv2_deepfake.h5
   ✅ Downloaded: resnet50_deepfake.h5
   ✅ Downloaded: xception_deepfake.h5
   ✅ ALL MODELS READY
   ```

4. After successful deployment, Railway gives you a URL:
   ```
   https://your-project.up.railway.app
   ```

---

### **Step 7: Test Your Deployment**

Test the health check:
```bash
curl https://your-project.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T...",
  "service": "DeepVerify API"
}
```

---

### **Step 8: Setup Stripe Webhook**

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-project.up.railway.app/api/stripe-webhook`
3. Select event: `checkout.session.completed`
4. Copy the webhook signing secret
5. Add to Railway env vars: `STRIPE_WEBHOOK_SECRET=whsec_xxx`
6. Redeploy (Railway auto-redeploys on env change)

---

### **Step 9: Update Frontend**

In Vercel (or your frontend host), update:
```env
NEXT_PUBLIC_API_URL=https://your-project.up.railway.app
```

---

## 🔧 Troubleshooting

### Models Not Downloading?
Check logs for download errors:
```bash
railway logs
```

Solutions:
- ✅ Verify R2 URLs are publicly accessible
- ✅ Check MODEL_*_URL env vars are set
- ✅ Ensure R2 bucket has public read access

### Out of Memory?
- ✅ Upgrade Railway plan (default is 512MB)
- ✅ Models need ~2-3GB to load
- ✅ Minimum: 4GB RAM recommended

### Database Connection Issues?
- ✅ Check DATABASE_URL format
- ✅ Ensure Supabase allows Railway IPs
- ✅ Verify `?sslmode=require` in connection string

### CORS Errors?
- ✅ Set FRONTEND_ORIGINS with your Vercel URL
- ✅ No trailing slashes in URLs
- ✅ Include both production and localhost for testing

---

## 💰 Railway Pricing

**Recommended Plan for Your App:**
- **Starter Plan**: $5/month (500 MB RAM) - ⚠️ Too small
- **Developer Plan**: $10/month (8 GB RAM) - ✅ Good for testing
- **Hobby Plan**: $20/month (32 GB RAM) - ✅ Recommended

Models + app need ~3-4GB RAM minimum.

---

## 📊 Monitoring

### Check Storage Usage:
```bash
curl https://your-project.up.railway.app/api/admin/storage-info
```

### Manual Cleanup:
```bash
curl -X POST https://your-project.up.railway.app/api/admin/cleanup
```

### View Logs:
```bash
railway logs --follow
```

Or in Railway Dashboard → Deployments → Click deployment → View Logs

---

## 🔄 Updates & Redeployment

Railway auto-deploys on git push:
```bash
git add .
git commit -m "Update backend"
git push origin main
```

Railway detects changes and redeploys automatically!

---

## ✅ Deployment Checklist

- [ ] Models uploaded to R2 and publicly accessible
- [ ] GitHub repo pushed with latest code
- [ ] Railway project created
- [ ] All environment variables set (especially model URLs)
- [ ] Backend deployed successfully
- [ ] Models downloaded (check logs)
- [ ] Health check returns 200
- [ ] Stripe webhook configured
- [ ] Frontend updated with Railway URL
- [ ] Test image upload & analysis
- [ ] Test payment flow
- [ ] Monitor logs for errors

---

## 🚀 Next Steps

1. **Custom Domain** (Optional):
   - Railway Settings → Domains → Add Custom Domain
   - Example: `api.yourapp.com`

2. **Set up monitoring**:
   - Railway has built-in metrics
   - Or use external: Sentry, LogRocket

3. **Scale up** as needed:
   - Railway Settings → Resources → Adjust RAM/CPU

---

## 📞 Support

If deployment fails:
1. Check Railway logs: `railway logs`
2. Check build logs in Railway dashboard
3. Verify all env vars are set
4. Test model URLs in browser
5. Check Railway Discord/community

Good luck! 🎉
