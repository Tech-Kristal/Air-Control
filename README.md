# AirControl OS
### Gesture-Based Desktop Control System

<p align="center">
  <strong>Control your computer. Without touching it.</strong>
</p>

AirControl OS (also known as **Gesture OS**) is a Python-based gesture-control system designed to transform the way users interact with their computers.

Using computer vision and real-time hand tracking, AirControl interprets hand gestures and translates them into computer commands, allowing users to interact with their desktop through natural hand movements.

The goal is to build a touchless computer interaction environment where your hands become your controller.

---

## Features

- **Real-Time Hand Tracking** – Detects and tracks hand landmarks using computer vision.
- **Gesture Recognition** – Interprets finger positions and hand movements.
- **Desktop Interaction** – Converts recognized gestures into computer actions.
- **Keyboard & Mouse Control** – Designed to support touchless input.
- **Application Navigation** – Gesture-based desktop and application navigation.
- **Tab Switching** – Navigate between open browser tabs using gestures.
- **Visual Interface** – Desktop interface built with PyQt6.
- **Modular Architecture** – Designed to support additional gestures and controls.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| OpenCV | Camera input and computer vision |
| MediaPipe | Hand landmark detection |
| PyQt6 | Graphical user interface |
| NumPy | Numerical processing |
| Hand Landmarker | Hand tracking model |

## Project Structure

```text
AirControl-OS/
│
├── models/
│   └── hand_landmarker.task
│
├── src/
│   ├── camera/
│   ├── gestures/
│   ├── tracking/
│   ├── controls/
│   └── interface/
│
├── assets/
├── config/
├── requirements.txt
├── run.py
└── README.md
```

*The structure above represents the intended modular organization; adjust it to match the actual repository.*

## How It Works

AirControl follows a computer-vision-based interaction pipeline:

```text
        Webcam Input
             |
             v
       Frame Capture
             |
             v
      Hand Detection
             |
             v
     Landmark Tracking
             |
             v
     Gesture Recognition
             |
             v
      Action Mapping
             |
             v
       Desktop Control
```

1. The webcam captures real-time video.
2. MediaPipe detects the user's hand.
3. Hand landmarks are extracted and analyzed.
4. The gesture recognition system identifies hand movements.
5. The corresponding desktop action is triggered.

## Installation

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd AirControl-OS
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python run.py
```

Make sure your webcam is connected and the required hand-tracking model is available in the `models/` directory.

## Development Goals

AirControl OS is an evolving project. Future development aims to introduce:

- More advanced gesture recognition.
- Customizable gesture-to-action mapping.
- Improved hand-tracking accuracy.
- Multi-hand gesture support.
- System volume and brightness control.
- Window management.
- Virtual mouse and keyboard.
- Application launching through gestures.
- Custom gesture profiles.
- AI-assisted gesture recognition.

## Vision

The long-term vision of AirControl OS is to create a complete gesture-driven interaction layer for desktop computers.

Instead of relying entirely on a keyboard, mouse, or touchscreen, users will be able to interact with their operating system through intuitive hand movements.

**AirControl OS — A new way to interact with your computer.**

---

## Author

**Kristal Poudel**

Project: AirControl OS / Gesture OS  
Language: Python  
Category: Computer Vision · Human-Computer Interaction · Gesture Recognition

---

*This project is actively under development. Features and architecture may evolve over time.*
