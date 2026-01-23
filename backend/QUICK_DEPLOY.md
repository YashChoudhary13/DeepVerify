# 🚀 Quick Railway Deployment

## ⚡ Fast Track (5 Minutes)

### 1️⃣ Upload Models to R2
- Go to Cloudflare R2 → Your bucket → Create `models` folder
- Upload 4 .h5 files from `backend/models/`
- Make public or enable custom domain
- Copy the public URLs

### 2️⃣ Push to GitHub
```bash
cd z:\Projects\DeepFakeDetection
git add .
git commit -m "Ready for Railway"
git push
```

### 3️⃣ Railway Setup
1. **Create Project**: https://railway.app → New Project → Deploy from GitHub
2. **Select Repo**: DeepFakeDetection
3. **Root Directory**: `backend` (if not at root, otherwise leave empty)

### 4️⃣ Set Environment Variables
Copy these to Railway → Variables:

```env
# Database (from Supabase)
DATABASE_URL=postgresql+psycopg2://postgres.vmatvxvzfwetntprwwxr:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
SUPABASE_URL=https://vmatvxvzfwetntprwwxr.supabase.co

# Stripe
STRIPE_SECRET_KEY=sk_test_YOUR_KEY
STRIPE_WEBHOOK_SECRET=(set after webhook creation)

# Model URLs (replace with your R2 URLs)
MODEL_EFFICIENTNET_URL=https://YOUR-R2-URL/models/efficientnet_b0_deepfake.h5
MODEL_MOBILENET_URL=https://YOUR-R2-URL/models/mobilenetv2_deepfake.h5
MODEL_RESNET_URL=https://YOUR-R2-URL/models/resnet50_deepfake.h5
MODEL_XCEPTION_URL=https://YOUR-R2-URL/models/xception_deepfake.h5

# Cloudflare R2
R2_ACCOUNT_ID=YOUR_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_ACCESS_KEY
R2_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
R2_BUCKET_NAME=deepfake-images
R2_PUBLIC_URL=https://YOUR-R2-URL.r2.dev

# Frontend
FRONTEND_URL=https://your-app.vercel.app
FRONTEND_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

### 5️⃣ Deploy & Test
- Railway auto-deploys after env vars are set
- Get URL: `https://your-project.up.railway.app`
- Test: `curl https://your-project.up.railway.app/health`

### 6️⃣ Connect Stripe Webhook
- Stripe Dashboard → Webhooks → Add endpoint
- URL: `https://your-project.up.railway.app/api/stripe-webhook`
- Event: `checkout.session.completed`
- Copy signing secret → Add to Railway as `STRIPE_WEBHOOK_SECRET`

### 7️⃣ Update Frontend
In Vercel:
```env
NEXT_PUBLIC_API_URL=https://your-project.up.railway.app
```

---

## 🔍 Verification

```bash
# Health check
curl https://your-project.up.railway.app/health

# Storage info
curl https://your-project.up.railway.app/api/admin/storage-info

# Check logs
railway logs --follow
```

---

## ⚠️ Common Issues

**Models not loading?**
- Check Railway logs for download errors
- Verify R2 URLs are publicly accessible (test in browser)
- Ensure MODEL_*_URL env vars are correct

**Out of memory?**
- Upgrade Railway plan to at least 4GB RAM
- Models need ~2-3GB to load

**Database connection failed?**
- Verify DATABASE_URL has `?sslmode=require`
- Check Supabase pooler URL format

---

## 💾 Your Current Setup

**Database**: 
```
postgresql+psycopg2://postgres.vmatvxvzfwetntprwwxr@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
```

**Supabase URL**:
```
https://vmatvxvzfwetntprwwxr.supabase.co
```

**R2 Bucket**:
```
deepfake-images
```

---

## 📚 Full Guide
See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed documentation.
