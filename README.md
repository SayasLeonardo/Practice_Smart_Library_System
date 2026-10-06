# Smart Library System

The existing HTML and CSS are served by Flask, which also provides the SQLite-backed API.

## Step-by-step: run locally on Windows

You need Python installed and a camera connected for face recognition. Run the two applications in **two separate PowerShell terminals**, and keep both terminals open while using the system. Run all commands below from `C:\SmartLibrarySystem001`.

### 1. Set up and start the Smart Library backend

In PowerShell terminal 1:

```powershell
cd C:\SmartLibrarySystem001
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Generate a private key for communication between the backend and camera station:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the generated value for use in both terminals. Do not post it publicly or commit it to the repository. In terminal 1, set the key and start the backend:

```powershell
$env:SMART_LIBRARY_IOT_KEY = "paste-the-generated-key-here"
.\.venv\Scripts\python.exe backend\app.py
```

Leave this terminal running. Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) to use the main system. The SQLite database is `smart_library.db`; startup preserves existing accounts and records.

### 2. Set up and start Face Recognition / IoT

Open PowerShell terminal 2 and run:

```powershell
cd C:\SmartLibrarySystem001
python -m venv face_recognition_iot\.venv
.\face_recognition_iot\.venv\Scripts\python.exe -m pip install -r face_recognition_iot\requirements.txt
$env:SMART_LIBRARY_IOT_KEY = "paste-the-same-generated-key-here"
$env:SMART_LIBRARY_API_URL = "http://127.0.0.1:5000"
.\face_recognition_iot\.venv\Scripts\python.exe face_recognition_iot\app.py
```

Leave this terminal running too. On its first start, the station downloads the YuNet and SFace model files into the ignored `face_recognition_iot\.models` folder; an internet connection is needed for this download. Open [http://127.0.0.1:5001/](http://127.0.0.1:5001/) and wait for the station status to say the camera is ready.

### 3. Sign in and use face attendance

If the database has no users yet, the starter accounts are:

- MIS Admin: `admin@smartlibrary.local` / `admin123`
- Librarian: `librarian@smartlibrary.local` / `librarian123`

These are not replacement credentials for an existing database; existing accounts and passwords are preserved. Sign in as MIS Admin, add or select a person, and upload that person's face image. Then use the camera station, select **Time-in** or **Time-out**, and confirm the action after the person is recognized. Recognition alone does not record attendance.

### 4. Stop the applications

In each PowerShell terminal, press **Ctrl+C**. Stop the camera station first, then the main backend. Starting them again later requires setting the IoT key in both new terminals again; generate a new key if you no longer have the old one, and use that same new value for both services.

### Troubleshooting

- **Station cannot connect to the library API:** Check that terminal 1 is still running and that `SMART_LIBRARY_API_URL` is `http://127.0.0.1:5000`. Make sure both terminals have the identical `SMART_LIBRARY_IOT_KEY`.
- **Camera is unavailable:** Close other apps using the camera and allow camera access in Windows privacy settings. The station uses camera device `0` by default; to select another device, set `$env:SMART_LIBRARY_CAMERA = "1"` (or the desired device index) in terminal 2 before starting the station.
- **Models fail to download:** Check the internet connection, then restart the camera station. The model files are downloaded on startup when missing or incomplete.
- **PowerShell says the address is already in use:** Another copy is likely running. Stop it with **Ctrl+C** in its terminal before starting another copy.

The Flask development servers bind to `127.0.0.1` and are for local development, not production deployment. Change development passwords before any wider deployment; configure a strong `SMART_LIBRARY_SECRET` and HTTPS (`SMART_LIBRARY_HTTPS=1`) in a properly secured deployment.

## Empty-database starter accounts

These accounts are created only when the database contains no users. Existing accounts and passwords are preserved, and people records remain in their current database IDs.

- MIS Admin: `admin@smartlibrary.local` / `admin123`
- Librarian: `librarian@smartlibrary.local` / `librarian123`

Change these development passwords before exposing the system to a network. In a deployed environment, set a strong `SMART_LIBRARY_SECRET` and use HTTPS (`SMART_LIBRARY_HTTPS=1`).

## Roles and API

MIS Admin and Librarian accounts can use the dashboard, book catalog, borrowing/returns, attendance history, and reports. Only MIS Admins can manage people and system accounts. People records do not receive login passwords.

## Face Recognition / IoT

The main backend stores attendance sessions and face-registration metadata; use `/api/attendance/time-in` and `/api/attendance/time-out` through the camera client. See `face_recognition_iot/README.md` for its independent dependencies, models, and camera configuration. Camera frames and downloaded embeddings stay in memory; the main service stores compact face encodings and the uploaded registration image.