# Packaging Box Optimizer

Aplikasi ini adalah sebuah tool untuk mengoptimalkan pengepakan barang (box) ke dalam kontainer menggunakan berbagai algoritma. Proyek ini terdiri dari:

-   **Frontend**: Dibuat dengan React, berada di direktori `storage-manager`.
-   **Backend**: Dibuat dengan Python (FastAPI), berada di direktori `storage-backend/python`.

## Prasyarat

Pastikan Anda telah menginstal perangkat lunak berikut di sistem operasi Windows Anda:

-   Python (versi 3.8 atau lebih baru)
-   Node.js (versi LTS direkomendasikan)
-   Git (opsional, untuk kloning repositori)

## Instalasi

Ikuti langkah-langkah berikut untuk menyiapkan proyek di lingkungan lokal Anda.

### 1. Kloning Repositori (Jika Diperlukan)

Jika Anda memiliki repositori git, klon terlebih dahulu. Jika tidak, lewati langkah ini dan pastikan Anda memiliki folder proyek.

```bash
git clone <URL_REPOSITORI_ANDA>
cd packaging-box
```

### 2. Setup Backend (Python/FastAPI)

Backend menangani logika komputasi untuk algoritma pengepakan.

1.  Buka Command Prompt atau PowerShell dan navigasi ke direktori backend:
    ```bash
    cd storage-backend\python
    ```

2.  Buat dan aktifkan virtual environment. Ini akan mengisolasi dependensi proyek Anda.
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
    Setelah aktivasi, Anda akan melihat `(venv)` di awal baris prompt Anda.

3.  Instal semua dependensi Python yang diperlukan dari file `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

    **Catatan tentang Gurobi:**
    `gurobipy` adalah solver optimisasi yang kuat dan mungkin memerlukan lisensi (termasuk lisensi akademik gratis). Jika Anda mengalami masalah saat instalasi atau penggunaan, silakan merujuk ke dokumentasi resmi Gurobi untuk panduan instalasi dan lisensi.

### 3. Setup Frontend (React)

Frontend menyediakan antarmuka pengguna untuk memasukkan data dan memvisualisasikan hasil.

1.  Buka terminal baru (biarkan terminal backend tetap berjalan) dan navigasi ke direktori frontend:
    ```bash
    cd storage-manager
    ```

2.  Instal semua dependensi Node.js:
    ```bash
    npm install
    ```
    *(Jika Anda menggunakan Yarn, jalankan `yarn install`)*

## Menjalankan Aplikasi

Setelah instalasi selesai, Anda perlu menjalankan kedua server (backend dan frontend) secara bersamaan.

### 1. Menjalankan Backend

1.  Pastikan Anda berada di direktori `storage-backend\python` dan virtual environment `venv` sudah aktif.
2.  Jalankan server FastAPI menggunakan Uvicorn:
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    -   `--reload`: Server akan otomatis restart jika ada perubahan pada kode.
    -   `--port 8000`: Menjalankan server di port 8000, sesuai dengan yang diharapkan oleh frontend.

    Server backend sekarang berjalan dan siap menerima permintaan di `http://localhost:8000`.

### 2. Menjalankan Frontend

1.  Pastikan Anda berada di direktori `storage-manager`.
2.  Jalankan server development React:
    ```bash
    npm start
    ```
    *(Jika Anda menggunakan Yarn, jalankan `yarn start`)*

    Ini akan secara otomatis membuka tab baru di browser Anda dengan alamat `http://localhost:3000` atau `http://localhost:5173`. Aplikasi sekarang siap digunakan.

## Cara Menggunakan

1.  Buka aplikasi di browser Anda (`http://localhost:3000` atau `http://localhost:5173`).
2.  Pilih preset kontainer dan barang, atau masukkan data Anda sendiri.
3.  Pilih algoritma pengepakan yang diinginkan.
4.  Klik tombol "Calculate & Visualize" untuk melihat hasil pengepakan dalam format 3D.