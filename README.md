# 🚀 Lenovo Emotion AI Framework

This is a multi-tab application framework built with Gradio, focusing on emotion AI functionality. Each tab corresponds to Python code in different subdirectories. This framework provides basic interface structure, and you can add specific functionality as needed in each subdirectory.

## 📁 Project Structure

```
LenovoEmotion/
├── main_app.py              # Main application file
├── requirements.txt          # Project dependencies
├── README.md                # Project documentation
├── data_analysis/           # Data analysis module
│   └── data_visualization.py
├── image_processing/        # Image processing module
│   └── image_editor.py
├── audio_processing/        # Audio processing module
│   └── audio_processor.py
└── text_analysis/           # Text analysis module
    └── text_processor.py
```

## 🛠️ Framework Structure

### 🔋 Emotion Battery Module
- Emotion battery functionality module
- Currently only displays "Hello World!" framework
- You can add emotion battery related functionality here
- Examples: emotion state monitoring, battery level display, emotion history records, etc.

### 📡 Realtime Emotion Module
- Real-time emotion monitoring module
- Currently only displays "Hello World!" framework
- You can add real-time emotion analysis functionality here
- Examples: real-time emotion recognition, emotion change tracking, emotion alerts, etc.

### 📊 Data Visualization Module (`data_analysis/`)
- Contains `data_visualization.py` file
- Currently only displays "Hello World!" framework
- You can add data analysis and visualization functionality here
- Examples: chart drawing, data analysis, statistical calculations, etc.

### 🖼️ Image Processing Module (`image_processing/`)
- Contains `image_editor.py` file
- Currently only displays "Hello World!" framework
- You can add image processing functionality here
- Examples: image filters, size adjustment, format conversion, etc.

### 🎵 Audio Processing Module (`audio_processing/`)
- Contains `audio_processor.py` file
- Currently only displays "Hello World!" framework
- You can add audio processing functionality here
- Examples: audio file processing, audio analysis, audio effects, etc.

### 📝 Text Analysis Module (`text_analysis/`)
- Contains `text_processor.py` file
- Currently only displays "Hello World!" framework
- You can add text analysis functionality here
- Examples: text preprocessing, sentiment analysis, keyword extraction, etc.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Application

```bash
python main_app.py
```

### 3. Access Application

The application will start locally at: `http://127.0.0.1:7861`

## 📋 Dependencies

- `gradio>=4.0.0` - Web interface framework

**Note**: This is a basic framework that only includes Gradio dependency. If you need to add specific functionality, please install the corresponding dependency packages as needed in each subdirectory.

## 💡 Usage Instructions

### Basic Usage
1. After running the application, you will see an interface with 6 tabs
2. The first two tabs are emotion-related modules, the last four are functional modules
3. Each tab currently only displays basic description information and "Hello World!"
4. You can add specific functionality as needed in these tabs

### Adding Functionality
1. Edit the corresponding Python files in each subdirectory
2. Add your specific functionality in the `create_*_interface()` functions
3. You can add Gradio components such as buttons, input boxes, charts, etc.
4. Install additional dependency packages as needed

### Examples
- View the Python files in each subdirectory to understand how to organize code
- These files demonstrate basic function structure that you can extend upon

## 🔧 Custom Extensions

### Adding New Modules
1. Create new subdirectories in the root directory
2. Create Python module files in the subdirectories
3. Import new modules in `main_app.py`
4. Add new tabs in the main interface

### Modifying Existing Modules
1. Directly edit the corresponding Python files in each subdirectory
2. Modify function logic or add new functionality
3. Update interface components and event bindings

## 🐛 Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure all dependency packages are correctly installed
   - Check Python path settings

2. **Interface Display Issues**
   - Ensure Gradio version compatibility
   - Check browser compatibility

### Log Viewing
The application will output detailed log information to the console during runtime, including error information and debugging information.

## 📄 License

This project uses MIT license. See LICENSE file for details.

## 🤝 Contributing

Welcome to submit Issues and Pull Requests to improve this project!

## 📞 Contact

For questions or suggestions, please contact through:
- Submit GitHub Issues
- Send email to project maintainers

---

**Enjoy using the Lenovo Emotion AI Framework!** 🎉
