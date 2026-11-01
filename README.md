<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vatrix Tweaker v1.2 - Cyberpunk Launcher & Portal</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        cyber: {
                            bg: '#0b0c10',
                            card: '#1f2833',
                            accent: '#66fcf1',
                            cyan: '#00dfd8',
                            pink: '#ff007f',
                            purple: '#7928ca',
                            darkText: '#c5c6c7'
                        }
                    },
                    fontFamily: {
                        mono: ['Fira Code', 'JetBrains Mono', 'monospace'],
                        sans: ['Inter', 'Segoe UI', 'sans-serif']
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&family=Inter:wght@400;600;800;900&display=swap');

        body {
            font-family: 'Inter', sans-serif;
            background-color: #0b0c10;
            color: #c5c6c7;
            overflow-x: hidden;
        }

        /* 1. Gradient Animat Multi-Color pe Titlu */
        .animated-gradient-title {
            background: linear-gradient(
                135deg,
                #ff007f,
                #7928ca,
                #00dfd8,
                #66fcf1,
                #ff007f
            );
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientShift 4s ease infinite;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* 2. Glow & Pulsing Subtext */
        .neon-glow-subtext {
            color: #00dfd8;
            text-shadow: 0 0 10px rgba(0, 223, 216, 0.5),
                         0 0 20px rgba(0, 223, 216, 0.3);
            animation: pulseGlow 2.5s ease-in-out infinite alternate;
        }

        @keyframes pulseGlow {
            0% {
                opacity: 0.8;
                transform: scale(0.99);
                text-shadow: 0 0 8px rgba(0, 223, 216, 0.4);
            }
            100% {
                opacity: 1;
                transform: scale(1.01);
                text-shadow: 0 0 25px rgba(0, 223, 216, 0.9),
                             0 0 35px rgba(121, 40, 202, 0.8);
            }
        }

        /* Card Cyberpunk Styling */
        .cyber-card {
            background: rgba(31, 40, 51, 0.75);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(0, 223, 216, 0.25);
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8);
            transition: all 0.3s ease;
        }

        .cyber-card:hover {
            border-color: rgba(0, 223, 216, 0.5);
            box-shadow: 0 0 25px rgba(0, 223, 216, 0.15);
        }

        /* Terminal Typing Cursor */
        .typing-cursor::after {
            content: '█';
            display: inline-block;
            margin-left: 2px;
            color: #ff007f;
            animation: blink 0.8s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        /* Drag Zone Active Highlight */
        .drag-over {
            border-color: #00dfd8 !important;
            background-color: rgba(0, 223, 216, 0.1) !important;
            box-shadow: 0 0 30px rgba(0, 223, 216, 0.3) !important;
        }

        /* Glitch Border Animation for Error */
        .error-shake {
            animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both;
        }

        @keyframes shake {
            10%, 90% { transform: translate3d(-1px, 0, 0); }
            20%, 80% { transform: translate3d(2px, 0, 0); }
            30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
            40%, 60% { transform: translate3d(4px, 0, 0); }
        }
    </style>
</head>
<body class="min-h-screen flex flex-col justify-between items-center p-4 sm:p-8 relative">

    <!-- Ambient Glowing Background Elements -->
    <div class="fixed top-[-10%] left-[-10%] w-[500px] h-[500px] bg-cyber-pink/20 rounded-full blur-[130px] pointer-events-none"></div>
    <div class="fixed bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-cyber-cyan/20 rounded-full blur-[130px] pointer-events-none"></div>

    <!-- Header Section -->
    <header class="text-center max-w-4xl mt-4 sm:mt-8 z-10 w-full">
        <div class="inline-flex items-center space-x-2 px-4 py-1.5 mb-4 rounded-full border border-cyber-pink/40 bg-cyber-pink/10 text-cyber-pink text-xs font-mono font-semibold tracking-widest uppercase shadow-[0_0_15px_rgba(255,0,127,0.2)]">
            <span class="w-2 h-2 rounded-full bg-cyber-pink animate-ping"></span>
            <span>SYSTEM OPTIMIZER V1.2</span>
        </div>

        <h1 class="text-5xl sm:text-7xl font-black tracking-tight uppercase mb-2 animated-gradient-title">
            VATRIX TWEAKER
        </h1>

        <p class="neon-glow-subtext text-xl sm:text-2xl font-bold tracking-wide mb-6">
            Versiunea 1.2 • Utilitar de Optimizare Windows
        </p>

        <!-- Live Terminal Typing Header -->
        <div class="w-full max-w-2xl mx-auto bg-black/70 border border-gray-800 rounded-lg p-3 text-left font-mono text-xs sm:text-sm text-gray-300 shadow-inner">
            <div class="flex items-center space-x-2 border-b border-gray-800 pb-2 mb-2">
                <span class="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                <span class="text-gray-500 text-xs ml-2">vatrix_status.sh</span>
            </div>
            <p id="typing-terminal-text" class="typing-cursor text-cyber-cyan"></p>
        </div>
    </header>

    <!-- Main Content Container -->
    <main class="w-full max-w-4xl my-8 z-10 grid grid-cols-1 lg:grid-cols-12 gap-8">

        <!-- LEFT COLUMN: App Description & How-To (7 cols) -->
        <section class="lg:col-span-7 flex flex-col space-y-6">
            
            <!-- Description Card -->
            <div class="cyber-card rounded-2xl p-6 sm:p-8">
                <div class="flex items-center space-x-3 mb-4">
                    <div class="p-2 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 text-cyber-cyan">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                    </div>
                    <h2 class="text-2xl font-black text-white uppercase tracking-wider">Despre Program</h2>
                </div>

                <p class="text-gray-300 leading-relaxed text-sm sm:text-base mb-6">
                    <strong class="text-cyber-cyan">Vatrix Tweaker</strong> este un utilitar desktop open-source creat în <strong>Python și PySide6</strong>, conceput special pentru curățarea, fluidizarea și optimizarea performanțelor sistemelor Windows 10 și 11.
                </p>

                <h3 class="text-xs font-mono font-bold text-gray-400 uppercase tracking-widest mb-3">Funcționalități Principale:</h3>
                
                <ul class="space-y-3 font-mono text-xs sm:text-sm">
                    <li class="flex items-start space-x-2 bg-black/30 p-2.5 rounded-lg border border-gray-800">
                        <span class="text-cyber-pink font-bold">▶</span>
                        <span class="text-gray-200"><strong class="text-cyber-cyan">RAM Flushing:</strong> Eliberează memoria RAM neutilizată și memoria cache a proceselor.</span>
                    </li>
                    <li class="flex items-start space-x-2 bg-black/30 p-2.5 rounded-lg border border-gray-800">
                        <span class="text-cyber-pink font-bold">▶</span>
                        <span class="text-gray-200"><strong class="text-cyber-cyan">Startup Management:</strong> Controlează aplicațiile de la pornirea Windows pentru boot rapid.</span>
                    </li>
                    <li class="flex items-start space-x-2 bg-black/30 p-2.5 rounded-lg border border-gray-800">
                        <span class="text-cyber-pink font-bold">▶</span>
                        <span class="text-gray-200"><strong class="text-cyber-cyan">Winget Package Manager:</strong> Căutare și instalare rapidă de software fără instrucțiuni CLI.</span>
                    </li>
                    <li class="flex items-start space-x-2 bg-black/30 p-2.5 rounded-lg border border-gray-800">
                        <span class="text-cyber-pink font-bold">▶</span>
                        <span class="text-gray-200"><strong class="text-cyber-cyan">System Tweaks:</strong> Ajustări fine ale sistemului pentru scăderea latenței în jocuri.</span>
                    </li>
                </ul>
            </div>

            <!-- How To Launch Card -->
            <div class="cyber-card rounded-2xl p-6 sm:p-8">
                <div class="flex items-center space-x-3 mb-4">
                    <div class="p-2 rounded-lg bg-cyber-pink/10 border border-cyber-pink/30 text-cyber-pink">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <h2 class="text-2xl font-black text-white uppercase tracking-wider">Cum se Deschide</h2>
                </div>

                <ol class="space-y-4 text-xs sm:text-sm text-gray-300">
                    <li class="flex items-start space-x-3">
                        <span class="bg-cyber-cyan text-black font-black w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">1</span>
                        <span>Descărcați și executați fișierul <code class="text-cyber-cyan font-mono bg-black/50 px-2 py-0.5 rounded">Vatrix.exe</code> pe Windows 10 sau 11.</span>
                    </li>
                    <li class="flex items-start space-x-3">
                        <span class="bg-cyber-cyan text-black font-black w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">2</span>
                        <span>Dacă apare avertismentul <em>Windows SmartScreen</em>, apăsați pe <strong>"Mai multe informații" (More info)</strong> și apoi pe <strong>"Rulați oricum" (Run anyway)</strong>.</span>
                    </li>
                    <li class="flex items-start space-x-3">
                        <span class="bg-cyber-cyan text-black font-black w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">3</span>
                        <span>Pentru a aplica modificările profunde în registri și servicii, deschideți aplicația dând <strong>Click dreapta &rarr; Execută ca administrator (Run as Administrator)</strong>.</span>
                    </li>
                </ol>
            </div>

        </section>

        <!-- RIGHT COLUMN: Interactive Executable Launcher & File Dropper (5 cols) -->
        <section class="lg:col-span-5 flex flex-col justify-start">
            <div class="cyber-card rounded-2xl p-6 sm:p-8 sticky top-8">
                
                <div class="flex items-center justify-between pb-4 mb-6 border-b border-gray-800">
                    <div class="flex items-center space-x-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-cyber-pink"></span>
                        <h3 class="font-mono text-xs font-bold text-gray-300 uppercase">Lansator Executabil</h3>
                    </div>
                    <span class="font-mono text-[10px] bg-cyber-pink/20 text-cyber-pink px-2 py-0.5 rounded border border-cyber-pink/40">
                        STRICT .EXE
                    </span>
                </div>

                <!-- File Drop Zone -->
                <div id="drop-zone" 
                     class="border-2 border-dashed border-gray-700 hover:border-cyber-cyan/70 rounded-xl p-8 text-center bg-black/40 transition-all duration-300 cursor-pointer group flex flex-col items-center justify-center space-y-4">
                    
                    <input type="file" id="file-input" class="hidden" accept=".exe">

                    <div id="drop-icon-container" class="w-16 h-16 rounded-full bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center group-hover:scale-110 group-hover:border-cyber-cyan transition-all">
                        <svg class="w-8 h-8 text-cyber-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                        </svg>
                    </div>

                    <div>
                        <p class="text-sm font-semibold text-gray-200">
                            Trage fișierul <span class="text-cyber-cyan font-mono font-bold">.exe</span> aici
                        </p>
                        <p class="text-xs text-gray-500 mt-1">
                            sau apasă pentru a explora calculatorul
                        </p>
                    </div>
                </div>

                <!-- Preset Fast Launch Button -->
                <button id="preset-launch-btn" 
                        class="w-full mt-4 py-3.5 px-4 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white bg-gradient-to-r from-cyber-pink via-cyber-purple to-cyber-cyan hover:opacity-90 active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(255,0,127,0.3)] flex items-center justify-center space-x-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
                    </svg>
                    <span>Lansează Vatrix.exe</span>
                </button>

                <!-- Status & Interactive Terminal Feedback -->
                <div id="status-card" class="mt-6 hidden p-4 rounded-xl border font-mono text-xs transition-all duration-300">
                    <div id="status-header" class="flex items-center space-x-2 mb-2 font-bold text-sm"></div>
                    <p id="status-message" class="text-gray-300 leading-relaxed mb-3"></p>

                    <!-- Interactive Progress Bar (Shown on Success) -->
                    <div id="progress-container" class="hidden w-full bg-black/60 rounded-full h-2.5 overflow-hidden border border-gray-800">
                        <div id="progress-bar" class="bg-gradient-to-r from-cyber-pink to-cyber-cyan h-2.5 w-0 transition-all duration-300"></div>
                    </div>

                    <!-- Mini Execution Console Log -->
                    <div id="console-log" class="hidden mt-3 p-2 bg-black/80 rounded border border-gray-900 text-[10px] text-gray-400 font-mono space-y-1 max-h-28 overflow-y-auto"></div>
                </div>

            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="text-center text-xs text-gray-500 z-10 my-6 font-mono">
        <p>© 2026 David • Licensed under <span class="text-cyber-cyan font-bold">MIT LICENSE</span></p>
        <p class="mt-1">Vatrix Tweaker v1.2 — Windows Optimization Utility</p>
    </footer>

    <!-- Interactive Script -->
    <script>
        // DOM Elements
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const presetBtn = document.getElementById('preset-launch-btn');
        const statusCard = document.getElementById('status-card');
        const statusHeader = document.getElementById('status-header');
        const statusMessage = document.getElementById('status-message');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const consoleLog = document.getElementById('console-log');
        const typingTerminal = document.getElementById('typing-terminal-text');

        // Typing Terminal Animation logic
        const terminalPhrases = [
            "> System initialize: Vatrix Tweaker v1.2",
            "> Ready for RAM flushing and Windows optimizations.",
            "> Waiting for executable file (.exe)..."
        ];
        let phraseIndex = 0;
        let charIndex = 0;
        let isDeleting = false;

        function typeLoop() {
            const currentPhrase = terminalPhrases[phraseIndex];
            
            if (isDeleting) {
                typingTerminal.textContent = currentPhrase.substring(0, charIndex--);
            } else {
                typingTerminal.textContent = currentPhrase.substring(0, charIndex++);
            }

            let typeSpeed = isDeleting ? 30 : 60;

            if (!isDeleting && charIndex === currentPhrase.length + 1) {
                typeSpeed = 2000;
                isDeleting = true;
            } else if (isDeleting && charIndex === 0) {
                isDeleting = false;
                phraseIndex = (phraseIndex + 1) % terminalPhrases.length;
                typeSpeed = 500;
            }

            setTimeout(typeLoop, typeSpeed);
        }
        typeLoop();

        // Drag & Drop Listeners
        dropZone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                processFile(files[0].name);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (fileInput.files.length > 0) {
                processFile(fileInput.files[0].name);
            }
        });

        presetBtn.addEventListener('click', () => {
            processFile("Vatrix.exe");
        });

        // Strict Validation & Execution Simulation
        function processFile(fileName) {
            const isExe = fileName.toLowerCase().endsWith('.exe');

            statusCard.classList.remove('hidden', 'bg-red-950/40', 'border-red-500/50', 'text-red-200', 'bg-emerald-950/40', 'border-emerald-500/50', 'text-emerald-200', 'error-shake');
            consoleLog.innerHTML = "";
            progressBar.style.width = '0%';

            if (isExe) {
                // SUCCESS: Valid EXE
                statusCard.classList.add('bg-emerald-950/40', 'border-emerald-500/50', 'text-emerald-200');
                statusHeader.innerHTML = `
                    <span class="w-3 h-3 rounded-full bg-emerald-400 animate-ping inline-block"></span>
                    <span class="text-emerald-400 font-bold uppercase tracking-wider">Lansare Executabilă Permisă</span>
                `;
                statusMessage.textContent = `Fișierul "${fileName}" este un executabil valid. Se inițializează Vatrix Tweaker v1.2...`;
                
                progressContainer.classList.remove('hidden');
                consoleLog.classList.remove('hidden');

                simulateExecution(fileName);

            } else {
                // FAILURE: Non-EXE file
                statusCard.classList.add('bg-red-950/40', 'border-red-500/50', 'text-red-200', 'error-shake');
                statusHeader.innerHTML = `
                    <span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span>
                    <span class="text-red-400 font-bold uppercase tracking-wider">Eroare Format Nepermis</span>
                `;
                statusMessage.innerHTML = `<strong class="text-red-400 font-bold">Doar fișierele .exe sunt permise!</strong> Fișierul selectat (<em>"${fileName}"</em>) a fost respins de sistem.`;
                
                progressContainer.classList.add('hidden');
                consoleLog.classList.add('hidden');
            }
        }

        // Simulate CLI Process Output for EXE launch
        function simulateExecution(fileName) {
            const logs = [
                `[INIT] Validare antet PE pentru ${fileName}...`,
                `[SYS] Drepturi Administrator verificate.`,
                `[PY] Încărcare PySide6 GUI runtime...`,
                `[OK] Vatrix Tweaker v1.2 pornit cu succes!`
            ];

            let step = 0;
            const interval = setInterval(() => {
                if (step < logs.length) {
                    const logItem = document.createElement('div');
                    logItem.textContent = logs[step];
                    consoleLog.appendChild(logItem);
                    consoleLog.scrollTop = consoleLog.scrollHeight;
                    
                    step++;
                    progressBar.style.width = `${(step / logs.length) * 100}%`;
                } else {
                    clearInterval(interval);
                }
            }, 350);
        }
    </script>
</body>
</html>
