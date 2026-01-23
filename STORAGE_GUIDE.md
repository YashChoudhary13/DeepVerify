# 💾 Storage Management Guide

## Current Setup

Your backend now has **automatic storage management**:

### ✅ What's Been Added:

1. **Automatic Cleanup on Startup**
   - Removes old files when backend starts
   - Frees up space immediately

2. **Configurable Retention Periods**:
   - Uploads: 6 hours (processed files)
   - Heatmaps: 24 hours (analysis results)
   - Reverse Images: 2 hours (temporary for search)

3. **Storage Monitoring Endpoints**:
   - `GET /api/admin/storage-info` - Check current usage
   - `POST /api/admin/cleanup` - Manually trigger cleanup

---

## 📊 Storage Breakdown

### With 5GB Hosting:

**✅ Will Fit:**
- Application code: ~100MB
- Python packages: ~1GB
- Temporary files (with cleanup): ~500MB-1GB
- **Total Baseline: ~1.5-2GB**
- **Remaining for usage: ~3-3.5GB**

**⚠️ Will NOT Fit Long-term:**
- All user uploads (grows indefinitely)
- All ML models (1.5-2.5GB) - should be on R2
- Permanent storage of heatmaps
- Training contribution images

---

## 🎯 Recommended Production Setup

### Backend Disk (5GB) - Store:
```
✅ Application code
✅ Python dependencies  
✅ Temporary processing files (auto-deleted)
✅ Small cache
```

### Cloudflare R2 (Unlimited) - Store:
```
✅ ML model files
✅ User uploaded images (after processing)
✅ Generated heatmaps (permanent)
✅ Contribution images
✅ Reverse search images
```

### Supabase Database - Store:
```
✅ All metadata
✅ Analysis results
✅ User data
✅ File references (URLs to R2)
```

---

## 🔧 Usage Examples

### Check Storage Usage:
```bash
curl http://localhost:8000/api/admin/storage-info
```

Output:
```json
{
  "directories": {
    "uploads": {
      "file_count": 156,
      "total_size_gb": 0.85
    },
    "heatmaps": {
      "file_count": 89,
      "total_size_gb": 0.34
    }
  },
  "total": {
    "file_count": 245,
    "total_size_gb": 1.19
  }
}
```

### Manual Cleanup:
```bash
curl -X POST http://localhost:8000/api/admin/cleanup
```

---

## ⚙️ Configuration

### Adjust Retention Times:

Edit `.env`:
```env
UPLOAD_RETENTION_HOURS=6       # Keep uploads for 6 hours
HEATMAP_RETENTION_HOURS=24     # Keep heatmaps for 24 hours  
REVERSE_IMAGE_RETENTION_HOURS=2 # Keep reverse images for 2 hours
```

### Current Behavior:
1. **On upload**: File saved temporarily
2. **After analysis**: Results saved to database
3. **After retention period**: File auto-deleted
4. **Permanent storage**: Move to R2 if needed

---

## 📈 Storage Growth Estimates

### Expected Usage (5GB disk):
- **Low traffic** (10 uploads/day): ✅ 5GB sufficient
- **Medium traffic** (100 uploads/day): ⚠️ 5GB tight, needs frequent cleanup
- **High traffic** (1000+ uploads/day): ❌ Need R2 integration

### Recommendations by Scale:

**< 100 uploads/day:**
- ✅ 5GB OK with auto-cleanup
- Keep 6-hour retention

**100-500 uploads/day:**
- ⚠️ Consider 10GB disk
- Or move uploads to R2 immediately

**> 500 uploads/day:**
- ❌ Must use R2 for all uploads
- Backend disk only for processing

---

## 🚨 Monitoring Alerts

Set up alerts when storage exceeds:
- **70%** (3.5GB): Warning
- **85%** (4.25GB): Critical
- **95%** (4.75GB): Emergency cleanup

---

## 💡 Cost Optimization

### Option 1: 5GB + R2 (Cheapest)
- Backend: 5GB disk
- R2: $0.015/GB/month
- **Best for**: Medium traffic
- **Cost**: ~$10-15/month total

### Option 2: 10GB disk (Simple)
- Backend: 10GB disk
- No R2 setup needed
- **Best for**: Low-medium traffic
- **Cost**: ~$15-20/month

### Option 3: 5GB + Aggressive Cleanup (Minimal)
- Backend: 5GB disk
- 2-hour retention for everything
- **Best for**: Very low traffic
- **Cost**: ~$10/month

---

## ✅ Conclusion

**5GB is sufficient IF:**
- ✅ You enable auto-cleanup (already done)
- ✅ You use short retention periods
- ✅ Traffic is low-medium
- ✅ You move to R2 as you grow

**You'll need more IF:**
- ❌ High traffic (100+ uploads/day)
- ❌ Need to keep files > 24 hours
- ❌ Storing models on disk (move to R2!)
- ❌ No cleanup enabled

Your current setup with auto-cleanup makes 5GB workable for development and initial production! 🎉
