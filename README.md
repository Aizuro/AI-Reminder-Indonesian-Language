# 🚀 Deployment Guide - Indonesian AI Reminder

**Complete step-by-step guide from local to production**

---

## 📋 Prerequisites

Before starting, make sure you have:

- ✅ Python 3.8+ installed
- ✅ Git installed
- ✅ Hugging Face account (free): https://huggingface.co/join
- ✅ Your trained NER model files in `model/checkpoint/`

---

## 🎯 STEP 1: Setup Project Structure

Create folder structure:

```bash
# Create project folder
mkdir ai-reminder-hf
cd ai-reminder-hf

# Create subfolders
mkdir src
mkdir model
mkdir model/checkpoint
```

Copy files from artifacts to this structure:

```
ai-reminder-hf/
├── app.py                     # Main Gradio app (from artifact)
├── requirements.txt           # Dependencies (from artifact)
├── README.md                  # Documentation (from artifact)
├── upload_model_to_hf.py     # Upload script (from artifact)
├── src/
│   ├── __init__.py           # Package init (from artifact)
│   ├── ner_model.py          # NER model (from artifact)
│   └── time_normalizer.py    # Time parser (from artifact)
└── model/
    └── checkpoint/
        ├── config.json        # YOUR model files
        ├── model.safetensors  # YOUR model files
        ├── tokenizer.json     # YOUR model files
        ├── tokenizer_config.json
        ├── special_tokens_map.json
        └── vocab.txt
```

---

## 📦 STEP 2: Upload Model to Hugging Face Model Hub

### Option A: Using Upload Script (Recommended)

```bash
# 1. Install huggingface_hub
pip install huggingface_hub

# 2. Edit upload_model_to_hf.py
# Change line 16:
REPO_ID = "your-username/indonesian-ner-reminder"
# Replace "your-username" with your HF username

# 3. Run script
python upload_model_to_hf.py

# 4. Follow prompts:
#    - Paste your HF token (get from https://huggingface.co/settings/tokens)
#    - Wait for upload (may take 5-10 minutes)
```

### Option B: Using Web Interface

1. Go to: https://huggingface.co/new
2. Select **Model**
3. Repository name: `indonesian-ner-reminder`
4. License: Apache 2.0
5. Click **Create model**
6. Click **Files and versions** tab
7. Click **Add file** → **Upload files**
8. Drag & drop all 6 files from `model/checkpoint/`
9. Click **Commit changes**

### Verify Upload

Visit: `https://huggingface.co/your-username/indonesian-ner-reminder`

Check that all 6 files are present:
- ✅ config.json
- ✅ model.safetensors
- ✅ tokenizer.json
- ✅ tokenizer_config.json
- ✅ special_tokens_map.json
- ✅ vocab.txt

---

## 🧪 STEP 3: Test Locally

### Update Model Path

Edit `app.py` line 27:

```python
MODEL_PATH = "your-username/indonesian-ner-reminder"  # Change this!
```

Replace `your-username` with your actual HF username.

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python app.py
```

Open browser: http://localhost:7860

### Test Checklist

- ✅ App loads without errors
- ✅ Model loads from Hugging Face
- ✅ Text input works
- ✅ Voice input works (Chrome/Edge only)
- ✅ Countdown updates every second
- ✅ Alarm sound plays (allow audio in browser)
- ✅ Entity table shows detected entities
- ✅ Debug info displays correctly

If all tests pass → proceed to deployment!

---

## 🚀 STEP 4: Deploy to Hugging Face Spaces

### Option A: Via Web Interface (Easiest)

**1. Create Space**
- Go to: https://huggingface.co/new-space
- Space name: `ai-reminder-demo`
- License: Apache 2.0
- Select SDK: **Gradio**
- Hardware: **CPU basic** (free)
- Visibility: Public
- Click **Create space**

**2. Upload Files**

Upload these files via web interface:

```
✅ app.py
✅ requirements.txt
✅ README.md
✅ src/__init__.py
✅ src/ner_model.py
✅ src/time_normalizer.py
```

**Method:**
- Click **Files** tab
- Click **Add file** → **Upload files**
- Drag & drop all 6 files
- Click **Commit changes to main**

**3. Wait for Build**

- Space will auto-build (takes 2-3 minutes)
- Check **App** tab - should show "Building..."
- Wait for green "Running" status

**4. Test Live**

- Click **App** tab
- Test all features
- Share link: `https://huggingface.co/spaces/your-username/ai-reminder-demo`

### Option B: Via Git (For Developers)

```bash
# 1. Clone space
git clone https://huggingface.co/spaces/your-username/ai-reminder-demo
cd ai-reminder-demo

# 2. Copy files
cp ../ai-reminder-hf/app.py .
cp ../ai-reminder-hf/requirements.txt .
cp ../ai-reminder-hf/README.md .
cp -r ../ai-reminder-hf/src .

# 3. Commit and push
git add .
git commit -m "Initial deployment"
git push

# 4. Check build status
# Visit: https://huggingface.co/spaces/your-username/ai-reminder-demo
```

---

## ✅ STEP 5: Verification Checklist

After deployment, verify:

### Model Hub
- ✅ Model accessible at: `https://huggingface.co/Aizuro/indonesian-ner-time_reminder`
- ✅ All 6 model files present
- ✅ README.md visible (optional but recommended)
- ✅ Model card filled (optional)

### Spaces
- ✅ App running at: `https://huggingface.co/spaces/Aizuro/ai-reminder-demo`
- ✅ No build errors (check Logs tab)
- ✅ All features working
- ✅ Voice input functional (Chrome/Edge)
- ✅ Alarm plays correctly
- ✅ Countdown updates in real-time

---

## 🐛 Troubleshooting

### Model Loading Error

**Error**: `OSError: your-username/indonesian-ner-reminder does not appear to be a valid repository`

**Solution**:
1. Check model is public (not private)
2. Verify repository name spelling
3. Ensure all 6 files uploaded
4. Wait 5 minutes for cache refresh

### Voice Input Not Working

**Error**: Microphone not detected or no transcription

**Solution**:
1. Use Chrome or Edge (Firefox/Safari not supported)
2. Allow microphone permissions
3. Speak clearly in Indonesian
4. Check browser console for errors

### Alarm Not Playing

**Error**: Countdown works but no sound

**Solution**:
1. Click anywhere on page first (browser autoplay restriction)
2. Enable audio autoplay in browser settings
3. Check volume is not muted
4. Try different browser

### Space Build Failed

**Error**: Space shows "Build failed" status

**Solution**:
1. Check **Logs** tab for error messages
2. Verify `requirements.txt` has correct versions
3. Ensure `MODEL_PATH` in `app.py` is correct
4. Check all files uploaded (6 files needed)
5. Try rebuilding: Settings → Factory Reboot

### Import Error

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
1. Ensure `src/` folder structure is correct
2. Check `src/__init__.py` exists
3. Verify all files in correct locations
4. Restart space: Settings → Factory Reboot

---

## 🎨 Customization After Deployment

### Change Theme

Edit `app.py`:

```python
# Line 380+
custom_css = """
.gr-button-primary {
    background: linear-gradient(135deg, #YOUR_COLOR1, #YOUR_COLOR2) !important;
}
"""
```

Commit and push changes.

### Add More Examples

Edit `app.py`:

```python
# Line 20+
EXAMPLES = [
    "Your new example 1",
    "Your new example 2",
]
```

### Change Alarm Sound

Edit `app.py`:

```python
# Line 17
ALARM_SOUND_URL = "https://your-sound-url.mp3"
```

Find free alarm sounds at:
- Pixabay: https://pixabay.com/sound-effects/
- Freesound: https://freesound.org/

---

## 📊 Monitoring

### Check Usage Stats

Visit: https://huggingface.co/spaces/Aizuro/ai-reminder-demo/analytics

Monitor:
- Daily views
- User interactions
- Error rates

### View Logs

Visit: https://huggingface.co/spaces/Aizuro/ai-reminder-demo/logs

Check for:
- Model loading success
- Inference times
- Any Python errors

---

## 🎯 Next Steps

After successful deployment:

1. **Add to Portfolio**
   - Add link to resume/CV
   - Share on LinkedIn
   - Add to GitHub README

2. **Optimize Performance**
   - Enable model caching
   - Add loading indicators
   - Optimize inference speed

3. **Gather Feedback**
   - Share with friends/colleagues
   - Post in HF discussions
   - Collect user feedback

4. **Iterate**
   - Fix reported bugs
   - Add requested features
   - Improve UX based on feedback

---

## 📞 Support

Need help?

- **Hugging Face Forum**: https://discuss.huggingface.co/
- **Discord**: https://discord.gg/hugging-face
- **Email**: support@huggingface.co

---

## 🎉 Congratulations!

You've successfully deployed your Indonesian AI Reminder to Hugging Face!

Share your demo:
- Twitter: Tag @huggingface
- LinkedIn: Add to projects
- GitHub: Add badge to README

**Demo URL**: `https://huggingface.co/spaces/Aizuro/ai-reminder-demo`

---

## 📝 Quick Reference

### Important URLs

- **HF Token**: https://huggingface.co/settings/tokens
- **Create Model**: https://huggingface.co/new
- **Create Space**: https://huggingface.co/new-space
- **Your Model**: https://huggingface.co/Aizuro/indonesian-ner-time_reminder
- **Your Space**: https://huggingface.co/spaces/Aizuro/ai-reminder-demo

### Command Cheatsheet

```bash
# Upload model
python upload_model_to_hf.py

# Test locally
python app.py

# Clone space
git clone https://huggingface.co/spaces/Aizuro/ai-reminder-demo

# Update space
git add .
git commit -m "Update"
git push
```