import gradio as gr
import torch
from datetime import datetime
import pytz
from typing import List, Dict, Tuple
import pandas as pd
import time

# Import our modules
from src.ner_model import ReminderNERModel
from src.time_normalizer import TimeNormalizer

# ============================================
# CONFIGURATION
# ============================================

TIMEZONE = "Asia/Jakarta"
MODEL_PATH = "Aizuro/indonesian-ner-time_reminder"  # GANTI dengan HF model Anda

# Alarm sound URL
ALARM_SOUND_URL = "https://cdn.pixabay.com/download/audio/2021/08/04/audio_bb630cc098.mp3"

# Alarm settings
ALARM_DURATION = 10  # Alarm will play for 30 seconds

# Example inputs
EXAMPLES = [
    ["reminder 20 detik lagi"],
    ["reminder 5 menit lagi"],
    ["reminder 2 jam lagi"],
    ["meeting besok jam 10 pagi"],
    ["makan siang hari ini jam 12.30"],
]

# ============================================
# GLOBAL STATE
# ============================================

reminders = []
alarm_triggered = {}

# ============================================
# LOAD MODELS
# ============================================

print("🔄 Loading models...")
ner_model = ReminderNERModel(model_path=MODEL_PATH)
time_normalizer = TimeNormalizer(timezone=TIMEZONE)
print("✅ Models loaded!")

# ============================================
# HELPER FUNCTIONS
# ============================================


def generate_reminder_id() -> str:
    """Generate unique reminder ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def calculate_time_until(target_time: datetime) -> str:
    """Calculate human-readable time until target"""
    now = datetime.now(pytz.timezone(TIMEZONE))
    delta = target_time - now

    if delta.total_seconds() <= 0:
        return "sudah lewat"

    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    if seconds > 0:
        parts.append(f"{seconds} detik")

    return " ".join(parts) + " lagi"


def create_entity_table(entities: List[Dict]) -> pd.DataFrame:
    """Create DataFrame for entity visualization"""
    if not entities:
        return pd.DataFrame({"Message": ["No entities detected"]})

    data = []
    for entity in entities:
        data.append({
            "Entity Type": entity['type'],
            "Text": entity['text'],
            "Tokens": " ".join(entity['tokens'])
        })

    return pd.DataFrame(data)

# ============================================
# DISPLAY FUNCTIONS (STATIC - NO ANIMATION)
# ============================================


def format_reminder_display() -> Tuple[str, str]:
    """
    Format reminders with STATIC display (no flicker)
    Returns: (html_display, audio_html)
    """

    if not reminders:
        empty_html = """
        <div style='text-align: center; padding: 60px; background: linear-gradient(135deg, #1e2130, #2d3142); border-radius: 12px;'>
            <div style='font-size: 48px; margin-bottom: 20px;'>📝</div>
            <div style='font-size: 20px; color: #a0a0a0; font-weight: 600;'>Reminder masih kosong</div>
        """
        return empty_html, ""

    html_parts = []
    audio_html = ""
    now_time = datetime.now(pytz.timezone(TIMEZONE))
    now_timestamp = time.time()

    for reminder in reversed(reminders):
        reminder_id = reminder['id']
        target_time = reminder['normalized_time']
        is_expired = target_time <= now_time

        # Check if alarm should trigger (FIRST TIME)
        if is_expired and reminder_id not in alarm_triggered:
            alarm_triggered[reminder_id] = now_timestamp
            print(f"🔔 ALARM BERBUNYI: {reminder_id}")

        # Check if alarm is currently playing
        is_alarm_playing = False
        if reminder_id in alarm_triggered:
            elapsed = now_timestamp - alarm_triggered[reminder_id]
            if elapsed < ALARM_DURATION:
                is_alarm_playing = True

                # Generate audio HTML with LOOP
                audio_html = f"""
                <audio id="alarm-{reminder_id}" loop autoplay style="display:none;">
                    <source src="{ALARM_SOUND_URL}" type="audio/mpeg">
                </audio>
                <script>
                (function() {{
                    const audio = document.getElementById('alarm-{reminder_id}');
                    if (audio && audio.paused) {{
                        audio.volume = 0.8;
                        audio.play().then(() => {{
                            console.log('🔔 Alarm playing: {reminder_id}');
                        }}).catch(e => {{
                            console.log('⚠️ Audio blocked, trying on interaction:', e);
                            document.body.addEventListener('click', () => {{
                                audio.play();
                            }}, {{once: true}});
                        }});
                    }}
                }})();
                </script>
                """

        # Card styling
        if is_expired:
            if is_alarm_playing:
                border_color = "#ff4d6d"
                status_bg = "#ff4d6d"
                status_text = "🔔 RINGING"
            else:
                border_color = "#6b6b6b"
                status_bg = "#6b6b6b"
                status_text = "SELESAI"
        else:
            border_color = "#4a9eff"
            status_bg = "#00d4aa"
            status_text = "SCHEDULED"

        # Time until display
        time_until = calculate_time_until(target_time)

        # Alarm visual section
        alarm_section = ""
        if is_alarm_playing:
            seconds_left = int(
                ALARM_DURATION - (now_timestamp - alarm_triggered[reminder_id]))
            alarm_section = f"""
            <div style='
                background: linear-gradient(135deg, #ff4d6d, #ff8a5b);
                color: white;
                padding: 30px;
                border-radius: 12px;
                margin-top: 20px;
                text-align: center;
                box-shadow: 0 0 30px rgba(255,77,109,0.8);
            '>
                <div style='font-size: 56px; margin-bottom: 15px;'>
                    🔔
                </div>
                <div style='font-size: 32px; font-weight: 900; margin-bottom: 15px;'>
                    ALARM BERBUNYI!
                </div>
                <div style='font-size: 18px; margin-bottom: 10px; opacity: 0.9;'>
                    {reminder['text']}
                </div>
                <div style='font-size: 16px; opacity: 0.8;'>
                    Alarm akan berhenti dalam {seconds_left} detik...
                </div>
            </div>
            """
        elif reminder_id in alarm_triggered:
            alarm_section = """
            <div style='
                background: #2d3142;
                color: #00d4aa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 15px;
                text-align: center;
                border: 2px solid #00d4aa;
            '>
                Alarm telah selesai
            </div>
            """

        card_html = f"""
        <div style='
            background: linear-gradient(135deg, #1e2130, #2d3142);
            border-radius: 12px;
            padding: 25px;
            margin: 15px 0;
            border-left: 5px solid {border_color};
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        '>
            <!-- Header -->
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;'>
                <div style='flex: 1;'>
                    <div style='color: #e6e6e6; font-size: 22px; font-weight: 600; margin-bottom: 8px;'>
                        📝 {reminder['text']}
                    </div>
                </div>
                <div style='
                    padding: 10px 20px;
                    background: {status_bg};
                    color: white;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 700;
                    margin-left: 15px;
                '>
                    {status_text}
                </div>
            </div>
            
            <!-- Target Time Display (STATIC) -->
            <div style='
                background: rgba(74, 158, 255, 0.1);
                padding: 30px;
                border-radius: 12px;
                text-align: center;
                border: 2px solid {border_color};
            '>
                <div style='color: #a0a0a0; font-size: 15px; margin-bottom: 12px;'>
                    Alarm akan berbunyi pada:
                </div>
                <div style='font-size: 48px; font-weight: 900; color: {border_color}; margin-bottom: 8px; font-family: monospace;'>
                    {target_time.strftime('%H:%M:%S')}
                </div>
                <div style='font-size: 20px; color: #a0a0a0; margin-bottom: 12px;'>
                    {target_time.strftime('%A, %d %B %Y')}
                </div>
                <div style='font-size: 16px; color: #4a9eff; font-weight: 600;'>
                    ⏱️ {time_until}
                </div>
            </div>
            
            {alarm_section}
            
            <!-- Info -->
            <div style='margin-top: 15px; display: flex; justify-content: space-between; font-size: 12px; color: #6b6b6b;'>
                <span>📅 Created: {reminder['created_at'].strftime('%d %b, %H:%M')}</span>
                <span>🎯 Confidence: {reminder['confidence']:.1%}</span>
                <span>🆔 {reminder_id}</span>
            </div>
        </div>
        """

        html_parts.append(card_html)

    display_html = "".join(html_parts)

    return display_html, audio_html

# ============================================
# PROCESSING FUNCTIONS
# ============================================


def process_reminder(text_input: str) -> Tuple:
    """Process and create reminder"""

    if not text_input or not text_input.strip():
        display_html, audio_html = format_reminder_display()
        return (
            display_html,
            audio_html,
            pd.DataFrame({"Message": ["No input"]}),
            "⚠️ Please enter text",
            ""
        )

    try:
        # NER Prediction
        ner_result = ner_model.predict(text_input)

        # Time Normalization
        normalized_time = time_normalizer.normalize(
            text_input, ner_result['entities'])

        # Create reminder
        reminder_id = generate_reminder_id()
        reminder = {
            'id': reminder_id,
            'text': text_input,
            'entities': ner_result['entities'],
            'normalized_time': normalized_time,
            'confidence': ner_result['confidence'],
            'created_at': datetime.now(pytz.timezone(TIMEZONE))
        }

        reminders.append(reminder)

        # Generate outputs
        display_html, audio_html = format_reminder_display()
        entity_table = create_entity_table(ner_result['entities'])

        # Debug info
        time_until_str = calculate_time_until(normalized_time)
        debug_info = f"""
📊 Reminder Created Successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Input: {text_input}
✅ Entities: {len(ner_result['entities'])}
✅ Target: {normalized_time.strftime('%d %B %Y, %H:%M:%S WIB')}
✅ Confidence: {ner_result['confidence']:.1%}
✅ ID: {reminder_id}
✅ Time Until: {time_until_str}
"""

        success_msg = f"✅ Alarm diset pada {normalized_time.strftime('%H:%M:%S - %d %b %Y')} ({time_until_str})"

        return display_html, audio_html, entity_table, debug_info, success_msg

    except Exception as e:
        import traceback
        display_html, audio_html = format_reminder_display()
        error_table = pd.DataFrame({"Error": [str(e)]})
        error_debug = f"❌ ERROR:\n{str(e)}\n\n{traceback.format_exc()}"

        return display_html, audio_html, error_table, error_debug, f"❌ {str(e)}"


def check_alarms() -> Tuple:
    """Check and trigger alarms (called every 1 second)"""
    display_html, audio_html = format_reminder_display()
    return display_html, audio_html


def clear_all() -> Tuple:
    """Clear all reminders"""
    global reminders, alarm_triggered
    reminders = []
    alarm_triggered = {}

    display_html, audio_html = format_reminder_display()
    empty_table = pd.DataFrame({"Message": ["Cleared"]})

    return display_html, audio_html, empty_table, "Kosong", "Sudah terhapus semua"

# ============================================
# GRADIO INTERFACE
# ============================================


custom_css = """
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}
"""

with gr.Blocks(css=custom_css, theme=gr.themes.Soft(primary_hue="blue")) as demo:
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## 📝 Buat Reminder")

            text_input = gr.Textbox(
                label="Masukkan Reminder",
                placeholder="Contoh: reminder 20 detik lagi",
                lines=3
            )

            with gr.Row():
                submit_btn = gr.Button(
                    "Buat Alarm", variant="primary", scale=2)
                clear_btn = gr.Button("🗑️ Hapus Semua", scale=1)

            success_msg = gr.Textbox(label="Status", interactive=False)

            gr.Examples(
                examples=EXAMPLES,
                inputs=[text_input],
                label="💡 Contoh yang bisa dipakai:"
            )

        with gr.Column(scale=1):
            gr.Markdown("## ⏰ Alarm Aktif")

            reminder_display = gr.HTML()

    # gr.Markdown("### 🔊 Alarm Audio")
    audio_player = gr.HTML()

    with gr.Accordion("🔍 NER Entities", open=False):
        entity_table = gr.Dataframe(interactive=False)

    with gr.Accordion("🐛 Debug Info", open=False):
        debug_info = gr.Textbox(lines=18, interactive=False)

    gr.Markdown("""
    ---
    ### 📚 Cara Kerja
    
    1. Masukkan input anda menggunakan bahasa Indonesia
    2. Pengingat anda akan ditampilkan dengan waktu yang sudah anda tetapkan
    3. Akan ada countdown waktu anda sampai waktunya tiba
    4. Alarm akan terpicu ketika waktunya sudah tiba
    5. Akan mengulang alarm selama 10 detik dan selesai
    
    **Supported formats:**
    - **Relative:** "20 detik lagi", "5 menit lagi", "2 jam lagi"
    - **Absolute:** "besok jam 10", "hari ini jam 14:30"
    - **Day + time:** "Senin pagi jam 9", "Jumat sore"
    
    **⚠️ Important: Tetap buka tab ini agar alarm bisa bekerja**
    
    **✨ Created by Abdul Azizur Rokhman | BiLSTM-CRF NER Model**
    """)

    # Event handlers
    submit_btn.click(
        fn=process_reminder,
        inputs=[text_input],
        outputs=[reminder_display, audio_player,
                 entity_table, debug_info, success_msg]
    )

    clear_btn.click(
        fn=clear_all,
        outputs=[reminder_display, audio_player,
                 entity_table, debug_info, success_msg]
    )

    # Auto-check alarms every 1 second
    demo.load(
        fn=check_alarms,
        outputs=[reminder_display, audio_player]
    )

    timer = demo.load(
        fn=check_alarms,
        outputs=[reminder_display, audio_player],
        every=1  # Check every 1 second
    )

if __name__ == "__main__":
    demo.launch()
