
const CONFIG = {
    laneHeight: 30,   // recalculated dynamically after packing
    lanePadding: 4,
    maxCanvasHeight: 8000, // cap so scrolling stays manageable
    timeScale: 60 * 1000,
    colors: {
        1: '#ef4444',
        2: '#f97316',
        3: '#10b981',
        4: '#22d3ee',
        5: '#94a3b8',
        wait: '#475569',
        text: '#cbd5e1',
        grid: '#334155'
    }
};

let state = {
    patients: [],
    viewOffset: 0, // ms from start
    zoomLevel: 1000 * 60 * 2, // ms per pixel (2 mins per pixel default)
    minDate: null,
    maxDate: null,
    lanes: [], // Array of { type: 'bed'|'wait', rows: [ {endTime: ms} ] }
    containerWidth: 0,
    containerHeight: 0
};

const canvas = document.getElementById('timeline-canvas');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

async function init() {
    try {
        const select = document.getElementById('data-source-select');

        // Initial load
        const loadData = () => {
            const mode = select.value;
            let data = null;

            if (mode === 'original' && window.DATA_ORIGINAL) {
                data = window.DATA_ORIGINAL;
            } else if (mode === 'fcfs' && window.DATA_FCFS) {
                data = window.DATA_FCFS;
            } else if (mode === 'predictive' && window.DATA_PREDICTIVE) {
                data = window.DATA_PREDICTIVE;
            }

            if (data) {
                processData(data);
                computePacking();
                // If first load
                if (!state.hasInit) {
                    window.addEventListener('resize', handleResize);
                    setupControls();
                    requestAnimationFrame(draw);
                    state.hasInit = true;
                } else {
                    // Just redraw
                    draw();
                }
            } else {
                console.error(`Data for mode ${mode} not found.`);
            }
        };

        select.addEventListener('change', loadData);

        // Initial call
        loadData();
        handleResize();

    } catch (e) {
        console.error("Failed to init", e);
    }
}

function processData(data) {
    state.patients = data.map(p => ({
        ...p,
        arrival: new Date(p.arrival_ts),
        serviceStart: new Date(p.service_start_ts),
        discharge: new Date(p.discharge_ts),
        bed_type: p.bed_type ? p.bed_type.trim().toUpperCase() : 'ED'
    }));

    // Find range
    if (state.patients.length > 0) {
        state.minDate = state.patients[0].arrival;
        state.maxDate = state.patients[state.patients.length - 1].discharge; // roughly
    }
    console.log(`Loaded ${state.patients.length} patients. Range: ${state.minDate} to ${state.maxDate}`);

    // Sort for packing
    state.patients.sort((a, b) => a.arrival - b.arrival);

    // Update stats
    document.getElementById('total-patients').textContent = state.patients.length;

    const totalWait = state.patients.reduce((acc, p) => acc + p.wait_minutes, 0);
    const avgWait = (totalWait / state.patients.length).toFixed(1);
    document.getElementById('avg-wait').textContent = `${avgWait}m`;

    const totalLos = state.patients.reduce((acc, p) => acc + p.los_minutes, 0);
    const avgLos = (totalLos / state.patients.length).toFixed(1);
    document.getElementById('avg-los').textContent = `${avgLos}m`;

    // Auto-fit: zoom to show the entire dataset across the container width
    if (state.minDate && state.maxDate) {
        const totalMs = state.maxDate.getTime() - state.minDate.getTime();
        const usableWidth = Math.max(state.containerWidth, window.innerWidth) - 60;
        const fitZoom = totalMs / usableWidth;
        state.zoomLevel = Math.max(fitZoom, 1000 * 15);
        state.viewOffset = 0;
    }

    // Per-level average wait times
    const waitByLevel = { 1: [], 2: [], 3: [], 4: [], 5: [] };
    let edServiceMin = 0, icuServiceMin = 0;

    state.patients.forEach(p => {
        if (waitByLevel[p.urgency]) waitByLevel[p.urgency].push(p.wait_minutes);
        const svc = p.los_minutes - p.wait_minutes;
        if (p.bed_type === 'ICU') icuServiceMin += svc;
        else edServiceMin += svc;
    });

    [1, 2, 3, 4, 5].forEach(lvl => {
        const arr = waitByLevel[lvl];
        const avg = arr.length ? (arr.reduce((a, b) => a + b, 0) / arr.length) : 0;
        const el = document.getElementById(`wait-l${lvl}`);
        if (el) el.textContent = `${avg.toFixed(0)}m`;
    });

    // Bed occupancy rate
    if (state.minDate && state.maxDate) {
        const simMin = (state.maxDate.getTime() - state.minDate.getTime()) / 60000;
        const edOccupancy = simMin > 0 ? (edServiceMin / (50 * simMin) * 100) : 0;
        const icuOccupancy = simMin > 0 ? (icuServiceMin / (20 * simMin) * 100) : 0;
        const edEl = document.getElementById('ed-occupancy');
        const icuEl = document.getElementById('icu-occupancy');
        if (edEl) edEl.textContent = `${edOccupancy.toFixed(1)}%`;
        if (icuEl) icuEl.textContent = `${icuOccupancy.toFixed(1)}%`;
    }
}

function computePacking() {
    const MAX_WAIT_LANES = 60;   // physical waiting room seats
    const MAX_ED_LANES = 50;   // ED bed count
    const MAX_ICU_LANES = 20;   // ICU bed count

    const waitLanes = [];
    const edLanes = [];
    const icuLanes = [];

    function findLane(lanes, start, end, maxLanes) {
        // Try to find a free lane
        for (let i = 0; i < lanes.length; i++) {
            if (lanes[i] <= start) {
                lanes[i] = end;
                return i;
            }
        }
        // Open a new lane if under cap
        if (lanes.length < maxLanes) {
            lanes.push(end);
            return lanes.length - 1;
        }
        // At cap — reuse the lane that frees up soonest (overlap accepted)
        let minIdx = 0;
        for (let i = 1; i < lanes.length; i++) {
            if (lanes[i] < lanes[minIdx]) minIdx = i;
        }
        lanes[minIdx] = end;
        return minIdx;
    }

    state.renderItems = [];

    state.patients.forEach(p => {
        if (p.wait_minutes > 0) {
            const laneIdx = findLane(waitLanes, p.arrival.getTime(), p.serviceStart.getTime(), MAX_WAIT_LANES);
            state.renderItems.push({
                type: 'wait', patient: p, lane: laneIdx, group: 'wait',
                start: p.arrival, end: p.serviceStart, urgency: p.urgency
            });
        }

        let laneIdx, group;
        if (p.bed_type === 'ICU') {
            laneIdx = findLane(icuLanes, p.serviceStart.getTime(), p.discharge.getTime(), MAX_ICU_LANES);
            group = 'icu';
        } else {
            laneIdx = findLane(edLanes, p.serviceStart.getTime(), p.discharge.getTime(), MAX_ED_LANES);
            group = 'ed';
        }
        state.renderItems.push({
            type: 'service', patient: p, lane: laneIdx, group,
            start: p.serviceStart, end: p.discharge, urgency: p.urgency
        });
    });

    state.waitLaneCount = Math.min(waitLanes.length, MAX_WAIT_LANES);
    state.edLaneCount = Math.min(edLanes.length, MAX_ED_LANES);
    state.icuLaneCount = Math.min(icuLanes.length, MAX_ICU_LANES);
    state.totalLanes = state.waitLaneCount + state.edLaneCount + state.icuLaneCount + 2;

    // Lane height: use 30px by default; shrink only if still too tall
    const rawHeight = state.totalLanes * 30 + 100;
    if (rawHeight > CONFIG.maxCanvasHeight) {
        CONFIG.laneHeight = Math.max(6, Math.floor((CONFIG.maxCanvasHeight - 100) / state.totalLanes));
        CONFIG.lanePadding = 1;
    } else {
        CONFIG.laneHeight = 30;
        CONFIG.lanePadding = 4;
    }
}


// Fix Squashed Text: Remove CSS scaling by setting width/height attributes to match client size
function handleResize() {
    const parent = canvas.parentElement;
    state.containerWidth = parent.clientWidth;
    state.containerHeight = parent.clientHeight;

    // We need to support scrolling. 
    // If contentHeight > containerHeight, we should probably let the parent scroll or handle internal offset.
    // For now, let's keep the canvas size fixed to container for Viewport, 
    // BUT we need to render the content with offset.
    // Wait, the previous logic set canvas.height to max(container, content).
    // If the parent has overflow:hidden, we can't scroll. 
    // Let's set parent to overflow:auto? No, we are doing custom panning.

    // The issue "squashed" usually comes from CSS 'height: 100%' forcing the canvas (which might be 5000px tall) into a 800px box.
    // We should NOT set CSS height if we want it to scroll or if we are controlling render size.
    // BEST FIX: Set canvas.width/height to CLIENT size (screen size) and use translation context for rendering.
    // BUT simpler fix for now: Remove CSS height/width constraints or sync them?

    // Let's go with: Canvas matches container size exactly. We pan vertically if needed (not implemented yet) or just scroll the parent.
    // Actually, let's allow the canvas to be tall and let the parent scroll.

    const contentHeight = state.totalLanes * CONFIG.laneHeight + 100;

    // Resize canvas to be full height of content
    canvas.width = state.containerWidth;
    canvas.height = Math.max(state.containerHeight, contentHeight);

    // IMPORTANT: We must ensure CSS doesn't squash it.
    canvas.style.height = `${canvas.height}px`;
    canvas.style.width = `${canvas.width}px`;

    draw();
}

function setupControls() {
    document.getElementById('zoom-in').onclick = () => {
        state.zoomLevel = Math.max(1000 * 15, state.zoomLevel * 0.8);
        draw();
    };

    document.getElementById('zoom-out').onclick = () => {
        state.zoomLevel = state.zoomLevel * 1.25;
        draw();
    };

    // Pan interaction
    let isDragging = false;
    let lastX = 0;

    canvas.addEventListener('mousedown', e => {
        isDragging = true;
        lastX = e.clientX;
    });

    window.addEventListener('mousemove', e => {
        if (isDragging) {
            const dx = e.clientX - lastX;
            state.viewOffset -= dx * state.zoomLevel;
            lastX = e.clientX;
            draw();
        } else {
            handleHover(e);
        }
    });

    window.addEventListener('mouseup', () => isDragging = false);

    // Mouse wheel + trackpad scroll
    canvas.addEventListener('wheel', e => {
        const isHorizontal = Math.abs(e.deltaX) > Math.abs(e.deltaY);
        const isShiftScroll = e.shiftKey && e.deltaY !== 0;

        if (isHorizontal || isShiftScroll) {
            // Trackpad horizontal swipe OR Shift+wheel → pan timeline left/right
            e.preventDefault();
            const delta = isShiftScroll ? e.deltaY : e.deltaX;
            state.viewOffset += delta * state.zoomLevel;
            state.viewOffset = Math.max(0, state.viewOffset);
            draw();
        }
        // Pure vertical scroll falls through to the container's native scrollbar
    }, { passive: false });
}

function msToPx(ms) {
    if (!state.minDate) return 0;
    const rel = ms - state.minDate.getTime();
    return (rel / state.zoomLevel) - (state.viewOffset / state.zoomLevel) + 50;
}

function pxToMs(px) {
    if (!state.minDate) return 0;
    return (px - 50) * state.zoomLevel + state.viewOffset + state.minDate.getTime();
}

function draw() {
    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--card-bg');
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (!state.minDate) return;

    // Time Grid
    const startTime = pxToMs(0);
    const endTime = pxToMs(canvas.width);

    ctx.strokeStyle = CONFIG.colors.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();

    // Dynamic grid lines
    const msPerMin = 60000;
    const msPerHour = msPerMin * 60;
    const msPerDay = msPerHour * 24;

    let step = msPerHour;
    if (state.zoomLevel < 10000) step = msPerMin * 10; // Zoomed in -> 10 mins
    if (state.zoomLevel > 10000 * 60) step = msPerDay; // Zoomed out -> Days

    // Snap to grid
    const firstLine = Math.floor(startTime / step) * step;

    for (let t = firstLine; t < endTime; t += step) {
        const x = msToPx(t);
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);

        // Time Label
        ctx.fillStyle = CONFIG.colors.text;
        ctx.font = '10px sans-serif';
        const date = new Date(t);

        let labelStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        // Adds Date if crossing midnight or zoomed out
        if (date.getHours() === 0 && date.getMinutes() === 0) {
            labelStr = date.toLocaleDateString() + " " + labelStr;
        }
        ctx.fillText(labelStr, x + 4, 12);
    }
    ctx.stroke();

    // Draw Items
    state.renderItems.forEach(item => {
        const x = msToPx(item.start.getTime());
        const w = Math.max(2, msToPx(item.end.getTime()) - x);

        // Calculate base Y based on group
        let basePath = 40;
        if (item.group === 'ed') {
            basePath = 40 + (state.waitLaneCount * CONFIG.laneHeight) + 30; // 30px for Wait Header
        } else if (item.group === 'icu') {
            // Wait Header + Wait Lanes + ED Header (30) + ED Lanes + Padding (20)
            // Wait, let's match the labels logic below:
            // ED Header Y is at: 40 + waitLanes * H + 20
            // ED Lanes start at: 40 + waitLanes * H + 30
            // ICU Header Y is at: ED Start + edLanes * H + 20
            // ICU Lanes start at: ED Start + edLanes * H + 30

            const edStart = 40 + (state.waitLaneCount * CONFIG.laneHeight) + 30;
            basePath = edStart + (state.edLaneCount * CONFIG.laneHeight) + 30;
        }

        const y = basePath + (item.lane * CONFIG.laneHeight);
        const h = CONFIG.laneHeight - CONFIG.lanePadding;

        // Visibility Check
        if (x + w < 0 || x > canvas.width) return;

        ctx.beginPath();
        ctx.roundRect(x, y, w, h, 4);

        if (item.type === 'wait') {
            ctx.fillStyle = CONFIG.colors.wait;
            ctx.globalAlpha = 0.6;
            ctx.fill();

            // Dashed border for wait
            ctx.strokeStyle = CONFIG.colors[item.urgency] || '#fff';
            ctx.setLineDash([2, 2]);
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.setLineDash([]);
        } else {
            ctx.fillStyle = CONFIG.colors[item.urgency] || '#999';
            ctx.globalAlpha = 1.0;
            ctx.fill();
        }
        ctx.globalAlpha = 1.0;
    });

    // Draw Section Labels
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText("WAITING ROOM", 10, 30);

    // ED Header
    const edY = 40 + (state.waitLaneCount * CONFIG.laneHeight) + 20;
    ctx.fillText("ED BEDS", 10, edY);

    // ED Separator
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, edY + 10);
    ctx.lineTo(canvas.width, edY + 10);
    ctx.stroke();

    // ICU Header
    const icuY = edY + 10 + (state.edLaneCount * CONFIG.laneHeight) + 20;
    ctx.fillText("ICU BEDS", 10, icuY);

    // ICU Separator
    ctx.beginPath();
    ctx.moveTo(0, icuY + 10);
    ctx.lineTo(canvas.width, icuY + 10);
    ctx.stroke();

    // Update Time Range Label dynamically
    const durationMs = canvas.width * state.zoomLevel;
    const hours = (durationMs / (1000 * 60 * 60)).toFixed(1);
    const label = document.getElementById('time-range-label');
    if (label) {
        label.textContent = `${hours} Hours`;
    }
}

function handleHover(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let found = null;

    // Reverse iter to check top items first (though usually no overalap)
    for (let i = state.renderItems.length - 1; i >= 0; i--) {
        const item = state.renderItems[i];
        const x = msToPx(item.start.getTime());
        const w = Math.max(2, msToPx(item.end.getTime()) - x);
        const y = item.lane * CONFIG.laneHeight + 40;
        const h = CONFIG.laneHeight - CONFIG.lanePadding;

        if (mx >= x && mx <= x + w && my >= y && my <= y + h) {
            found = item;
            break;
        }
    }

    if (found) {
        tooltip.classList.remove('hidden');
        tooltip.style.left = `${e.clientX + 10}px`;
        tooltip.style.top = `${e.clientY + 10}px`;

        const duration = Math.round((item.end - item.start) / 60000);

        tooltip.innerHTML = `
            <div class="tooltip-row"><strong>Patient</strong> <span>${found.patient.id}</span></div>
            <div class="tooltip-row"><span class="tooltip-label">Status</span> <span>${item.type.toUpperCase()}</span></div>
            <div class="tooltip-row"><span class="tooltip-label">Urgency</span> <span>Level ${found.urgency}</span></div>
            <div class="tooltip-row"><span class="tooltip-label">Duration</span> <span>${duration} mins</span></div>
            <div class="tooltip-row"><span class="tooltip-label">Bed Type</span> <span>${found.patient.bed_type}</span></div>
        `;
    } else {
        tooltip.classList.add('hidden');
    }
}

init();

// Triage Modal Logic
const triageModal = document.getElementById('triage-modal');
const openTriageBtn = document.getElementById('open-triage-btn');
const closeTriageBtn = document.getElementById('close-triage-btn');
const nextStepBtn = document.getElementById('next-step');
const prevStepBtn = document.getElementById('prev-step');
const submitTriageBtn = document.getElementById('submit-triage');
const triageForm = document.getElementById('triage-form');
const progressBar = document.getElementById('triage-progress-bar');
const painRange = document.getElementById('t-pain-range');
const painVal = document.getElementById('pain-val');

let currentStep = 1;

if (openTriageBtn) {
    openTriageBtn.onclick = () => {
        triageModal.classList.remove('hidden');
        resetTriage();
    };
}

if (closeTriageBtn) {
    closeTriageBtn.onclick = () => triageModal.classList.add('hidden');
}

if (painRange) {
    painRange.oninput = (e) => painVal.textContent = e.target.value;
}

function resetTriage() {
    currentStep = 1;
    updateStepVisibility();
    triageForm.reset();
    painVal.textContent = "0";
}

function updateStepVisibility() {
    const steps = document.querySelectorAll('.triage-step');
    steps.forEach(step => {
        if (parseInt(step.dataset.step) === currentStep) {
            step.classList.remove('hidden');
        } else {
            step.classList.add('hidden');
        }
    });

    // Progress
    progressBar.style.width = `${(currentStep / 4) * 100}%`;

    // Buttons
    prevStepBtn.classList.toggle('hidden', currentStep === 1);
    nextStepBtn.classList.toggle('hidden', currentStep === 4);
    submitTriageBtn.classList.toggle('hidden', currentStep !== 4);

    // Conditional Logic Check
    if (currentStep === 4) {
        handleConditionalLogic();
    }
}

function handleConditionalLogic() {
    const age = parseInt(document.getElementById('t-age').value) || 0;
    const isPregnant = document.getElementById('t-pregnancy-check').checked;

    const pedSection = document.getElementById('pediatric-section');
    const pregSection = document.getElementById('pregnancy-section');
    const noCond = document.getElementById('no-conditional');

    let hasAny = false;
    if (age < 18) {
        pedSection.classList.remove('hidden');
        hasAny = true;
    } else {
        pedSection.classList.add('hidden');
    }

    if (isPregnant) {
        pregSection.classList.remove('hidden');
        hasAny = true;
    } else {
        pregSection.classList.add('hidden');
    }

    noCond.classList.toggle('hidden', hasAny);
}

nextStepBtn.onclick = () => {
    if (currentStep < 4) {
        currentStep++;
        updateStepVisibility();
    }
};

prevStepBtn.onclick = () => {
    if (currentStep > 1) {
        currentStep--;
        updateStepVisibility();
    }
};

submitTriageBtn.onclick = (e) => {
    e.preventDefault();
    const formData = new FormData(triageForm);
    const data = {};
    formData.forEach((value, key) => {
        if (key === 'history') {
            if (!data[key]) data[key] = [];
            data[key].push(value);
        } else {
            data[key] = value;
        }
    });

    const ctas = calculateCTAS(data);
    alert(`Triage Complete!\nAssigned Level: CTAS ${ctas}\n(System would now prioritize accordingly)`);
    triageModal.classList.add('hidden');
};

function calculateCTAS(data) {
    // Red-Flag Overrides (CTAS 1)
    if (data.active_seizure || data.uncontrollable_hemorrhage || data.consciousness === 'unresponsive') {
        return 1;
    }
    const spo2 = parseInt(data.spo2) || 100;
    if (spo2 < 90) return 1;

    // Weighted Scoring
    let score = 0;

    // Vitals
    const hr = parseInt(data.heart_rate) || 70;
    const sbp = parseInt(data.systolic_bp) || 120;
    const rr = parseInt(data.respiratory_rate) || 16;
    const age = parseInt(data.age) || 30;

    if (spo2 < 92 || sbp < 80 || rr > 35 || hr > 130) score += 5;
    else if (spo2 < 95 || sbp < 100 || rr > 24 || hr > 110) score += 3;
    else if (hr > 100 || rr > 20 || sbp > 160) score += 1;

    // Complaint
    const comp = data.primary_complaint;
    if (comp === 'chest pain' || comp === 'stroke') score += 4;
    else if (comp === 'abdominal pain') score += 3;
    else if (comp === 'trauma') score += 2;
    else score += 1;

    // Pain
    const pain = parseInt(data.pain_score) || 0;
    if (pain >= 8) score += 2;
    else if (pain >= 5) score += 1;

    // Risks
    const history = data.history || [];
    if (history.includes('chronic_disease')) score += 1;
    if (history.includes('pregnancy')) score += 2;
    if (history.includes('immunocompromised')) score += 1;

    // Age Adjustment
    if (age > 65 || age < 18) score += 1;

    // Mapping
    if (score >= 9) return 1;
    if (score >= 7) return 2;
    if (score >= 4) return 3;
    if (score >= 2) return 4;
    return 5;
}
