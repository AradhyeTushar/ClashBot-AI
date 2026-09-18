document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Simple terminal typing effect
    const terminalLines = [
        "[+] Initializing Gemini Flash Tactical Brain...",
        "[+] Connected to VPS 200.234.41.58:29171",
        "[*] Capturing Frame (Latency: 12ms)",
        "[+] Target Detected: Eagle Artillery",
        "[✓] Funnel Deployed Successfully."
    ];
    
    const terminalBody = document.querySelector('.mockup-body code');
    if (terminalBody) {
        terminalBody.innerHTML = '';
        let lineIndex = 0;
        
        function typeLine() {
            if (lineIndex < terminalLines.length) {
                terminalBody.innerHTML += terminalLines[lineIndex] + '<br>';
                lineIndex++;
                setTimeout(typeLine, 800);
            } else {
                setTimeout(() => {
                    terminalBody.innerHTML = '';
                    lineIndex = 0;
                    typeLine();
                }, 5000);
            }
        }
        
        typeLine();
    }
});
