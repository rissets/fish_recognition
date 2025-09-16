# Django Fish Recognition API

Real-time fish recognition system menggunakan Django REST API dengan WebSocket untuk komunikasi real-time. Sistem ini mengintegrasikan engine dari `realtime_fish_recognition.py` untuk deteksi dan klasifikasi ikan secara real-time.

## Fitur Utama

- **Real-time Fish Detection**: Deteksi ikan real-time menggunakan kamera dengan FPS hingga 60
- **WebSocket Integration**: Komunikasi real-time antara frontend dan backend
- **REST API**: Endpoint API untuk processing gambar dan management session
- **Image Upload**: Upload dan analisis gambar statis
- **Web Interface**: Interface HTML modern untuk testing dan monitoring
- **Session Management**: Tracking session deteksi dan statistik
- **Performance Controls**: Kontrol FPS, kualitas frame, dan mode high-speed
- **Species Tracking**: List spesies ikan yang terdeteksi dengan counter
- **Real-time Statistics**: Monitoring performa dan akurasi secara real-time

## Struktur Project

```
django_fish_api/
├── fish_project/              # Django project settings
│   ├── __init__.py
│   ├── settings.py           # Konfigurasi Django
│   ├── urls.py              # URL routing utama
│   ├── asgi.py              # ASGI configuration untuk WebSocket
│   └── wsgi.py              # WSGI configuration
├── fish_recognition/          # Main Django app
│   ├── __init__.py
│   ├── apps.py              # App configuration
│   ├── models.py            # Database models
│   ├── views.py             # REST API views
│   ├── serializers.py       # DRF serializers
│   ├── consumers.py         # WebSocket consumers
│   ├── routing.py           # WebSocket routing
│   └── urls.py              # URL patterns
├── templates/                 # HTML templates
│   └── fish_recognition/
│       └── index.html       # Main interface
├── static/                   # Static files (CSS, JS, images)
├── manage.py                 # Django management script
└── requirements.txt          # Python dependencies
```

## Instalasi dan Setup

### 1. Clone Repository
```bash
cd /Users/user/Dev/researchs/fish_recognition/django_fish_api
```

### 2. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Atau menggunakan virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
pip install -r requirements.txt
```

### 3. Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 5. Collect Static Files
```bash
python manage.py collectstatic
```

## Menjalankan Aplikasi

### Development Server
```bash
python manage.py runserver
```

Aplikasi akan berjalan di: `http://localhost:8000`

### Production Deployment
```bash
# Using Gunicorn
gunicorn fish_project.asgi:application -k uvicorn.workers.UvicornWorker

# Atau dengan Docker (akan dibuat Dockerfile terpisah)
```

## API Endpoints

### REST API Endpoints

#### Sessions Management
- `GET /api/sessions/` - List semua session
- `POST /api/sessions/` - Buat session baru
- `GET /api/sessions/{id}/` - Detail session
- `POST /api/sessions/{id}/end_session/` - End session
- `GET /api/sessions/active_sessions/` - List active sessions

#### Fish Detections
- `GET /api/detections/` - List deteksi
- `GET /api/detections/?session_id={session_id}` - Filter by session
- `GET /api/detections/statistics/` - Statistik deteksi

#### Image Processing
- `POST /api/process-image/` - Upload dan process gambar
- `POST /api/process-frame/` - Process single frame (base64)

#### System Info
- `GET /api/stats/` - System statistics
- `GET /api/websocket-info/` - WebSocket connection info
- `GET /api/health/` - Health check

### WebSocket Endpoints

#### Real-time Recognition
- **URL**: `ws://localhost:8000/ws/fish-recognition/`
- **Messages**:
  - `start_recognition` - Mulai deteksi real-time
  - `stop_recognition` - Stop deteksi
  - `process_frame` - Process single frame
  - `get_status` - Get system status

#### Image Upload Processing
- **URL**: `ws://localhost:8000/ws/image-upload/`
- **Messages**:
  - `process_image` - Process uploaded image

## Konfigurasi

### Settings Penting

File: `fish_project/settings.py`

```python
# Fish Recognition specific settings
FISH_RECOGNITION_SETTINGS = {
    'MODEL_DIRS': {
        'classification': os.path.join(BASE_DIR.parent, 'models', 'classification'),
        'segmentation': os.path.join(BASE_DIR.parent, 'models', 'segmentation'),
        'detection': os.path.join(BASE_DIR.parent, 'models', 'detection'),
        'face': os.path.join(BASE_DIR.parent, 'models', 'face_detector')
    },
    'CAMERA_ID': 0,
    'SKIP_FRAMES': 0,  # Process every frame for higher FPS and real-time experience
    'CONF_THRESHOLD': 0.5,  # Lower threshold for more detections
    'NMS_THRESHOLD': 0.3,
    'FACE_CONF_THRESHOLD': 0.69,
    'FACE_NMS_THRESHOLD': 0.5,
    'FRAME_QUALITY': 70,  # JPEG quality for streaming (lower = faster)
    'FRAME_RESIZE': (640, 480),  # Resize frames for faster processing
    'MAX_FPS': 30,  # Target FPS
}
}
```

### Environment Variables (Optional)

Buat file `.env` untuk production:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/1
```

## Penggunaan

### 1. Web Interface

Akses `http://localhost:8000` untuk menggunakan interface web:

- **Live Camera Feed**: Real-time deteksi menggunakan kamera
- **Image Upload**: Upload gambar untuk analisis
- **Statistics**: Monitoring statistik deteksi
- **System Log**: Log aktivitas sistem

### 2. API Usage Examples

#### Start Detection Session
```python
import requests

# Create new session
response = requests.post('http://localhost:8000/api/sessions/')
session_data = response.json()
session_id = session_data['session_id']

# Process image
with open('fish_image.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:8000/api/process-image/', files=files)
    result = response.json()
    print(f"Detected {result['fish_count']} fish")
```

#### WebSocket Usage (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/fish-recognition/');

ws.onopen = function() {
    // Start detection
    ws.send(JSON.stringify({
        type: 'start_recognition',
        camera_id: 0
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'recognition_result') {
        console.log('Fish detected:', data.data.fish_results);
    }
};
```

## Integrasi dengan realtime_fish_recognition.py

Engine deteksi menggunakan class `RealTimeFishRecognition` dari file utama:

1. **Model Loading**: Sama dengan implementasi asli
2. **Frame Processing**: Menggunakan method `_process_frame()`
3. **Camera Integration**: Support multiple camera sources
4. **Performance Optimization**: Frame skipping dan async processing

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Pastikan Django Channels terinstall
   - Check ASGI configuration
   - Verify WebSocket URL

2. **Model Loading Error**
   - Pastikan path model sesuai dengan `FISH_RECOGNITION_SETTINGS`
   - Check model files existence
   - Verify PyTorch installation

3. **Camera Access Error**
   - Check camera permissions
   - Try different camera ID (0, 1, 2)
   - Verify OpenCV installation

4. **Performance Issues**
   - Adjust `SKIP_FRAMES` setting
   - Reduce model confidence threshold
   - Use smaller input resolution

### Debug Mode

Enable debug logging:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'fish_recognition': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Production Deployment

### Using Docker

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "fish_project.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Using Nginx + Gunicorn

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
}
```

## Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - lihat file LICENSE untuk detail.

## Support

Untuk pertanyaan dan support:
- Create issue di GitHub repository
- Contact: [your-email@domain.com]

---

**Note**: Pastikan model AI (`models/` directory) tersedia dan kompatibel dengan format yang diharapkan oleh `realtime_fish_recognition.py`.