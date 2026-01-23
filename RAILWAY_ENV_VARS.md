# Production Environment Variables for Railway

## Copy these to Railway Dashboard → Variables

```env
# Database
DATABASE_URL=postgresql+psycopg2://postgres.vmatvxvzfwetntprwwxr:Ashayash1@aws-1-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
SUPABASE_URL=https://vmatvxvzfwetntprwwxr.supabase.co

# Stripe
STRIPE_SECRET_KEY=sk_test_51RVkjfKNnogxVUF9pcaFpgVsIWHqIO89G4vPQ367Nu0BEjlNWjyiBKyZaFArbsL4XZosr5vehx9t2RTN6ngs8rt100UEEgLUw1
STRIPE_WEBHOOK_SECRET=(add after creating webhook)

# Cloudflare R2
R2_ACCOUNT_ID=e725c5bf9610710b61c35ab31dde6bf5
R2_ACCESS_KEY_ID=1ff397994e70eea6fc3f8db13914c973
R2_SECRET_ACCESS_KEY=9cad5375cd96f0324f88a5146052bb3e5a9266b2d5fbb8b6617082fff29de2da
R2_BUCKET_NAME=deepfake-images
R2_PUBLIC_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev

# Model URLs
MODEL_EFFICIENTNET_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev/models/efficientnet_b0_deepfake.h5
MODEL_MOBILENET_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev/models/mobilenetv2_deepfake.h5
MODEL_RESNET_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev/models/resnet50_deepfake.h5
MODEL_XCEPTION_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev/models/xception_deepfake.h5
MODEL_DEEPVERIFY_URL=https://pub-fec6371a9d484a47b42917afcca5ca27.r2.dev/models/deepverify_finetuned.pt

# CORS - UPDATE AFTER VERCEL DEPLOYMENT
FRONTEND_URL=https://your-app.vercel.app
FRONTEND_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

## After Vercel Deployment

Once you deploy to Vercel and get your URL (e.g., `https://deepfake-detection.vercel.app`), update these two variables in Railway:

```env
FRONTEND_URL=https://your-actual-vercel-url.vercel.app
FRONTEND_ORIGINS=https://your-actual-vercel-url.vercel.app,http://localhost:3000
```

## Stripe Webhook Setup

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://deepfakedetection-production-ab9b.up.railway.app/api/stripe-webhook`
3. Select event: `checkout.session.completed`
4. Copy webhook signing secret
5. Add to Railway: `STRIPE_WEBHOOK_SECRET=whsec_xxx`
