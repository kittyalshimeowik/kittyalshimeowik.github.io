#!/usr/bin/env python3
"""
Generates the SVG logo and rendered PNG favicons for Armenia Real Estate Hub.
"""
import os
from PIL import Image
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

SVG_LOGO = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" fill="none">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120"/>
      <stop offset="50%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    
    <!-- Accent Ring Gradient -->
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.6"/>
      <stop offset="50%" stop-color="#818cf8" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.4"/>
    </linearGradient>
    
    <!-- Main Peak / Roof Gradient -->
    <linearGradient id="roofMain" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#cbd5e1"/>
    </linearGradient>
    
    <!-- Secondary Peak / Highrise Gradient -->
    <linearGradient id="roofSide" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#60a5fa"/>
      <stop offset="100%" stop-color="#2563eb"/>
    </linearGradient>

    <!-- Door / Hearth Glow Gradient -->
    <linearGradient id="hearthGlow" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>

    <!-- Armenian Tricolor Gradients -->
    <linearGradient id="amRed" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ef4444"/>
      <stop offset="100%" stop-color="#dc2626"/>
    </linearGradient>
    <linearGradient id="amBlue" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
    <linearGradient id="amOrange" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
    
    <filter id="shadowFilter" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#000000" flood-opacity="0.45"/>
    </filter>
  </defs>

  <!-- Outer squircle frame -->
  <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#bgGrad)" stroke="url(#ringGrad)" stroke-width="1.5"/>

  <!-- Architectural Elements -->
  <g filter="url(#shadowFilter)">
    <!-- Modern Tower / Wing Right (Ararat Minor reference & highrise) -->
    <path d="M30 25 L47 14 L53 18.5 V42 H35 V30.5 L30 25 Z" fill="url(#roofSide)" opacity="0.95"/>
    
    <!-- Primary Residential Home / Peak (Ararat Major reference) -->
    <path d="M11 42 V22.5 L25 11 L39 22.5 V42 H11 Z" fill="url(#roofMain)"/>
    
    <!-- Subtle Architectural Shadow facet -->
    <path d="M25 11 L39 22.5 V42 H25 V11 Z" fill="#0f172a" opacity="0.16"/>
    <path d="M11 22.5 L25 11 V42 H11 V22.5 Z" fill="#ffffff" opacity="0.12"/>

    <!-- Keyhole / Arched Hearth (Light from home) -->
    <path d="M21 42 V31 C21 28.8 22.8 27 25 27 C27.2 27 29 28.8 29 31 V42 H21 Z" fill="url(#hearthGlow)"/>
    
    <!-- Accent architectural windows on tower -->
    <rect x="42" y="23" width="5.5" height="4" rx="1" fill="#ffffff" opacity="0.9"/>
    <rect x="42" y="30" width="5.5" height="4" rx="1" fill="#ffffff" opacity="0.9"/>
    <rect x="42" y="37" width="5.5" height="4" rx="1" fill="#ffffff" opacity="0.9"/>
  </g>

  <!-- Foundation: Stylized Armenian Tricolor Ribbon Baseline -->
  <g>
    <!-- Red Stripe -->
    <rect x="11" y="46" width="42" height="2.6" rx="1.3" fill="url(#amRed)"/>
    <!-- Blue Stripe -->
    <rect x="11" y="49.8" width="42" height="2.6" rx="1.3" fill="url(#amBlue)"/>
    <!-- Orange Stripe -->
    <rect x="11" y="53.6" width="42" height="2.6" rx="1.3" fill="url(#amOrange)"/>
  </g>
</svg>
"""

def generate_icons():
    # Save SVG logo
    svg_path = os.path.join(PROJECT_ROOT, "logo.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_LOGO.strip())
    print(f"Generated {svg_path}")

    # Also save favicon.svg
    favicon_svg_path = os.path.join(PROJECT_ROOT, "favicon.svg")
    with open(favicon_svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_LOGO.strip())
    print(f"Generated {favicon_svg_path}")

    # Use Playwright to render high-res PNG and resize with Pillow
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
  svg {{ display: block; width: 512px; height: 512px; }}
</style>
</head>
<body>
{SVG_LOGO}
</body>
</html>"""
    
    temp_html = os.path.join(PROJECT_ROOT, "_temp_logo.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    master_png = os.path.join(PROJECT_ROOT, "apple-touch-icon.png")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 512, "height": 512}, device_scale_factor=2)
        page.goto(f"file:///{temp_html.replace(os.sep, '/')}")
        page.wait_for_selector("svg")
        # Capture 512x512 with transparent background
        page.locator("svg").screenshot(path=master_png, omit_background=True)
        browser.close()

    if os.path.exists(temp_html):
        os.remove(temp_html)

    # Now use PIL to generate 180x180, 32x32, 16x16, and favicon.ico
    img_master = Image.open(master_png)

    # 180x180 apple-touch-icon
    img_180 = img_master.resize((180, 180), Image.Resampling.LANCZOS)
    img_180.save(master_png, "PNG")

    # 32x32 favicon
    fav_32_path = os.path.join(PROJECT_ROOT, "favicon-32x32.png")
    img_32 = img_master.resize((32, 32), Image.Resampling.LANCZOS)
    img_32.save(fav_32_path, "PNG")

    # 16x16 favicon
    fav_16_path = os.path.join(PROJECT_ROOT, "favicon-16x16.png")
    img_16 = img_master.resize((16, 16), Image.Resampling.LANCZOS)
    img_16.save(fav_16_path, "PNG")

    # favicon.ico (multi-size ICO containing 16, 32, 48)
    ico_path = os.path.join(PROJECT_ROOT, "favicon.ico")
    img_master.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"Generated PNG and ICO icons: 16x16, 32x32, 180x180, favicon.ico")

if __name__ == "__main__":
    generate_icons()
