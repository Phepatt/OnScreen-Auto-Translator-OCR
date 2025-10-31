# GameTranslator (Gaming-Optimized Japanese Screen Translator)

## Features
- Real-time Japanese text detection and translation overlay
- Region selection for faster OCR
- Smart translation cache
- Individual overlay lifespans (no flickering)
- Memory efficient auto-cleanup
- GPU acceleration (if available)

## Requirements
- Windows 10/11
- NVIDIA GPU (for GPU acceleration)
- [Miniconda/Anaconda](https://docs.conda.io/en/latest/miniconda.html)

## Installation

### 1. Clone or Download the Project
```
# Download or clone to your desired folder
```

### 2. Create and Activate Conda Environment
```
conda create -n screen_translator python=3.10
conda activate screen_translator
```

### 3. Install Dependencies
```
pip install paddleocr paddlepaddle pillow googletrans numpy
```
- For GPU support, install PaddlePaddle with CUDA:
  - [PaddlePaddle GPU Install Guide](https://www.paddlepaddle.org.cn/install/quick)
  - Example for CUDA 11.2:
    ```
    pip install paddlepaddle-gpu==2.5.0.post112 -f https://paddlepaddle.org.cn/whl/mkl/avx/stable.html
    ```

### 4. Run the Program (Python)
```
python game_translator_paddleocr.py
```

### 5. Build Standalone EXE (Optional)
```
pip install pyinstaller
pyinstaller --name="GameTranslator" --onefile --windowed --hidden-import=PIL --hidden-import=paddleocr --hidden-import=googletrans --hidden-import=paddle --hidden-import=tkinter game_translator_paddleocr.py
```
- The EXE will be in the `dist/` folder.
- For GPU support, target machine must have CUDA drivers installed.

## Usage
- Start the app: overlays will appear for detected Japanese text.
- Use "Select Capture Region" to focus OCR on a specific area.
- Adjust settings for scan interval, confidence, font size, overlay opacity, and display duration.
- Click "Clear All Overlays" to remove translations.
- Exit with the "❌ Exit" button.

## Troubleshooting
- If GPU is not detected, PaddleOCR will run in CPU mode.
- For GPU errors, check CUDA and cuDNN installation.
- If overlays do not appear, ensure you have screen capture permissions.

## License
MIT

## Credits
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddlePaddle](https://github.com/PaddlePaddle/Paddle)
- [Googletrans](https://github.com/ssut/py-googletrans)
