const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const inputJson = process.argv[2];
const outputWebm = process.argv[3];
const durationSeconds = parseFloat(process.argv[4] || "0");

if (!inputJson || !outputWebm) {
    console.error("Usage: node index.js <input.json> <output.webm> <durationSeconds>");
    process.exit(1);
}

const words = JSON.parse(fs.readFileSync(inputJson, 'utf8'));

(async () => {
    // Determine total duration
    let maxTime = durationSeconds;
    if (!maxTime) {
        maxTime = words.reduce((max, w) => Math.max(max, w.end || 0), 0);
        maxTime += 1.0; // padding
    }

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
    
    // We create a basic HTML page with a canvas to draw the words
    const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 0; background-color: transparent; overflow: hidden; }
            #container {
                width: 1080px; height: 1920px;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Impact', sans-serif;
            }
            .word {
                position: absolute;
                font-size: 100px;
                color: #ffff00;
                text-shadow: 6px 6px 0px #000;
                -webkit-text-stroke: 4px black;
                text-transform: uppercase;
                opacity: 0;
                transform: scale(0.5);
                top: 50%;
                text-align: center;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div id="container"></div>
        <script>
            window.words = ${JSON.stringify(words)};
            window.durationSeconds = ${maxTime};
            
            const container = document.getElementById('container');
            const wordElements = [];
            
            words.forEach(w => {
                if(w.word && w.start !== undefined && w.end !== undefined) {
                    const el = document.createElement('div');
                    el.className = 'word';
                    el.innerText = w.word;
                    container.appendChild(el);
                    wordElements.push({el, start: w.start, end: w.end});
                }
            });

            // We will use requestAnimationFrame to animate
            let startTime = null;
            window.renderComplete = false;
            
            function animate(timestamp) {
                if (!startTime) startTime = timestamp;
                const elapsedSec = (timestamp - startTime) / 1000;
                
                wordElements.forEach(w => {
                    if (elapsedSec >= w.start && elapsedSec <= w.end + 0.1) {
                        w.el.style.opacity = 1;
                        // Pop effect
                        let progress = (elapsedSec - w.start) / 0.1; // 100ms pop
                        if (progress > 1) progress = 1;
                        let scale = 0.5 + (0.7 * progress); // 0.5 to 1.2
                        if (progress === 1) scale = 1.0; // settle
                        w.el.style.transform = \`translateY(-50%) scale(\${scale})\`;
                    } else {
                        w.el.style.opacity = 0;
                    }
                });

                if (elapsedSec < window.durationSeconds) {
                    requestAnimationFrame(animate);
                } else {
                    window.renderComplete = true;
                }
            }
            
            // start animation
            requestAnimationFrame(animate);
        </script>
    </body>
    </html>
    `;

    // Rather than capturing via JS MediaRecorder which might be unstable in headless, 
    // it's much better to capture frames and pipe to ffmpeg, or use puppeteer-screencast.
    // For simplicity in this demo, let's just log that we would capture it.
    // Real implementation of frame-by-frame:
    
    const { exec } = require('child_process');
    
    // We will save frames and encode.
    const framesDir = path.join(path.dirname(outputWebm), 'frames_' + Date.now());
    fs.mkdirSync(framesDir, {recursive: true});

    await page.setContent(htmlContent);
    
    const fps = 30;
    const totalFrames = Math.ceil(maxTime * fps);
    
    // Override Date.now/performance.now to perfectly sync frames
    await page.evaluate((fps) => {
        window.frameTime = 0;
        window.performance.now = () => window.frameTime;
        
        // Reset animation logic for manual ticking
        window.tickFrame = (frameIdx) => {
            window.frameTime = (frameIdx / fps) * 1000;
            // dispatch animation frame manually
            animate(window.frameTime);
        };
    }, fps);

    for (let i = 0; i < totalFrames; i++) {
        await page.evaluate((i) => window.tickFrame(i), i);
        await page.screenshot({
            path: path.join(framesDir, `frame_${String(i).padStart(5, '0')}.png`),
            omitBackground: true
        });
    }

    await browser.close();

    // Encode to webm with alpha using ffmpeg
    const ffmpegCmd = `ffmpeg -y -framerate ${fps} -i "${path.join(framesDir, 'frame_%05d.png')}" -c:v libvpx-vp9 -pix_fmt yuva420p "${outputWebm}"`;
    
    exec(ffmpegCmd, (error) => {
        // Cleanup frames
        fs.rmSync(framesDir, { recursive: true, force: true });
        if (error) {
            console.error("FFmpeg error:", error);
            process.exit(1);
        } else {
            console.log("WebM generated at", outputWebm);
        }
    });

})();
