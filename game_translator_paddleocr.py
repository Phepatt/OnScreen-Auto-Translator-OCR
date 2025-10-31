#!/usr/bin/env python3
"""
Gaming-Optimized Japanese Screen Translator with PaddleOCR
VERSION: 3.0 (OPTIMIZED - Smart Overlays + Region Selection)

Perfect for: Games, Anime, Manga, Visual Novels
Features:
- Individual overlay lifespans (no more flickering!)
- Translation cache (prevents duplicates)
- Region selection (faster OCR)
- Smart memory management

UPDATED: 2025-10-23
- Added: Individual overlay timers
- Added: Translation cache system
- Added: Region of Interest selection
- Fixed: Smooth real-time experience
"""
import re
import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageGrab, ImageDraw
from googletrans import Translator
import threading
import time
import sys
import numpy as np
import hashlib

# Version check
VERSION = "3.0 - Optimized"

class GameTranslatorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Gaming Japanese Translator v{VERSION}")
        self.root.geometry("420x720")
        self.root.attributes('-topmost', True)
        
        # PaddleOCR - will be initialized when starting
        self.ocr = None
        self.ocr_ready = False
        
        # Variables
        self.is_running = False
        self.translator = Translator()
        
        # NEW: Overlay management with individual timers
        self.overlay_data = {}  # {id: {window, text_hash, expires_at, ...}}
        self.next_overlay_id = 0
        
        # NEW: Translation cache
        self.translation_cache = {}  # {text_hash: {translation, last_seen, position_hash}}
        
        # NEW: Region of Interest
        self.capture_region = None  # None = full screen, or (x, y, w, h)
        self.region_selection_window = None
        
        # Settings
        self.scan_interval = tk.DoubleVar(value=0.05)
        self.min_confidence = tk.DoubleVar(value=0.53)
        self.font_size = tk.IntVar(value=8)
        self.overlay_alpha = tk.DoubleVar(value=0.75)
        
        # NEW: Duration settings
        self.duration_short = tk.DoubleVar(value=2.0)   # < 15 chars
        self.duration_medium = tk.DoubleVar(value=3.0)  # 15-30 chars
        self.duration_long = tk.DoubleVar(value=4.0)   # > 30 chars
        self.cache_lifetime = tk.DoubleVar(value=20.0)  # Cache duration
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup user interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        container = ttk.Frame(scrollable_frame, padding="15")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(container, text="🎮 Gaming Japanese Translator", 
                          font=('Arial', 16, 'bold'))
        header.pack(pady=(0, 3))
        
        version_label = ttk.Label(container, text=f"v{VERSION}", 
                                 font=('Arial', 8), foreground='gray')
        version_label.pack(pady=(0, 3))
        
        sub_header = ttk.Label(container, text="Optimized • Smart Cache • Region Select", 
                              font=('Arial', 9), foreground='gray')
        sub_header.pack(pady=(0, 15))
        
        # Status frame
        status_frame = ttk.LabelFrame(container, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_indicator = tk.Canvas(status_frame, width=20, height=20, 
                                         highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))
        self.status_circle = self.status_indicator.create_oval(2, 2, 18, 18, 
                                                                fill='red', outline='')
        
        self.status_text = ttk.Label(status_frame, text="Not initialized", 
                                     font=('Arial', 10, 'bold'))
        self.status_text.pack(side=tk.LEFT)
        
        # Region info
        self.region_label = ttk.Label(status_frame, text="📐 Full Screen", 
                                      font=('Arial', 9), foreground='blue')
        self.region_label.pack(side=tk.RIGHT)
        
        # Control buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_btn = ttk.Button(btn_frame, text="▶ Start Translation", 
                                    command=self.toggle_translation)
        self.start_btn.pack(fill=tk.X, pady=(0, 5))
        
        # NEW: Region selection button
        self.region_btn = ttk.Button(btn_frame, text="📐 Select Capture Region", 
                                     command=self.start_region_selection)
        self.region_btn.pack(fill=tk.X, pady=(0, 5))
        
        reset_region_btn = ttk.Button(btn_frame, text="🔄 Reset to Full Screen", 
                                      command=self.reset_region)
        reset_region_btn.pack(fill=tk.X, pady=(0, 5))
        
        clear_btn = ttk.Button(btn_frame, text="🗑️ Clear All Overlays", 
                              command=self.clear_all_overlays)
        clear_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Settings
        settings_frame = ttk.LabelFrame(container, text="⚙️ Settings", padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scan interval
        ttk.Label(settings_frame, text="Scan Interval:").grid(row=0, column=0, 
                                                              sticky=tk.W, pady=5)
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.grid(row=0, column=1, sticky=tk.W, padx=10)
        ttk.Scale(interval_frame, from_=1.0, to=10.0, variable=self.scan_interval,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        ttk.Label(interval_frame, textvariable=self.scan_interval,
                 width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(interval_frame, text="sec").pack(side=tk.LEFT)
        
        # Confidence threshold
        ttk.Label(settings_frame, text="Min Confidence:").grid(row=1, column=0, 
                                                               sticky=tk.W, pady=5)
        conf_frame = ttk.Frame(settings_frame)
        conf_frame.grid(row=1, column=1, sticky=tk.W, padx=10)
        ttk.Scale(conf_frame, from_=0.3, to=0.9, variable=self.min_confidence,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        conf_label = ttk.Label(conf_frame, text="", width=5)
        conf_label.pack(side=tk.LEFT, padx=5)
        
        def update_conf(*args):
            conf_label.config(text=f"{int(self.min_confidence.get()*100)}%")
        self.min_confidence.trace('w', update_conf)
        update_conf()
        
        # Font size
        ttk.Label(settings_frame, text="Font Size:").grid(row=2, column=0, 
                                                          sticky=tk.W, pady=5)
        font_frame = ttk.Frame(settings_frame)
        font_frame.grid(row=2, column=1, sticky=tk.W, padx=10)
        ttk.Scale(font_frame, from_=8, to=20, variable=self.font_size,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        ttk.Label(font_frame, textvariable=self.font_size,
                 width=5).pack(side=tk.LEFT, padx=5)
        
        # Overlay transparency
        ttk.Label(settings_frame, text="Overlay Opacity:").grid(row=3, column=0, 
                                                                sticky=tk.W, pady=5)
        alpha_frame = ttk.Frame(settings_frame)
        alpha_frame.grid(row=3, column=1, sticky=tk.W, padx=10)
        ttk.Scale(alpha_frame, from_=0.5, to=1.0, variable=self.overlay_alpha,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        opacity_label = ttk.Label(alpha_frame, text="", width=5)
        opacity_label.pack(side=tk.LEFT, padx=5)
        
        def update_opacity(*args):
            opacity_label.config(text=f"{int(self.overlay_alpha.get()*100)}%")
        self.overlay_alpha.trace('w', update_opacity)
        update_opacity()
        
        # NEW: Duration settings
        ttk.Separator(settings_frame, orient='horizontal').grid(row=4, column=0, 
                                                                columnspan=2, sticky='ew', pady=10)
        
        ttk.Label(settings_frame, text="Display Duration:", 
                 font=('Arial', 9, 'bold')).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Short text duration
        ttk.Label(settings_frame, text="Short (<15 chars):").grid(row=6, column=0, 
                                                                  sticky=tk.W, pady=5)
        short_frame = ttk.Frame(settings_frame)
        short_frame.grid(row=6, column=1, sticky=tk.W, padx=10)
        ttk.Scale(short_frame, from_=3.0, to=10.0, variable=self.duration_short,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        ttk.Label(short_frame, textvariable=self.duration_short,
                 width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(short_frame, text="sec").pack(side=tk.LEFT)
        
        # Medium text duration
        ttk.Label(settings_frame, text="Medium (15-30):").grid(row=7, column=0, 
                                                               sticky=tk.W, pady=5)
        med_frame = ttk.Frame(settings_frame)
        med_frame.grid(row=7, column=1, sticky=tk.W, padx=10)
        ttk.Scale(med_frame, from_=5.0, to=15.0, variable=self.duration_medium,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        ttk.Label(med_frame, textvariable=self.duration_medium,
                 width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(med_frame, text="sec").pack(side=tk.LEFT)
        
        # Long text duration
        ttk.Label(settings_frame, text="Long (>30 chars):").grid(row=8, column=0, 
                                                                 sticky=tk.W, pady=5)
        long_frame = ttk.Frame(settings_frame)
        long_frame.grid(row=8, column=1, sticky=tk.W, padx=10)
        ttk.Scale(long_frame, from_=8.0, to=20.0, variable=self.duration_long,
                 orient=tk.HORIZONTAL, length=150).pack(side=tk.LEFT)
        ttk.Label(long_frame, textvariable=self.duration_long,
                 width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(long_frame, text="sec").pack(side=tk.LEFT)
        
        # Info text
        info_frame = ttk.LabelFrame(container, text="ℹ️ What's New", padding="10")
        info_frame.pack(fill=tk.X)
        
        info_text = """✨ v3.0 Features:
• No more flickering! Each overlay has its own timer
• Smart cache prevents duplicate translations
• Select region for faster OCR processing
• Overlays stay visible based on text length
• Memory efficient - auto-cleanup system"""
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT,
                 font=('Arial', 9)).pack()
        
        # Exit button
        ttk.Button(container, text="❌ Exit", 
                  command=self.on_exit).pack(fill=tk.X, pady=(10, 0))
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
    def initialize_ocr(self):
        """Initialize PaddleOCR (done in background)"""
        try:
            self.status_text.config(text="Loading PaddleOCR models...")
            from paddleocr import PaddleOCR
            import paddle
            
            use_gpu_available = paddle.device.cuda.device_count() > 0
            
            if use_gpu_available:
                print("🎮 GPU detected! Using GPU acceleration")
                self.status_text.config(text="Loading models (GPU mode)...")
            else:
                print("💻 Using CPU mode")
                self.status_text.config(text="Loading models (CPU mode)...")
            
            self.ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='japan'
            )
            
            self.ocr_ready = True
            if use_gpu_available:
                self.status_text.config(text="Ready (GPU Enabled)! 🚀")
            else:
                self.status_text.config(text="Ready to start!")
            self.status_indicator.itemconfig(self.status_circle, fill='orange')
            return True
            
        except Exception as e:
            self.status_text.config(text=f"OCR Init Error: {str(e)[:30]}")
            print(f"OCR initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_region_selection(self):
        """Start region selection mode"""
        if self.is_running:
            tk.messagebox.showwarning("Warning", "Please stop translation first!")
            return
        
        # Create fullscreen transparent window
        self.region_selection_window = tk.Toplevel(self.root)
        self.region_selection_window.attributes('-fullscreen', True)
        self.region_selection_window.attributes('-alpha', 0.3)
        self.region_selection_window.configure(bg='black')
        
        canvas = tk.Canvas(self.region_selection_window, cursor="cross", 
                          bg='black', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = tk.Label(self.region_selection_window, 
                               text="Click and drag to select capture region\nPress ESC to cancel",
                               font=('Arial', 16, 'bold'), fg='white', bg='black')
        instructions.place(relx=0.5, rely=0.05, anchor='center')
        
        # Selection state
        selection = {'start': None, 'rect': None}
        
        def on_mouse_down(event):
            selection['start'] = (event.x, event.y)
            if selection['rect']:
                canvas.delete(selection['rect'])
        
        def on_mouse_move(event):
            if selection['start']:
                if selection['rect']:
                    canvas.delete(selection['rect'])
                x1, y1 = selection['start']
                selection['rect'] = canvas.create_rectangle(
                    x1, y1, event.x, event.y,
                    outline='red', width=3
                )
        
        def on_mouse_up(event):
            if selection['start']:
                x1, y1 = selection['start']
                x2, y2 = event.x, event.y
                
                # Normalize coordinates
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                if w > 50 and h > 50:  # Minimum size
                    self.capture_region = (x, y, w, h)
                    self.region_label.config(text=f"📐 Region: {w}x{h}")
                    print(f"✓ Region set: {self.capture_region}")
                    self.region_selection_window.destroy()
                else:
                    tk.messagebox.showwarning("Warning", "Region too small! Try again.")
                    self.region_selection_window.destroy()
        
        def on_escape(event):
            self.region_selection_window.destroy()
        
        canvas.bind('<Button-1>', on_mouse_down)
        canvas.bind('<B1-Motion>', on_mouse_move)
        canvas.bind('<ButtonRelease-1>', on_mouse_up)
        self.region_selection_window.bind('<Escape>', on_escape)
    
    def reset_region(self):
        """Reset to full screen capture"""
        self.capture_region = None
        self.region_label.config(text="📐 Full Screen")
        print("✓ Reset to full screen capture")
    
    def toggle_translation(self):
        """Start or stop translation"""
        if not self.is_running:
            self.start_translation()
        else:
            self.stop_translation()
    
    def start_translation(self):
        """Start auto-translation"""
        if not self.ocr_ready:
            self.start_btn.config(state='disabled', text="Loading OCR...")
            thread = threading.Thread(target=self._init_and_start, daemon=True)
            thread.start()
        else:
            self._start_scanning()
    
    def _init_and_start(self):
        """Initialize OCR and start scanning"""
        if self.initialize_ocr():
            self.root.after(100, self._start_scanning)
        self.root.after(100, lambda: self.start_btn.config(state='normal'))
    
    def _start_scanning(self):
        """Begin scanning"""
        self.is_running = True
        self.status_indicator.itemconfig(self.status_circle, fill='#00FF00')
        self.status_text.config(text="Running - Scanning...")
        self.start_btn.config(text="⏸ Stop Translation")
        
        # Start scan thread
        scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
        scan_thread.start()
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        # Start cache cleanup thread
        cache_thread = threading.Thread(target=self.cache_cleanup_loop, daemon=True)
        cache_thread.start()
    
    def stop_translation(self):
        """Stop auto-translation"""
        self.is_running = False
        self.status_indicator.itemconfig(self.status_circle, fill='orange')
        self.status_text.config(text="Stopped (Ready)")
        self.start_btn.config(text="▶ Start Translation")
        time.sleep(0.5)  # Let threads finish
        self.clear_all_overlays()
    
    def scan_loop(self):
        """Main scanning loop"""
        while self.is_running:
            try:
                # Capture screen (region or full)
                if self.capture_region:
                    x, y, w, h = self.capture_region
                    screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
                    offset = (x, y)  # For coordinate adjustment
                else:
                    screenshot = ImageGrab.grab()
                    offset = (0, 0)
                
                # Convert to numpy array
                img_array = np.array(screenshot)
                
                # Detect and translate
                self.detect_and_translate(img_array, offset)
                
                # Wait for next scan
                time.sleep(self.scan_interval.get())
                
            except Exception as e:
                print(f"Scan error: {e}")
                time.sleep(1)
    
    def cleanup_loop(self):
        """Background thread to remove expired overlays"""
        while self.is_running:
            try:
                current_time = time.time()
                expired_ids = []
                
                # Check each overlay
                for overlay_id, data in list(self.overlay_data.items()):
                    if current_time >= data['expires_at']:
                        try:
                            data['window'].destroy()
                        except:
                            pass
                        expired_ids.append(overlay_id)
                
                # Remove expired
                for oid in expired_ids:
                    del self.overlay_data[oid]
                
                time.sleep(0.5)  # Check every 0.5 seconds
                
            except Exception as e:
                print(f"Cleanup error: {e}")
                time.sleep(1)
    
    def cache_cleanup_loop(self):
        """Background thread to clean old cache entries"""
        while self.is_running:
            try:
                current_time = time.time()
                cache_lifetime = self.cache_lifetime.get()
                
                # Remove expired cache entries
                expired_keys = []
                for key, data in list(self.translation_cache.items()):
                    if current_time - data['last_seen'] > cache_lifetime:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.translation_cache[key]
                
                if expired_keys:
                    print(f"🧹 Cleaned {len(expired_keys)} old cache entries")
                
                time.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Cache cleanup error: {e}")
                time.sleep(5)

    def detect_and_translate(self, img_array, offset=(0, 0)):
        """Detect Japanese text and create translation overlays"""
        try:
            print("🔍 Starting OCR detection...")

            result = self.ocr.predict(img_array)
            
            if not result or not isinstance(result, list) or not result[0]:
                print("⚠️ Empty or invalid OCR result")
                return

            data = result[0] 
            
            rec_texts = data.get("rec_texts", [])
            rec_scores = data.get("rec_scores", [])
            rec_polys = data.get("rec_polys", [])

            text_boxes = []
            
            for i, text in enumerate(rec_texts):
                if not text.strip():
                    continue

                if not re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9faf\uFF66-\uFF9D]', text):
                    continue

                confidence = rec_scores[i] if i < len(rec_scores) else 0
                if confidence < self.min_confidence.get():
                    continue

                poly_list = None
                if i < len(rec_polys):
                    poly_obj = rec_polys[i]
                    
                    try:
                        if isinstance(poly_obj, np.ndarray):
                            poly_list = poly_obj.tolist()
                        elif isinstance(poly_obj, list):
                            poly_list = poly_obj
                        elif isinstance(poly_obj, str):
                            if '...' not in poly_obj:
                                poly_list = eval(poly_obj)
                                if isinstance(poly_list, np.ndarray):
                                    poly_list = poly_list.tolist()
                    except Exception as e:
                        print(f"⚠️ Failed to parse polygon for line {i}: {e}")
                        poly_list = None
                
                text_boxes.append({
                    "text": text,
                    "box": poly_list,
                    "confidence": float(confidence)
                })

            print(f"📊 Parsed {len(text_boxes)} valid Japanese OCR boxes")

            # Process each text box
            for tb in text_boxes:
                try:
                    if tb["box"] is None:
                        continue
                    
                    # Calculate text hash for caching
                    text_hash = self.get_text_hash(tb["text"])
                    
                    # Check cache
                    if self.is_in_cache(text_hash):
                        print(f"💾 Cache hit: '{tb['text'][:20]}...'")
                        continue  # Skip - already translated
                    
                    # Translate
                    translation_result = self.translator.translate(tb["text"], src='ja', dest='en')
                    
                    if not translation_result or not translation_result.text:
                        continue
                    
                    translated = translation_result.text
                    
                    # Convert polygon to box
                    box = self._poly_to_box(tb["box"])
                    
                    # Adjust coordinates for region offset
                    box['x'] += offset[0]
                    box['y'] += offset[1]
                    
                    # Calculate duration based on text length
                    duration = self.calculate_duration(tb["text"])
                    
                    # Create overlay with timer
                    self.create_overlay_with_timer(box, translated, duration)
                    
                    # Add to cache
                    self.add_to_cache(text_hash, tb["text"], translated, box)
                    
                    print(f"✓ Translated: '{tb['text'][:20]}...' → '{translated[:30]}...' (duration: {duration}s)")
                        
                except Exception as e:
                    print(f"⚠️ Error processing text '{tb['text'][:20]}': {e}")

            print("✨ Detection complete!")

        except Exception as e:
            print("❌ Error in detect_and_translate:", e)
            import traceback
            traceback.print_exc()
    
    def get_text_hash(self, text):
        """Generate hash for text (for caching)"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def is_in_cache(self, text_hash):
        """Check if text is in cache and not expired"""
        if text_hash not in self.translation_cache:
            return False
        
        cache_entry = self.translation_cache[text_hash]
        current_time = time.time()
        
        # Check if expired
        if current_time - cache_entry['last_seen'] > self.cache_lifetime.get():
            del self.translation_cache[text_hash]
            return False
        
        return True
    
    def add_to_cache(self, text_hash, japanese_text, translation, box):
        """Add translation to cache"""
        self.translation_cache[text_hash] = {
            'japanese': japanese_text,
            'translation': translation,
            'last_seen': time.time(),
            'position_hash': hash((box['x'], box['y'], box['w'], box['h']))
        }
    
    def calculate_duration(self, text):
        """Calculate overlay duration based on text length"""
        length = len(text)
        
        if length < 15:
            return self.duration_short.get()
        elif length < 30:
            return self.duration_medium.get()
        else:
            return self.duration_long.get()

    def _poly_to_box(self, poly):
        """Converts a 4-point polygon to a simple [x, y, w, h] bounding box."""
        try:
            x_coords = [p[0] for p in poly]
            y_coords = [p[1] for p in poly]
            min_x = int(min(x_coords))
            min_y = int(min(y_coords))
            max_x = int(max(x_coords))
            max_y = int(max(y_coords))
            return {
                'x': min_x,
                'y': min_y,
                'w': max_x - min_x,
                'h': max_y - min_y
            }
        except Exception as e:
            print(f"Error converting polygon {poly}: {e}")
            return {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        
    def create_overlay_with_timer(self, box, translation, duration):
        """Create overlay window with individual timer"""
        try:
            overlay = tk.Toplevel(self.root)
            overlay.attributes('-topmost', True)
            overlay.attributes('-alpha', self.overlay_alpha.get())
            overlay.overrideredirect(True)
            
            # Position below detected text
            new_y = box['y'] + box['h'] - 5
            overlay.geometry(f"+{box['x']}+{new_y}")
            
            # Create label
            label = tk.Label(
                overlay,
                text=translation,
                bg='#FFFF99',
                fg='#000000',
                font=('Arial', int(self.font_size.get()), 'bold'),
                padx=6,
                pady=3,
                relief=tk.RIDGE,
                borderwidth=2,
                wraplength=max(300, box['w'])
            )
            label.pack()
            
            # Store with expiration time
            overlay_id = self.next_overlay_id
            self.next_overlay_id += 1
            
            self.overlay_data[overlay_id] = {
                'window': overlay,
                'translation': translation,
                'created_at': time.time(),
                'expires_at': time.time() + duration,
                'position': (box['x'], box['y'], box['w'], box['h'])
            }
            
        except Exception as e:
            print(f"Overlay error: {e}")
            
    def clear_all_overlays(self):
        """Remove all translation overlays"""
        for overlay_id, data in list(self.overlay_data.items()):
            try:
                data['window'].destroy()
            except:
                pass
        self.overlay_data.clear()
        self.translation_cache.clear()
        print("🗑️ All overlays and cache cleared")
    
    def on_exit(self):
        """Exit application"""
        self.stop_translation()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        print("=" * 50)
        print(f"🎮 Gaming Japanese Translator v{VERSION}")
        print("=" * 50)
        print("\n✨ NEW in v3.0:")
        print("  • Individual overlay timers (no flickering!)")
        print("  • Smart translation cache")
        print("  • Region selection for faster OCR")
        print("  • Text-length-based display duration")
        print("\nFirst run will download AI models (~10MB)")
        print("This is normal and only happens once!\n")
        
        app = GameTranslatorApp()
        app.run()
        
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()