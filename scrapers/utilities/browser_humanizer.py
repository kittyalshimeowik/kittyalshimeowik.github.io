# scrapers/facebook/browser_humanizer.py

import time
import random
from scrapers.utilities.time_utils import parse_relative_time, format_elapsed_time

def extract_timestamp_from_dom(page, post_url):
    try:
        time_text = page.evaluate("""
            (targetUrl) => {
                const links = Array.from(document.querySelectorAll('a[href*="/posts/"], a[href*="permalink"]'));
                const match = links.find(a => a.href.includes(targetUrl) || targetUrl.includes(a.href.split('?')[0]));
                if (match) {
                    const container = match.closest('div[role="feed"] > div') || match.parentElement;
                    const timeEl = container ? container.querySelector('span[aria-label], abbr, [id*="stamp"]') : null;
                    if (timeEl) {
                        return timeEl.getAttribute('aria-label') || timeEl.textContent || null;
                    }
                    return match.textContent || null;
                }
                return null;
            }
        """, post_url)
        return time_text
    except Exception:
        return None


def move_mouse_bezier(page, start_x, start_y, end_x, end_y, steps=25):
    control_x = (start_x + end_x) / 2 + random.randint(-80, 80)
    control_y = (start_y + end_y) / 2 + random.randint(-80, 80)
    for i in range(1, steps + 1):
        t = i / steps
        t_eased = t * t * (3 - 2 * t)
        x = (1 - t_eased)**2 * start_x + 2 * (1 - t_eased) * t_eased * control_x + t_eased**2 * end_x
        y = (1 - t_eased)**2 * start_y + 2 * (1 - t_eased) * t_eased * control_y + t_eased**2 * end_y
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.01, 0.025))


def try_click_see_more(page, viewport, mouse_pos):
    try:
        rects = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('div[role="button"]'))
                    .filter(b => b.textContent.trim() === 'See more' && b.offsetWidth > 0 && b.offsetHeight > 0);
                return btns.map(b => {
                    const r = b.getBoundingClientRect();
                    return { x: r.x, y: r.y, width: r.width, height: r.height };
                }).filter(r => r.y >= 0 && r.y <= (window.innerHeight - r.height) && r.x >= 0 && r.x <= (window.innerWidth - r.width));
            }
        """)

        if rects:
            box = random.choice(rects[:3])
            target_x = box["x"] + (box["width"] * random.uniform(0.2, 0.8))
            target_y = box["y"] + (box["height"] * random.uniform(0.2, 0.8))
            move_mouse_bezier(page, mouse_pos["x"], mouse_pos["y"], target_x, target_y, steps=random.randint(20, 30))
            mouse_pos["x"], mouse_pos["y"] = target_x, target_y
            time.sleep(random.uniform(0.2, 0.5))
            page.mouse.click(target_x, target_y)
            return True
    except Exception:
        pass
    return False


def smooth_scroll(page, direction="down", pixels=None):
    if pixels is None:
        distance = random.randint(500, 900) if direction == "down" else -random.randint(300, 500)
    else:
        distance = pixels if direction == "down" else -pixels

    steps = random.randint(10, 15)
    step_delay = random.randint(12, 20)

    page.evaluate(f"""async () => {{
        const distance = {distance};
        const steps = {steps};
        const stepDistance = distance / steps;
        for (let i = 0; i < steps; i++) {{
            window.scrollBy({{ top: stepDistance, behavior: 'instant' }});
            await new Promise(resolve => setTimeout(resolve, {step_delay}));
        }}
    }}""")


def perform_human_action_chain(page, mouse_pos, current_os):
    if current_os == "windows":
        action_type = random.choices(["scroll_down", "scroll_up"], weights=[0.90, 0.10], k=1)[0]
    else:
        action_type = random.choices(["scroll_down", "scroll_up", "see_more"], weights=[0.80, 0.05, 0.15], k=1)[0]
    
    if action_type == "scroll_down":
        smooth_scroll(page, direction="down")
    elif action_type == "scroll_up":
        smooth_scroll(page, direction="up")
    elif action_type == "see_more":
        viewport = page.viewport_size or {"width": 1366, "height": 768}
        try_click_see_more(page, viewport, mouse_pos)
        
    time.sleep(random.uniform(1.5, 3.5))


def check_global_break(global_timer_state, page, mouse_pos, current_os):
    now = time.time()
    if now >= global_timer_state["next_break_due"]:
        pause_duration = random.randint(30, 180)
        print(f"\n☕ [Global Break] Taking a natural human break for {format_elapsed_time(pause_duration)}...")
        
        break_end = time.time() + pause_duration
        viewport = page.viewport_size or {"width": 1366, "height": 768}
        
        while time.time() < break_end:
            if current_os != "windows" and random.random() < 0.15:
                target_x = random.randint(200, viewport["width"] - 200)
                target_y = random.randint(200, viewport["height"] - 200)
                move_mouse_bezier(page, mouse_pos["x"], mouse_pos["y"], target_x, target_y, steps=random.randint(15, 25))
                mouse_pos["x"], mouse_pos["y"] = target_x, target_y
            time.sleep(random.uniform(8.0, 20.0))
            
        global_timer_state["next_break_due"] = time.time() + random.randint(480, 720)
        print(f"▶️ [Global Break] Resuming scraping workflow.")