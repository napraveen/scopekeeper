import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
FONT_REGULAR = os.path.join(FONTS_DIR, "segoeui.ttf")
FONT_BOLD = os.path.join(FONTS_DIR, "segoeuib.ttf")
FONT_MONO = os.path.join(FONTS_DIR, "consola.ttf")

OUT_DIR = Path("dashboard/public/blog_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def get_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def draw_card(draw, x, y, w, h, bg_color, border_color, radius=12):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=bg_color, outline=border_color, width=2)

def draw_badge(draw, x, y, text, font, text_color, bg_color, border_color):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pw, ph = 12, 6
    draw.rounded_rectangle([x, y, x + tw + pw * 2, y + th + ph * 2], radius=6, fill=bg_color, outline=border_color, width=1)
    draw.text((x + pw, y + ph - bbox[1]), text, font=font, fill=text_color)
    return tw + pw * 2

# ==============================================================================
# 1. HERO BANNER
# ==============================================================================
def make_hero_banner():
    W, H = 1600, 600
    img = Image.new("RGB", (W, H), color="#090d16")
    draw = ImageDraw.Draw(img)
    
    # Outer glow border
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=16, outline="#1f293d", width=2)
    
    # Subtle background accent lines
    for i in range(100, W - 100, 150):
        draw.line([(i, 40), (i + 100, H - 40)], fill="#0f172a", width=1)
    
    # Center Card
    draw_card(draw, 60, 60, W - 120, H - 120, "#0f172a", "#334155", radius=16)
    
    f_badge = get_font(FONT_BOLD, 18)
    f_title = get_font(FONT_BOLD, 64)
    f_sub = get_font(FONT_REGULAR, 26)
    f_desc = get_font(FONT_REGULAR, 20)
    
    # Badges
    bx = 100
    by = 100
    bx += draw_badge(draw, bx, by, "WEMAKEDEVS HACKATHON 2026", f_badge, "#38bdf8", "#0369a122", "#0284c7") + 16
    bx += draw_badge(draw, bx, by, "TRACK 1: BEST WORKFLOW", f_badge, "#4ade80", "#15803d22", "#16a34a") + 16
    bx += draw_badge(draw, bx, by, "SWITCH PROTOCOL 0.31", f_badge, "#c084fc", "#7e22ce22", "#9333ea")
    
    # Title & Subtitle
    draw.text((100, 160), "ScopeKeeper", font=f_title, fill="#ffffff")
    draw.text((100, 250), "Stopping Agency Scope Creep with Switch Protocol & Multi-Agent AI", font=f_sub, fill="#94a3b8")
    
    # Value props grid inside banner
    props = [
        ("⚡ Shift Flip Protocol (!flip)", "Atomic role leases between Day PM & Night Autopilot"),
        ("🛡️ Signer Authority Gate", "Separates junior requesters from budget signatories"),
        ("🔄 $0 Win-Win Scope Swap", "Trades unstarted backlog tasks to protect client budget"),
        ("🚀 1-Click 4-Cloud Cascade", "Jira Cloud + Google Workspace + GitHub PR + Slack review")
    ]
    
    px = 100
    py = 340
    pw = 320
    ph = 140
    f_p_title = get_font(FONT_BOLD, 18)
    f_p_desc = get_font(FONT_REGULAR, 15)
    
    for i, (title, desc) in enumerate(props):
        cx = px + i * (pw + 26)
        draw_card(draw, cx, py, pw, ph, "#1e293b", "#475569", radius=10)
        draw.text((cx + 16, py + 18), title, font=f_p_title, fill="#38bdf8")
        
        # Word wrap desc
        words = desc.split()
        line1 = " ".join(words[:4])
        line2 = " ".join(words[4:9])
        line3 = " ".join(words[9:])
        draw.text((cx + 16, py + 54), line1, font=f_p_desc, fill="#cbd5e1")
        if line2:
            draw.text((cx + 16, py + 78), line2, font=f_p_desc, fill="#cbd5e1")
        if line3:
            draw.text((cx + 16, py + 102), line3, font=f_p_desc, fill="#cbd5e1")

    p = OUT_DIR / "01-scopekeeper-banner.png"
    img.save(p)
    print("Saved:", p)

# ==============================================================================
# 2. PERSONAS & AGENTS MATRIX
# ==============================================================================
def make_personas_matrix():
    W, H = 1600, 820
    img = Image.new("RGB", (W, H), color="#0b0f19")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=16, outline="#1e293b", width=2)
    
    f_title = get_font(FONT_BOLD, 36)
    f_sub = get_font(FONT_REGULAR, 20)
    f_sec = get_font(FONT_BOLD, 22)
    f_name = get_font(FONT_BOLD, 20)
    f_role = get_font(FONT_BOLD, 15)
    f_desc = get_font(FONT_REGULAR, 15)
    
    draw.text((60, 50), "ScopeKeeper Stakeholder & AI Agent Topology", font=f_title, fill="#ffffff")
    draw.text((60, 100), "How 4 human personas collaborate seamlessly with 4 autonomous Switch agents across 3 chat platforms", font=f_sub, fill="#94a3b8")
    
    # SECTION 1: 4 HUMAN PERSONAS
    draw.text((60, 160), "HUMAN STAKEHOLDERS ACROSS TWO ORGANIZATIONS", font=f_sec, fill="#38bdf8")
    
    humans = [
        ("🧑‍💻 Harish", "Junior Frontend Developer", "Acme Corp (Client)", "Discord (#acme-client)", "Requester only • Cannot commit budget", "#ef4444"),
        ("👔 Dhana", "Head of Product", "Acme Corp (Client)", "Telegram Mobile Bot", "Authorized Signatory • $5,000 approval cap", "#22c55e"),
        ("👩‍💼 Sakthi", "Lead Project Manager", "Pixel & Co (Agency)", "Switch Console (#acme-intake)", "Day PM Leaseholder • Oversees SOW intake", "#3b82f6"),
        ("👨‍💻 Bala", "Technical Delivery Lead", "Pixel & Co (Agency)", "Slack (#acme-delivery)", "Code Reviewer • Approves PR with @builder lgtm", "#a855f7"),
    ]
    
    cw = 345
    ch = 220
    for i, (name, role, org, platform, auth, tag_col) in enumerate(humans):
        cx = 60 + i * (cw + 26)
        cy = 205
        draw_card(draw, cx, cy, cw, ch, "#111827", "#374151", radius=10)
        draw.text((cx + 18, cy + 18), name, font=f_name, fill="#ffffff")
        draw.text((cx + 18, cy + 50), role, font=f_role, fill="#9ca3af")
        draw.text((cx + 18, cy + 75), f"Org: {org}", font=f_desc, fill="#d1d5db")
        draw.text((cx + 18, cy + 105), f"Channel: {platform}", font=f_desc, fill="#60a5fa")
        
        # Authority badge box
        draw.rounded_rectangle([cx + 18, cy + 145, cx + cw - 18, cy + 200], radius=6, fill="#1f2937", outline=tag_col, width=1)
        draw.text((cx + 26, cy + 162), auth, font=get_font(FONT_BOLD, 13), fill=tag_col)

    # SECTION 2: 4 AUTONOMOUS AI AGENTS
    draw.text((60, 460), "AUTONOMOUS AGENTS ON THE SWITCH PROTOCOL MESH", font=f_sec, fill="#c084fc")
    
    agents = [
        ("🤖 @acme-scout", "Client Desk Representative", "Monitors Discord & Telegram 24/7. Classifies incoming client asks and enforces signer authority.", "#38bdf8"),
        ("🛡️ @clerk", "Contract & Pricing Governor", "Audits Statement of Work v1.2 in document store. Calculates hourly rates ($90/hr) and change orders.", "#f59e0b"),
        ("🛠️ @acme-builder", "Code Engine & Git Lead", "Clones git repos, checks out feature branches, builds React components, and opens GitHub PRs.", "#10b981"),
        ("📊 @acme-estimator", "Capacity & Backlog Modeler", "Scans deliverable backlog to discover unstarted tasks suitable for $0 win-win scope swaps.", "#8b5cf6"),
    ]
    
    for i, (name, role, desc, tag_col) in enumerate(agents):
        cx = 60 + i * (cw + 26)
        cy = 505
        draw_card(draw, cx, cy, cw, ch, "#111827", "#374151", radius=10)
        draw.text((cx + 18, cy + 18), name, font=f_name, fill=tag_col)
        draw.text((cx + 18, cy + 50), role, font=f_role, fill="#e5e7eb")
        
        words = desc.split()
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 32:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
            
        ly = cy + 90
        for l in lines[:4]:
            draw.text((cx + 18, ly), l, font=f_desc, fill="#9ca3af")
            ly += 24

    p = OUT_DIR / "02-personas-and-agents.png"
    img.save(p)
    print("Saved:", p)

# ==============================================================================
# 3. SYSTEM ARCHITECTURE DIAGRAM
# ==============================================================================
def make_architecture_diagram():
    W, H = 1600, 920
    img = Image.new("RGB", (W, H), color="#080c14")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=16, outline="#1e293b", width=2)
    
    f_title = get_font(FONT_BOLD, 36)
    f_sub = get_font(FONT_REGULAR, 20)
    f_box_h = get_font(FONT_BOLD, 22)
    f_item_b = get_font(FONT_BOLD, 17)
    f_item_d = get_font(FONT_REGULAR, 15)
    f_conn = get_font(FONT_BOLD, 14)
    
    draw.text((60, 50), "ScopeKeeper End-to-End System Architecture", font=f_title, fill="#ffffff")
    draw.text((60, 100), "Powered by Switch Protocol 0.31 Mesh: Multi-Platform Messaging, Role Leases, and Enterprise Cloud Cascade", font=f_sub, fill="#94a3b8")
    
    # 4 HORIZONTAL TIERS
    # Tier 1: Client Organization (Top Left)
    draw_card(draw, 60, 160, 440, 230, "#0f172a", "#38bdf8", radius=12)
    draw.text((80, 180), "Acme Corp (Client - San Francisco)", font=f_box_h, fill="#38bdf8")
    draw.text((80, 225), "🧑‍💻 Harish (Junior Dev)", font=f_item_b, fill="#ffffff")
    draw.text((80, 250), "• Discord: #acme-client • Requester Only", font=f_item_d, fill="#94a3b8")
    draw.text((80, 295), "👔 Dhana (Head of Product)", font=f_item_b, fill="#ffffff")
    draw.text((80, 320), "• Telegram Bot • Authorized Signer ($5k Cap)", font=f_item_d, fill="#94a3b8")
    
    # Tier 1 Right: Agency Organization (Top Right)
    draw_card(draw, 1100, 160, 440, 230, "#0f172a", "#a855f7", radius=12)
    draw.text((1120, 180), "Pixel & Co (Agency - Bengaluru)", font=f_box_h, fill="#a855f7")
    draw.text((1120, 225), "👩‍💼 Sakthi (Lead PM)", font=f_item_b, fill="#ffffff")
    draw.text((1120, 250), "• Switch Console: #acme-intake • Day Lease", font=f_item_d, fill="#94a3b8")
    draw.text((1120, 295), "👨‍💻 Bala (Delivery Tech Lead)", font=f_item_b, fill="#ffffff")
    draw.text((1120, 320), "• Slack: #acme-delivery • Code Reviewer", font=f_item_d, fill="#94a3b8")
    
    # Tier 2: SWITCH PROTOCOL 0.31 MESH (Center Box)
    draw_card(draw, 540, 160, 520, 380, "#111827", "#f59e0b", radius=12)
    draw.text((560, 185), "Switch Protocol 0.31 Mesh Engine", font=f_box_h, fill="#f59e0b")
    draw.text((560, 215), "HTTP: 50415 | PostgreSQL DB: 50417", font=get_font(FONT_MONO, 14), fill="#d97706")
    
    mesh_items = [
        ("⚡ Collaboration Bridges", "Bidirectional gateways for Telegram, Discord, and Slack"),
        ("📄 Native Document Store", "Statement of Work v1.2 indexed in documents table"),
        ("🔗 Native References Graph", "Pins Jira issues, Google Sheets & PRs to room sidebar"),
        ("🕒 PostgreSQL Role Leases", "Atomic !flip day / !flip night handover protocol")
    ]
    my = 260
    for title, desc in mesh_items:
        draw.text((560, my), title, font=f_item_b, fill="#fbbf24")
        draw.text((560, my + 24), desc, font=f_item_d, fill="#d1d5db")
        my += 64

    # Connectors between Client/Agency and Switch Mesh
    draw.line([(500, 270), (540, 270)], fill="#38bdf8", width=3)
    draw.polygon([(540, 270), (530, 265), (530, 275)], fill="#38bdf8")
    
    draw.line([(1100, 270), (1060, 270)], fill="#a855f7", width=3)
    draw.polygon([(1060, 270), (1070, 265), (1070, 275)], fill="#a855f7")

    # Tier 3: MULTI-AGENT SQUAD (Below Client Org)
    draw_card(draw, 60, 440, 440, 420, "#0f172a", "#10b981", radius=12)
    draw.text((80, 465), "ScopeKeeper Multi-Agent Squad", font=f_box_h, fill="#10b981")
    
    agent_list = [
        ("🤖 @acme-scout (Desk Lead)", "Evaluates SOW clauses & signer authority"),
        ("🛡️ @clerk (Contract Brain)", "Calculates quote ($1,890) & generates CR-004"),
        ("🛠️ @acme-builder (Git/PR)", "Autonomously authors React code & git branch"),
        ("📊 @acme-estimator", "Discovers D3 CSV task for $0 scope swap")
    ]
    ay = 520
    for name, desc in agent_list:
        draw.text((80, ay), name, font=f_item_b, fill="#34d399")
        draw.text((80, ay + 24), desc, font=f_item_d, fill="#94a3b8")
        ay += 68

    # Connectors from Mesh to Agents
    draw.line([(600, 540), (600, 650), (500, 650)], fill="#10b981", width=3)
    draw.polygon([(500, 650), (510, 645), (510, 655)], fill="#10b981")

    # Tier 4: LIVE ENTERPRISE CLOUD CASCADE (Bottom Right)
    draw_card(draw, 540, 580, 1000, 280, "#0f172a", "#3b82f6", radius=12)
    draw.text((560, 605), "100% Free Live Cloud Cascade (Executed in under 45 seconds)", font=f_box_h, fill="#60a5fa")
    
    clouds = [
        ("🔷 Atlassian Jira Cloud", "Logs Bug KAN-24 ($0 warranty)\nCreates Story KAN-30\nDeschedules Deliverable D3", "#0284c7"),
        ("📊 Google Workspace", "Sheets: Appends to Master Ledger\nDocs: Generates SOW Amendment\nCryptographic SHA-256 Digest", "#16a34a"),
        ("🐙 GitHub Cloud Engine", "Branch: feature/cr-004-stripe\nBuilds StripeCheckoutModal.tsx\nOpens Pull Request with clean CI", "#a855f7"),
        ("💬 Slack Code Review", "Notifies tech lead Bala\nBala reviews & types: @builder lgtm\nVerifies 91 passing tests", "#f59e0b")
    ]
    
    for i, (title, desc, col) in enumerate(clouds):
        box_x = 560 + i * 238
        box_y = 650
        draw_card(draw, box_x, box_y, 226, 185, "#1e293b", col, radius=8)
        draw.text((box_x + 12, box_y + 14), title, font=get_font(FONT_BOLD, 14), fill=col)
        
        lines = desc.split("\n")
        ly = box_y + 48
        for l in lines:
            draw.text((box_x + 12, ly), l, font=get_font(FONT_REGULAR, 12), fill="#cbd5e1")
            ly += 22

    # Final arrow from Agents to Cloud
    draw.line([(500, 720), (540, 720)], fill="#3b82f6", width=3)
    draw.polygon([(540, 720), (530, 715), (530, 725)], fill="#3b82f6")

    p = OUT_DIR / "03-system-architecture.png"
    img.save(p)
    print("Saved:", p)

# ==============================================================================
# 4. SWITCH SUPERPOWERS TABLE
# ==============================================================================
def make_superpowers_table():
    W, H = 1600, 640
    img = Image.new("RGB", (W, H), color="#090d16")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=16, outline="#1f293d", width=2)
    
    f_title = get_font(FONT_BOLD, 36)
    f_sub = get_font(FONT_REGULAR, 20)
    f_th = get_font(FONT_BOLD, 18)
    f_td_b = get_font(FONT_BOLD, 17)
    f_td_r = get_font(FONT_REGULAR, 15)
    f_td_m = get_font(FONT_MONO, 14)
    
    draw.text((60, 45), "The 4 Switch Protocol Superpowers Leveraged by ScopeKeeper", font=f_title, fill="#ffffff")
    draw.text((60, 95), "How ScopeKeeper maps Switch's core architecture into an enterprise contract desk", font=f_sub, fill="#94a3b8")
    
    # Table Header Box
    ty = 150
    draw.rounded_rectangle([60, ty, W - 60, ty + 50], radius=8, fill="#1e293b", outline="#334155", width=1)
    draw.text((80, ty + 14), "SWITCH PROTOCOL FEATURE", font=f_th, fill="#38bdf8")
    draw.text((450, ty + 14), "HOW SCOPEKEEPER USES IT", font=f_th, fill="#38bdf8")
    draw.text((1020, ty + 14), "UNDERLYING TECHNICAL IMPLEMENTATION", font=f_th, fill="#38bdf8")
    
    rows = [
        ("Collaboration Bridges", "Real-time bidirectional message routing across Discord, Telegram, and Slack simultaneously.", "switch_core.bridges adapters with Socket Mode & Telegram long-polling listeners.", "#60a5fa"),
        ("Role Leases (role_leases)", "Atomic shift handoff of @client-desk custody between Day PM (Sakthi) and Night Autopilot (Scout).", "PostgreSQL role_leases table with optimistic locking and automatic lease expiration.", "#4ade80"),
        ("Native Document Store", "Canonical storage of Statement of Work v1.2, hourly blended rate ($90/hr), and warranty terms.", "PostgreSQL documents & room_documents queried via semantic clause extractors.", "#fbbf24"),
        ("Native References Graph", "Pins live Jira issues, Google Sheets billing ledger, and GitHub PR links directly into room sidebars.", "PostgreSQL references & room_references tables with bidirectional cloud entity URLs.", "#c084fc"),
    ]
    
    row_y = ty + 65
    for feature, usage, impl, col in rows:
        draw_card(draw, 60, row_y, W - 120, 85, "#111827", "#1f2937", radius=8)
        
        # Column 1
        draw.text((80, row_y + 30), feature, font=f_td_b, fill=col)
        
        # Column 2
        words_u = usage.split()
        u1 = " ".join(words_u[:7])
        u2 = " ".join(words_u[7:])
        draw.text((450, row_y + 18), u1, font=f_td_r, fill="#e2e8f0")
        if u2:
            draw.text((450, row_y + 46), u2, font=f_td_r, fill="#e2e8f0")
            
        # Column 3
        words_i = impl.split()
        i1 = " ".join(words_i[:6])
        i2 = " ".join(words_i[6:])
        draw.text((1020, row_y + 18), i1, font=f_td_m, fill="#94a3b8")
        if i2:
            draw.text((1020, row_y + 46), i2, font=f_td_m, fill="#94a3b8")
            
        row_y += 105

    p = OUT_DIR / "04-switch-superpowers-table.png"
    img.save(p)
    print("Saved:", p)

# ==============================================================================
# 5. TELEGRAM CHANGE ORDER CARD
# ==============================================================================
def make_telegram_card():
    W, H = 1000, 780
    img = Image.new("RGB", (W, H), color="#0e1621") # Telegram dark mode background
    draw = ImageDraw.Draw(img)
    
    # Outer device frame
    draw_card(draw, 80, 40, W - 160, H - 80, "#17212b", "#242f3d", radius=20)
    
    f_head = get_font(FONT_BOLD, 26)
    f_sub = get_font(FONT_REGULAR, 17)
    f_lbl = get_font(FONT_BOLD, 17)
    f_val = get_font(FONT_REGULAR, 17)
    f_val_b = get_font(FONT_BOLD, 19)
    f_btn = get_font(FONT_BOLD, 18)
    
    # Header bar
    draw.rounded_rectangle([80, 40, W - 80, 110], radius=20, fill="#242f3d")
    draw.text((120, 60), "🛡️ ACME SOW GOVERNANCE DESK (CR-004)", font=f_head, fill="#ffffff")
    
    # Body details
    dy = 140
    fields = [
        ("📋 Change Proposal:", "CR-004 (Statement of Work v1.2 Amendment)", "#ffffff"),
        ("📦 Feature Name:", "Enterprise Stripe Checkout Portal", "#38bdf8"),
        ("👤 Requested By:", "Harish (Junior Developer on Discord)", "#94a3b8"),
        ("⏱️ Development Effort:", "21 Engineering Hours (Blended Rate: $90.00 / hr)", "#e2e8f0"),
        ("💰 Commercial Value:", "$1,890.00 USD (Clause 6.1 Change Control)", "#fbbf24"),
        ("⚠️ Signer Authorization:", "Dhana (Acme Head of Product • Authorized Cap: $5,000)", "#4ade80"),
    ]
    
    for lbl, val, col in fields:
        draw.text((120, dy), lbl, font=f_lbl, fill="#8ea5b8")
        draw.text((360, dy), val, font=f_val_b if "Commercial" in lbl or "Feature" in lbl else f_val, fill=col)
        dy += 46
        
    # Divider
    draw.line([(120, dy + 10), (W - 120, dy + 10)], fill="#242f3d", width=2)
    dy += 30
    
    draw.text((120, dy), "Select governance action as Authorized Signatory:", font=f_sub, fill="#8ea5b8")
    dy += 40
    
    # 3 INTERACTIVE TELEGRAM BUTTONS
    # Button A: Pay $1,890
    draw.rounded_rectangle([120, dy, W - 120, dy + 60], radius=10, fill="#2b5278", outline="#5288c1", width=1)
    draw.text((160, dy + 18), "💼 Option A: Authorize Payment ($1,890.00 USD on next invoice)", font=f_btn, fill="#ffffff")
    dy += 74
    
    # Button B: $0 Scope Swap (Highlighted)
    draw.rounded_rectangle([120, dy, W - 120, dy + 68], radius=10, fill="#1c4b31", outline="#22c55e", width=2)
    draw.text((160, dy + 14), "🔄 Option B: $0 Scope Swap (Deschedule D3 CSV Export)", font=f_btn, fill="#4ade80")
    draw.text((160, dy + 40), "★ Recommended: $0 budget change • 0 days timeline slip", font=get_font(FONT_REGULAR, 14), fill="#86efac")
    dy += 82
    
    # Button C: Decline
    draw.rounded_rectangle([120, dy, W - 120, dy + 60], radius=10, fill="#3b2327", outline="#7a343b", width=1)
    draw.text((160, dy + 18), "❌ Option C: Decline Proposal (Reject out-of-scope feature)", font=f_btn, fill="#f87171")

    p = OUT_DIR / "05-telegram-change-order-card.png"
    img.save(p)
    print("Saved:", p)

# ==============================================================================
# 6. CLOUD CASCADE FLOWCHART
# ==============================================================================
def make_cloud_cascade():
    W, H = 1600, 720
    img = Image.new("RGB", (W, H), color="#080c14")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=16, outline="#1e293b", width=2)
    
    f_title = get_font(FONT_BOLD, 36)
    f_sub = get_font(FONT_REGULAR, 20)
    f_step = get_font(FONT_BOLD, 20)
    f_desc = get_font(FONT_REGULAR, 15)
    f_meta = get_font(FONT_MONO, 14)
    
    draw.text((60, 45), "The 1-Click Multi-Cloud Cascade (Under 45 Seconds Execution)", font=f_title, fill="#ffffff")
    draw.text((60, 95), "Triggered atomically when Dhana taps '[🔄 Option B: $0 Scope Swap]' on Telegram Mobile", font=f_sub, fill="#94a3b8")
    
    steps = [
        ("1. Telegram Tap", "Dhana selects Option B", "Callback query processed by webhook listener", "#22c55e"),
        ("2. Jira Cloud", "Backlog Rebalancing", "Creates Story KAN-30\nDeschedules D3 CSV task", "#0284c7"),
        ("3. Google Sheets", "Billing Ledger Sync", "HTTPS POST to Apps Script\nAppends CR-004 ($0 swap)", "#10b981"),
        ("4. SOW Amendment", "Signed Legal Document", "Authors markdown amendment\nSHA-256 audit digest", "#f59e0b"),
        ("5. GitHub PR", "Autonomous Code Gen", "Branch: feature/cr-004-stripe\nBuilds StripeCheckoutModal.tsx", "#a855f7"),
        ("6. Slack Handshake", "Delivery Team Review", "Builder alerts tech lead Bala\nBala replies: @builder lgtm", "#ef4444"),
    ]
    
    cw = 220
    ch = 320
    sy = 170
    
    for i, (title, action, details, col) in enumerate(steps):
        cx = 60 + i * (cw + 28)
        draw_card(draw, cx, sy, cw, ch, "#111827", col, radius=12)
        
        # Step Number Badge
        draw.rounded_rectangle([cx + 16, sy + 16, cx + 56, sy + 56], radius=8, fill=col)
        draw.text((cx + 28, sy + 22), str(i + 1), font=get_font(FONT_BOLD, 22), fill="#000000")
        
        draw.text((cx + 16, sy + 75), title, font=f_step, fill="#ffffff")
        draw.text((cx + 16, sy + 115), action, font=get_font(FONT_BOLD, 15), fill=col)
        
        lines = details.split("\n")
        ly = sy + 155
        for l in lines:
            draw.text((cx + 16, ly), l, font=f_desc, fill="#cbd5e1")
            ly += 26
            
        # Arrow to next step
        if i < len(steps) - 1:
            ax = cx + cw + 4
            ay = sy + ch // 2
            draw.line([(ax, ay), (ax + 20, ay)], fill="#64748b", width=3)
            draw.polygon([(ax + 20, ay), (ax + 12, ay - 6), (ax + 12, ay + 6)], fill="#64748b")

    # Bottom summary benchmark box
    draw_card(draw, 60, 530, W - 120, 140, "#1e293b", "#334155", radius=12)
    draw.text((90, 555), "⚡ TOTAL CASCADE EXECUTION TIME: 7.59 SECONDS", font=get_font(FONT_BOLD, 22), fill="#38bdf8")
    draw.text((90, 595), "• Measured latency: Jira (1.18s) • Google Sheets (1.84s) • GitHub PR (4.21s) • Slack Socket (0.35s) • Lease (14ms)", font=f_desc, fill="#e2e8f0")
    draw.text((90, 625), "• 100% Free Developer Tiers: Zero extra SaaS costs. 91/91 unit tests passing green.", font=f_desc, fill="#4ade80")

    p = OUT_DIR / "06-cloud-cascade-flowchart.png"
    img.save(p)
    print("Saved:", p)

if __name__ == "__main__":
    make_hero_banner()
    make_personas_matrix()
    make_architecture_diagram()
    make_superpowers_table()
    make_telegram_card()
    make_cloud_cascade()
    print("All 6 high-resolution blog images generated successfully!")
