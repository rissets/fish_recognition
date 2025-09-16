# Quick Start Guide

## Langkah Cepat untuk Menjalankan Aplikasi

### 1. Persiapan
```bash
cd /Users/user/Dev/researchs/fish_recognition/django_fish_api
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Database
```bash
python manage.py makemigrations fish_recognition
python manage.py migrate
```

### 4. Jalankan Server
```bash
python manage.py runserver
```

### 5. Akses Aplikasi
- Buka browser: `http://localhost:8000`
- Interface akan menampilkan:
  - Live camera feed untuk real-time detection
  - Upload area untuk analisis gambar
  - Statistics dan log monitoring

## Fitur Utama

1. **Real-time Detection**: Menggunakan WebSocket untuk streaming camera
2. **Image Upload**: Drag & drop atau upload gambar untuk analisis
3. **REST API**: Endpoint untuk integrasi dengan aplikasi lain
4. **Session Management**: Tracking dan statistik deteksi

## Troubleshooting

**Camera tidak terdeteksi?**
- Pastikan camera terhubung
- Coba ganti Camera ID (0, 1, 2) di dropdown

**Model error?**
- Pastikan folder `models/` ada di parent directory
- Check path model di `settings.py`

**WebSocket error?**
- Restart server Django
- Check browser console untuk error detail