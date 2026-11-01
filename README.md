<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vatrix Tweaker v1.2 - Official Launcher & Info</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background-color: #0b0c10;
            color: #c5c6c7;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }

        .container {
            max-width: 800px;
            width: 100%;
            text-align: center;
        }

        /* 1. Titlu și Animații */
        .main-title {
            font-size: 3.5rem;
            font-weight: 900;
            letter-spacing: 2px;
            background: linear-gradient(45deg, #ff007f, #7928ca, #00dfd8, #ff007f);
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 4s ease infinite;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .subtitle {
            color: #00dfd8;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 30px;
            text-shadow: 0 0 10px rgba(0, 223, 216, 0.4);
            animation: pulseGlow 2s ease-in-out infinite alternate;
        }

        @keyframes pulseGlow {
            from { opacity: 0.8; transform: scale(0.99); }
            to { opacity: 1; transform: scale(1.01); }
        }

        /* 2. Card Descriere Program */
        .info-card {
            background: #1f2833;
            border: 1px solid #45a29e;
            border-radius: 12px;
            padding: 25px;
            text-align: left;
            margin-bottom: 30px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        }

        .info-card h2 {
            color: #66fcf1;
            margin-bottom: 15px;
            font-size: 1.5rem;
            border-bottom: 1px solid #45a29e;
            padding-bottom: 8px;
        }

        .info-card p {
            line-height: 1.6;
            margin-bottom: 15px;
            color: #e5e5e5;
        }

        .features-list {
            list-style: none;
            margin-bottom: 20px;
        }

        .features-list li {
            position: relative;
            padding-left: 25px;
            margin-bottom: 10px;
            line-height: 1.4;
        }

        .features-list li::before {
            content: "⚡";
            position: absolute;
            left: 0;
            top: 0;
        }

        /* 3. Instrucțiuni Deschidere Executabil */
        .instructions-box {
            background: rgba(102, 252, 241, 0.05);
            border-left: 4px solid #66fcf1;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }

        .instructions-box h3 {
            color: #00dfd8;
            font-size: 1.1rem;
            margin-bottom: 8px;
        }

        .instructions-box ol {
            margin-left: 20px;
            line-height: 1.5;
        }

        /* 4. Modul Selectare & Lansare .EXE */
        .launcher-zone {
            background: #1f2833;
            border: 2px dashed #ff007f;
            border-radius: 12px;
            padding: 30px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .launcher-zone:hover {
            border-color: #00dfd8;
            background: #253342;
            box-shadow: 0 0 15px rgba(0, 223, 216, 0.3);
        }

        .file-input {
            display: none;
        }

        .btn-select {
            display: inline-block;
            background: linear-gradient(45deg, #ff007f, #7928ca);
            color: #fff;
            padding: 12px 24px;
            font-weight: bold;
            border-radius: 6px;
            margin-top: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: transform 0.2s;
        }

        .btn-select:hover {
            transform: scale(1.05);
        }

        /* Mesaje Stare */
        .status-message {
            margin-top: 20px;
            font-family: monospace;
            font-size: 1.1rem;
            font-weight: bold;
            min-height: 24px;
        }

        .status-success {
            color: #00dfd8;
            text-shadow: 0 0 8px rgba(0, 223, 216, 0.6);
        }

        .status-error {
            color: #ff007f;
            text-shadow: 0 0 8px rgba(255, 0, 127, 0.6);
        }
    </style>
</head>
<body>

    <div class="container">
        <!-- Titlu principal -->
        <h1 class="main-title">VATRIX TWEAKER</h1>
        <p class="subtitle">Versiunea 1.2 • Utilitar de Optimizare Windows</p>

        <!-- Prezentare Program -->
        <div class="info-card">
            <h2>Despre Vatrix Tweaker</h2>
            <p><strong>Vatrix Tweaker</strong> este o aplicație desktop open-source concepută pentru optimizarea rapidă a sistemului de operare Windows. Aceasta ajută la eliberarea resurselor hardware și la îmbunătățirea performanței generale.</p>
            
            <ul class="features-list">
                <li><strong>Eliberare RAM:</strong> Curățare rapidă a memoriei cache neutilizate.</li>
                <li><strong>Management Startup:</strong> Activare sau dezactivare simplă a aplicațiilor la pornire.</li>
                <li><strong>Manager de Pachete:</strong> Integrat cu <code>winget</code> pentru instalarea rapidă a programelor esențiale.</li>
                <li><strong>Optimizări de Sistem:</strong> Aplicare de tweak-uri pentru reducerea latenței în jocuri și aplicații.</li>
            </ul>

            <!-- Ghid deschidere program -->
            <div class="instructions-box">
                <h3>Cum se deschide programul:</h3>
                <ol>
                    <li>Rulați fișierul executabil <code>Vatrix.exe</code> pe un sistem cu <strong>Windows 10 sau 11</strong>.</li>
                    <li>Dacă apare o alertă <em>Windows SmartScreen</em>, apăsați pe <strong>"Mai multe informații"</strong> (More info) și apoi pe <strong>"Rulați oricum"</strong> (Run anyway).</li>
                    <li>Pentru utilizarea funcțiilor avansate (optimizări registri sau oprirea serviciilor de sistem), se recomandă deschiderea cu <strong>Drepturi de Administrator</strong> (Right-Click &rarr; <em>Run as Administrator</em>).</li>
                </ol>
            </div>
        </div>

        <!-- Lansator Executabil -->
        <div class="launcher-zone" onclick="document.getElementById('fileInput').click()">
            <p style="font-size: 1.2rem; font-weight: bold;">Selectați fișierul aplicației pentru lansare</p>
            <p style="color: #8892b0; font-size: 0.9rem; margin-top: 5px;">Se acceptă exclusiv fișiere cu extensia <strong>.exe</strong></p>
            <div class="btn-select">Alege fișierul (.exe)</div>
            <input type="file" id="fileInput" class="file-input" accept=".exe" onchange="validateAndLaunch(this)">
        </div>

        <!-- Zona de feedback -->
        <div id="statusMessage" class="status-message"></div>
    </div>

    <script>
        function validateAndLaunch(input) {
            const statusDiv = document.getElementById('statusMessage');
            const file = input.files[0];

            if (!file) {
                statusDiv.innerText = "";
                return;
            }

            // Verificare extensie .exe
            if (file.name.toLowerCase().endsWith('.exe')) {
                statusDiv.className = "status-message status-success";
                statusDiv.innerText = `[SUCCESS] Fișierul "${file.name}" a fost validat! Se inițializează lansarea Vatrix Tweaker...`;
            } else {
                statusDiv.className = "status-message status-error";
                statusDiv.innerText = `[EROARE] Tip de fișier nepermis! Puteți deschide doar fișiere executabile (.exe).`;
                input.value = ""; // Resetează selecția
            }
        }
    </script>

</body>
</html>
