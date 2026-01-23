# 🚀 Deployment Checklist

## Backend (.env variables to set)
- [ ] `DATABASE_URL` - Supabase connection string
- [ ] `STRIPE_SECRET_KEY` - From Stripe dashboard
- [ ] `STRIPE_WEBHOOK_SECRET` - After setting up webhook
- [ ] `SUPABASE_URL` - Your Supabase project URL
- [ ] `R2_ACCOUNT_ID` - Cloudflare account ID
- [ ] `R2_ACCESS_KEY_ID` - R2 API token
- [ ] `R2_SECRET_ACCESS_KEY` - R2 secret key
- [ ] `R2_BUCKET_NAME` - Your bucket name
- [ ] `R2_PUBLIC_URL` - Public R2 URL
- [ ] `FRONTEND_URL` - Your deployed frontend URL
- [ ] `REDIS_URL` - Redis connection string (for Celery)

## Frontend (.env.local)
- [ ] `NEXT_PUBLIC_API_URL` - Your backend URL (https://...)
- [ ] `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` - Stripe public key

## Domain & DNS
- [ ] Backend domain configured
- [ ] Frontend domain configured
- [ ] SSL certificates (automatic with Vercel/Railway)

## Stripe Setup
- [ ] Create webhook endpoint: `https://your-backend.com/api/stripe-webhook`
- [ ] Select event: `checkout.session.completed`
- [ ] Copy webhook secret to backend env

## Database
- [ ] Run migrations if needed
- [ ] Verify Supabase connection

## Storage
- [ ] R2 bucket created
- [ ] Public access configured
- [ ] Test image upload

## Testing
- [ ] Test user registration/login
- [ ] Test image upload and analysis
- [ ] Test payment flow
- [ ] Test reverse image search
- [ ] Test all tools

## Security
- [ ] Change all default secrets
- [ ] Enable CORS properly
- [ ] Set up rate limiting
- [ ] Review error messages (don't expose sensitive info)

## Monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Set up analytics (if needed)

## Optimization
- [ ] Compress model files if possible
- [ ] Enable caching
- [ ] Optimize images
- [ ] Test performance under load
