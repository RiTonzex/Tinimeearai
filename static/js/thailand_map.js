/**
 * Thailand 77 Province Interactive SVG Map Renderer
 * Tinimeearai Gamification - Travel Footprints
 */

const THAILAND_PROVINCES_MAP_DATA = [
  // Central
  { id: "TH-10", name: "กรุงเทพมหานคร", x: 400, y: 550, r: 24, region: "กลาง" },
  { id: "TH-11", name: "สมุทรปราการ", x: 420, y: 575, r: 16, region: "กลาง" },
  { id: "TH-12", name: "นนทบุรี", x: 390, y: 530, r: 16, region: "กลาง" },
  { id: "TH-13", name: "ปทุมธานี", x: 410, y: 510, r: 18, region: "กลาง" },
  { id: "TH-14", name: "พระนครศรีอยุธยา", x: 400, y: 485, r: 20, region: "กลาง" },
  { id: "TH-15", name: "อ่างทอง", x: 380, y: 465, r: 15, region: "กลาง" },
  { id: "TH-16", name: "ลพบุรี", x: 415, y: 440, r: 22, region: "กลาง" },
  { id: "TH-17", name: "สิงห์บุรี", x: 375, y: 445, r: 14, region: "กลาง" },
  { id: "TH-18", name: "ชัยนาท", x: 360, y: 425, r: 16, region: "กลาง" },
  { id: "TH-19", name: "สระบุรี", x: 435, y: 475, r: 20, region: "กลาง" },
  { id: "TH-26", name: "นครนายก", x: 465, y: 495, r: 18, region: "กลาง" },
  { id: "TH-73", name: "นครปฐม", x: 365, y: 540, r: 20, region: "กลาง" },
  { id: "TH-74", name: "สมุทรสาคร", x: 375, y: 570, r: 15, region: "กลาง" },
  { id: "TH-75", name: "สมุทรสงคราม", x: 355, y: 580, r: 14, region: "กลาง" },
  { id: "TH-72", name: "สุพรรณบุรี", x: 345, y: 470, r: 24, region: "กลาง" },

  // Eastern
  { id: "TH-20", name: "ชลบุรี", x: 460, y: 580, r: 24, region: "ตะวันออก" },
  { id: "TH-21", name: "ระยอง", x: 485, y: 615, r: 20, region: "ตะวันออก" },
  { id: "TH-22", name: "จันทบุรี", x: 535, y: 610, r: 22, region: "ตะวันออก" },
  { id: "TH-23", name: "ตราด", x: 575, y: 645, r: 20, region: "ตะวันออก" },
  { id: "TH-24", name: "ฉะเชิงเทรา", x: 475, y: 535, r: 24, region: "ตะวันออก" },
  { id: "TH-25", name: "ปราจีนบุรี", x: 510, y: 500, r: 20, region: "ตะวันออก" },
  { id: "TH-27", name: "สระแก้ว", x: 555, y: 515, r: 24, region: "ตะวันออก" },

  // Northern
  { id: "TH-50", name: "เชียงใหม่", x: 260, y: 160, r: 36, region: "เหนือ" },
  { id: "TH-51", name: "ลำพูน", x: 275, y: 200, r: 18, region: "เหนือ" },
  { id: "TH-52", name: "ลำปาง", x: 310, y: 215, r: 28, region: "เหนือ" },
  { id: "TH-53", name: "อุตรดิตถ์", x: 360, y: 260, r: 22, region: "เหนือ" },
  { id: "TH-54", name: "แพร่", x: 350, y: 220, r: 22, region: "เหนือ" },
  { id: "TH-55", name: "น่าน", x: 390, y: 180, r: 28, region: "เหนือ" },
  { id: "TH-56", name: "พะเยา", x: 355, y: 165, r: 22, region: "เหนือ" },
  { id: "TH-57", name: "เชียงราย", x: 320, y: 110, r: 30, region: "เหนือ" },
  { id: "TH-58", name: "แม่ฮ่องสอน", x: 205, y: 155, r: 30, region: "เหนือ" },
  { id: "TH-60", name: "นครสวรรค์", x: 350, y: 385, r: 26, region: "เหนือ" },
  { id: "TH-61", name: "อุทัยธานี", x: 310, y: 400, r: 24, region: "เหนือ" },
  { id: "TH-62", name: "กำแพงเพชร", x: 315, y: 345, r: 24, region: "เหนือ" },
  { id: "TH-63", name: "ตาก", x: 250, y: 310, r: 34, region: "เหนือ" },
  { id: "TH-64", name: "สุโขทัย", x: 320, y: 295, r: 22, region: "เหนือ" },
  { id: "TH-65", name: "พิษณุโลก", x: 365, y: 310, r: 26, region: "เหนือ" },
  { id: "TH-66", name: "พิจิตร", x: 355, y: 345, r: 20, region: "เหนือ" },
  { id: "TH-67", name: "เพชรบูรณ์", x: 410, y: 340, r: 28, region: "เหนือ" },

  // Northeastern (Isan)
  { id: "TH-30", name: "นครราชสีมา", x: 500, y: 440, r: 38, region: "อีสาน" },
  { id: "TH-31", name: "บุรีรัมย์", x: 565, y: 450, r: 28, region: "อีสาน" },
  { id: "TH-32", name: "สุรินทร์", x: 615, y: 455, r: 26, region: "อีสาน" },
  { id: "TH-33", name: "ศรีสะเกษ", x: 660, y: 450, r: 26, region: "อีสาน" },
  { id: "TH-34", name: "อุบลราชธานี", x: 720, y: 440, r: 36, region: "อีสาน" },
  { id: "TH-35", name: "ยโสธร", x: 670, y: 400, r: 20, region: "อีสาน" },
  { id: "TH-36", name: "ชัยภูมิ", x: 465, y: 385, r: 28, region: "อีสาน" },
  { id: "TH-37", name: "อำนาจเจริญ", x: 715, y: 390, r: 18, region: "อีสาน" },
  { id: "TH-38", name: "บึงกาฬ", x: 640, y: 225, r: 20, region: "อีสาน" },
  { id: "TH-39", name: "หนองบัวลำภู", x: 515, y: 290, r: 20, region: "อีสาน" },
  { id: "TH-40", name: "ขอนแก่น", x: 535, y: 345, r: 30, region: "อีสาน" },
  { id: "TH-41", name: "อุดรธานี", x: 565, y: 275, r: 28, region: "อีสาน" },
  { id: "TH-42", name: "เลย", x: 465, y: 270, r: 30, region: "อีสาน" },
  { id: "TH-43", name: "หนองคาย", x: 575, y: 235, r: 22, region: "อีสาน" },
  { id: "TH-44", name: "มหาสารคาม", x: 580, y: 360, r: 20, region: "อีสาน" },
  { id: "TH-45", name: "ร้อยเอ็ด", x: 620, y: 375, r: 24, region: "อีสาน" },
  { id: "TH-46", name: "กาฬสินธุ์", x: 615, y: 325, r: 22, region: "อีสาน" },
  { id: "TH-47", name: "สกลนคร", x: 655, y: 280, r: 28, region: "อีสาน" },
  { id: "TH-48", name: "นครพนม", x: 700, y: 270, r: 24, region: "อีสาน" },
  { id: "TH-49", name: "มุกดาหาร", x: 705, y: 335, r: 20, region: "อีสาน" },

  // Western
  { id: "TH-70", name: "ราชบุรี", x: 310, y: 550, r: 26, region: "ตะวันตก" },
  { id: "TH-71", name: "กาญจนบุรี", x: 260, y: 470, r: 38, region: "ตะวันตก" },
  { id: "TH-76", name: "เพชรบุรี", x: 320, y: 610, r: 26, region: "ตะวันตก" },
  { id: "TH-77", name: "ประจวบคีรีขันธ์", x: 310, y: 675, r: 28, region: "ตะวันตก" },

  // Southern
  { id: "TH-80", name: "นครศรีธรรมราช", x: 285, y: 840, r: 32, region: "ใต้" },
  { id: "TH-81", name: "กระบี่", x: 235, y: 855, r: 24, region: "ใต้" },
  { id: "TH-82", name: "พังงา", x: 215, y: 815, r: 22, region: "ใต้" },
  { id: "TH-83", name: "ภูเก็ต", x: 200, y: 875, r: 18, region: "ใต้" },
  { id: "TH-84", name: "สุราษฎร์ธานี", x: 260, y: 785, r: 34, region: "ใต้" },
  { id: "TH-85", name: "ระนอง", x: 230, y: 740, r: 20, region: "ใต้" },
  { id: "TH-86", name: "ชุมพร", x: 275, y: 725, r: 26, region: "ใต้" },
  { id: "TH-90", name: "สงขลา", x: 320, y: 920, r: 28, region: "ใต้" },
  { id: "TH-91", name: "สตูล", x: 270, y: 925, r: 20, region: "ใต้" },
  { id: "TH-92", name: "ตรัง", x: 255, y: 890, r: 22, region: "ใต้" },
  { id: "TH-93", name: "พัทลุง", x: 290, y: 885, r: 20, region: "ใต้" },
  { id: "TH-94", name: "ปัตตานี", x: 355, y: 940, r: 18, region: "ใต้" },
  { id: "TH-95", name: "ยะลา", x: 345, y: 970, r: 22, region: "ใต้" },
  { id: "TH-96", name: "นราธิวาส", x: 380, y: 965, r: 22, region: "ใต้" },
];

let tooltipEl = null;
let selectedNode = null;

function renderThailandMap(containerId, visitedSvgIds = []) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const visitedSet = new Set(visitedSvgIds);

  let svgHtml = `
    <svg viewBox="0 0 800 1020" class="w-full h-full filter drop-shadow-xl select-none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="visitedGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="100%" stop-color="#d4d4d8" />
        </radialGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
  `;

  THAILAND_PROVINCES_MAP_DATA.forEach(p => {
    const isVisited = visitedSet.has(p.id);
    const fill = isVisited ? "url(#visitedGrad)" : "#09090b";
    const stroke = isVisited ? "#ffffff" : "#27272a";
    const strokeWidth = isVisited ? "2.5" : "1.2";
    const filter = isVisited ? "url(#glow)" : "none";
    const textColor = isVisited ? "#09090b" : "#71717a";

    svgHtml += `
      <g class="province-node cursor-pointer transition-all duration-200 group" data-id="${p.id}" data-name="${p.name}" data-visited="${isVisited}">
        <circle cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" filter="${filter}" class="transition-all duration-150 group-hover:stroke-white group-hover:stroke-[3px]" />
        <text x="${p.x}" y="${p.y + 3}" text-anchor="middle" fill="${textColor}" font-size="${Math.max(9, Math.min(12, p.r * 0.55))}" font-weight="bold" font-family="sans-serif" pointer-events="none" class="group-hover:fill-white">
          ${p.name.substring(0, 4)}
        </text>
      </g>
    `;
  });

  svgHtml += `</svg>`;

  container.innerHTML = svgHtml;

  // Event listeners for static tooltips & click selection
  const nodes = container.querySelectorAll('.province-node');
  nodes.forEach(node => {
    node.addEventListener('mouseenter', () => {
      if (!selectedNode) {
        showProvinceTooltip(node);
      }
    });

    node.addEventListener('mouseleave', () => {
      if (!selectedNode) {
        hideProvinceTooltip();
      }
    });

    node.addEventListener('click', (e) => {
      e.stopPropagation();
      selectedNode = node;
      showProvinceTooltip(node);
    });
  });

  // Clear selection on clicking outside
  document.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      selectedNode = null;
      hideProvinceTooltip();
    }
  });

  window.addEventListener('resize', () => {
    if (selectedNode) {
      positionTooltipOnNode(selectedNode);
    }
  });
}

function positionTooltipOnNode(node) {
  if (!tooltipEl) return;
  const rect = node.getBoundingClientRect();
  const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
  const scrollY = window.pageYOffset || document.documentElement.scrollTop;

  const centerX = rect.left + rect.width / 2 + scrollX;
  const topY = rect.top + scrollY - 6;

  tooltipEl.style.left = centerX + 'px';
  tooltipEl.style.top = topY + 'px';
}

function showProvinceTooltip(node) {
  const name = node.getAttribute('data-name');
  const isVisited = node.getAttribute('data-visited') === 'true';

  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'absolute z-[9999] px-3.5 py-2 rounded-2xl bg-zinc-950/95 border border-zinc-700/80 text-white text-xs font-bold shadow-2xl backdrop-blur-md pointer-events-none transition-all duration-150 transform -translate-x-1/2 -translate-y-full opacity-0 scale-95';
    document.body.appendChild(tooltipEl);
  }

  tooltipEl.innerHTML = `
    <div class="flex items-center gap-2 whitespace-nowrap">
      <span class="text-white font-black text-xs tracking-tight">${name}</span>
      ${isVisited 
        ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-white text-black font-bold font-mono">✓ พิชิตแล้ว</span>' 
        : '<span class="text-[10px] px-2 py-0.5 rounded-full bg-zinc-900 text-zinc-400 border border-zinc-800 font-bold font-mono">ยังไม่เคยไป</span>'}
    </div>
  `;

  positionTooltipOnNode(node);
  requestAnimationFrame(() => {
    tooltipEl.style.opacity = '1';
    tooltipEl.style.transform = 'translate(-50%, -100%) scale(1)';
  });
}

function hideProvinceTooltip() {
  if (tooltipEl) {
    tooltipEl.style.opacity = '0';
    tooltipEl.style.transform = 'translate(-50%, -100%) scale(0.95)';
  }
}

window.renderThailandMap = renderThailandMap;
