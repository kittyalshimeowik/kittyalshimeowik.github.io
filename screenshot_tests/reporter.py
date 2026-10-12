"""
HTML Report Generator for Screenshot Testing.
Creates an interactive, modern visual dashboard showcasing side-by-side screenshot
comparisons, diff heatmaps, and test execution statistics.
"""

from datetime import datetime
import os
from typing import List
from .comparator import ComparisonResult
from .scenarios import TestScenario


def generate_html_report(
    results: List[ComparisonResult],
    scenarios: List[TestScenario],
    report_output_path: str,
    output_dir: str,
    baselines_dir: str,
    duration_seconds: float = 0.0,
) -> str:
    """Generates an interactive, standalone HTML visual report."""
    os.makedirs(os.path.dirname(os.path.abspath(report_output_path)), exist_ok=True)
    report_dir = os.path.dirname(os.path.abspath(report_output_path))

    scenarios_by_id = {s.id: s for s in scenarios}

    total_count = len(results)
    pass_count = sum(1 for r in results if r.status in ("MATCH", "NEW_BASELINE"))
    mismatch_count = sum(1 for r in results if r.status in ("MISMATCH", "SIZE_MISMATCH"))
    new_baseline_count = sum(1 for r in results if r.status == "NEW_BASELINE")
    error_count = sum(1 for r in results if r.status == "ERROR")

    # Helper to calculate relative URL from report.html to images
    def rel_url(target_path: str) -> str:
        if not target_path or not os.path.exists(target_path):
            return ""
        try:
            rel = os.path.relpath(target_path, report_dir)
            return rel.replace("\\", "/")
        except ValueError:
            return target_path.replace("\\", "/")

    cards_html = []
    for r in results:
        scenario = scenarios_by_id.get(r.scenario_id)
        desc = scenario.description if scenario else ""
        title = scenario.title if scenario else r.scenario_id

        # Badge color and text
        if r.status == "MATCH":
            badge_class = "badge-success"
            badge_text = "PASSED (MATCH)"
        elif r.status == "NEW_BASELINE":
            badge_class = "badge-info"
            badge_text = "NEW BASELINE"
        elif r.status == "SIZE_MISMATCH":
            badge_class = "badge-warning"
            badge_text = "SIZE MISMATCH"
        else:
            badge_class = "badge-danger"
            badge_text = "MISMATCH"

        cur_url = rel_url(r.current_path) if r.current_path else ""
        base_url = rel_url(r.baseline_path) if r.baseline_path else ""
        diff_url = rel_url(r.diff_path) if r.diff_path else ""

        has_baseline = bool(base_url)
        has_diff = bool(diff_url)

        viewport_text = (
            f"{scenario.viewport[0]}x{scenario.viewport[1]}"
            if scenario
            else (f"{r.current_size[0]}x{r.current_size[1]}" if r.current_size else "N/A")
        )
        if scenario and scenario.full_page:
            viewport_text += " (Full Page)"
        if scenario and scenario.element_selector:
            viewport_text += " (Element)"

        cards_html.append(f"""
        <div class="test-card" id="card-{r.scenario_id}">
            <div class="card-header">
                <div class="card-title-wrap">
                    <span class="status-badge {badge_class}">{badge_text}</span>
                    <h3 class="card-title">{title}</h3>
                    <code class="scenario-id">#{r.scenario_id}</code>
                </div>
                <div class="card-meta">
                    <span class="meta-pill">📐 {viewport_text}</span>
                    <span class="meta-pill">📊 Diff: <strong>{r.diff_percent:.3f}%</strong> ({r.diff_pixels:,} px)</span>
                </div>
            </div>
            <p class="card-desc">{desc}</p>
            {f'<p class="card-msg">{r.message}</p>' if r.message else ''}

            <!-- Image View Tabs -->
            <div class="image-viewer" data-scenario="{r.scenario_id}">
                <div class="tab-buttons">
                    <button class="tab-btn active" onclick="switchTab('{r.scenario_id}', 'current')">Current Capture</button>
                    {f'<button class="tab-btn" onclick="switchTab(\'{r.scenario_id}\', \'baseline\')">Baseline</button>' if has_baseline else ''}
                    {f'<button class="tab-btn has-diff" onclick="switchTab(\'{r.scenario_id}\', \'diff\')">Diff Highlight</button>' if has_diff else ''}
                </div>

                <div class="tab-content" id="view-{r.scenario_id}">
                    <div class="tab-pane active" id="pane-{r.scenario_id}-current">
                        <div class="img-container">
                            <img src="{cur_url}" alt="Current Screenshot: {title}" loading="lazy" onclick="openModal(this.src, '{title} - Current')">
                        </div>
                    </div>
                    {f'''
                    <div class="tab-pane" id="pane-{r.scenario_id}-baseline" style="display: none;">
                        <div class="img-container">
                            <img src="{base_url}" alt="Baseline: {title}" loading="lazy" onclick="openModal(this.src, '{title} - Baseline')">
                        </div>
                    </div>
                    ''' if has_baseline else ''}
                    {f'''
                    <div class="tab-pane" id="pane-{r.scenario_id}-diff" style="display: none;">
                        <div class="img-container diff-img-container">
                            <img src="{diff_url}" alt="Diff: {title}" loading="lazy" onclick="openModal(this.src, '{title} - Visual Diff')">
                        </div>
                    </div>
                    ''' if has_diff else ''}
                </div>
            </div>
        </div>
        """)

    cards_joined = "\n".join(cards_html)
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Screenshot Test Report - Armenia Real Estate Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #23314f;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #06b6d4;
            --radius-md: 10px;
            --radius-lg: 14px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', -apple-system, sans-serif; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            padding: 2rem 1.5rem 4rem;
        }}
        .container {{
            max-width: 1440px;
            margin: 0 auto;
        }}
        header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.75rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .brand-title {{
            font-size: 1.6rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .brand-subtitle {{
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }}
        .timestamp {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1rem 1.25rem;
        }}
        .stat-label {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.35rem;
        }}
        .stat-value {{
            font-size: 1.75rem;
            font-weight: 800;
            line-height: 1;
        }}
        .stat-value.total {{ color: var(--accent); }}
        .stat-value.pass {{ color: var(--success); }}
        .stat-value.new {{ color: var(--info); }}
        .stat-value.fail {{ color: var(--danger); }}

        /* Filter Controls */
        .controls-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .filter-buttons {{
            display: inline-flex;
            gap: 0.5rem;
        }}
        .filter-btn {{
            background: var(--surface);
            color: var(--text-muted);
            border: 1px solid var(--border);
            padding: 0.45rem 0.9rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }}

        /* Test Cards */
        .test-cards {{
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}
        .test-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }}
        .card-title-wrap {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        .card-title {{
            font-size: 1.25rem;
            font-weight: 700;
        }}
        .scenario-id {{
            color: var(--text-muted);
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        .status-badge {{
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }}
        .badge-success {{ background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid var(--success); }}
        .badge-info {{ background: rgba(6, 182, 212, 0.15); color: var(--info); border: 1px solid var(--info); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid var(--warning); }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }}

        .card-meta {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .meta-pill {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .card-desc {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }}
        .card-msg {{
            color: #cbd5e1;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            margin-bottom: 1rem;
            display: inline-block;
        }}

        /* Viewer Tabs */
        .image-viewer {{
            margin-top: 1rem;
            background: #090d16;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            overflow: hidden;
        }}
        .tab-buttons {{
            display: flex;
            gap: 0.25rem;
            padding: 0.5rem 0.75rem;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border);
        }}
        .tab-btn {{
            background: transparent;
            color: var(--text-muted);
            border: none;
            padding: 0.4rem 0.85rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .tab-btn:hover {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
        }}
        .tab-btn.active {{
            background: var(--surface-hover);
            color: var(--accent);
        }}
        .tab-btn.has-diff {{
            color: #f43f5e;
        }}
        .tab-content {{
            padding: 1rem;
            display: flex;
            justify-content: center;
            background: radial-gradient(#151e33 1px, transparent 1px);
            background-size: 20px 20px;
        }}
        .tab-pane {{
            width: 100%;
            display: flex;
            justify-content: center;
        }}
        .img-container {{
            max-width: 100%;
            overflow: auto;
            border-radius: 6px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border);
            background: #ffffff;
        }}
        .img-container img {{
            display: block;
            max-width: 100%;
            height: auto;
            cursor: zoom-in;
            transition: opacity 0.2s ease;
        }}
        .diff-img-container {{
            background: #000000;
        }}

        /* Modal Lightbox */
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.88);
            backdrop-filter: blur(8px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }}
        .modal.open {{ display: flex; }}
        .modal-content {{
            max-width: 95vw;
            max-height: 95vh;
            overflow: auto;
            border-radius: var(--radius-md);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
        }}
        .modal-content img {{
            display: block;
            max-width: 100%;
            height: auto;
        }}
        .modal-close {{
            position: absolute;
            top: 1.5rem;
            right: 1.5rem;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border: none;
            width: 40px; height: 40px;
            border-radius: 50%;
            font-size: 1.25rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-close:hover {{ background: rgba(255, 255, 255, 0.25); }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-top">
                <div>
                    <h1 class="brand-title">📸 Website Screenshot Verification Report</h1>
                    <p class="brand-subtitle">Automated Visual Regression & Multi-Viewport Suite for Armenia Real Estate Hub</p>
                </div>
                <div class="timestamp">Generated: {timestamp_str} | Execution: {duration_seconds:.2f}s</div>
            </div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Scenarios</div>
                    <div class="stat-value total">{total_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Passed / Baseline</div>
                    <div class="stat-value pass">{pass_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">New Baselines</div>
                    <div class="stat-value new">{new_baseline_count}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Visual Mismatches</div>
                    <div class="stat-value fail">{mismatch_count}</div>
                </div>
            </div>
        </header>

        <div class="controls-bar">
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="filterCards('all')">All ({total_count})</button>
                <button class="filter-btn" onclick="filterCards('mismatch')">Mismatches ({mismatch_count})</button>
                <button class="filter-btn" onclick="filterCards('new')">New Baselines ({new_baseline_count})</button>
                <button class="filter-btn" onclick="filterCards('match')">Matches ({pass_count})</button>
            </div>
        </div>

        <div class="test-cards">
            {cards_joined}
        </div>
    </div>

    <!-- Lightbox Modal -->
    <div class="modal" id="imageModal" onclick="closeModal()">
        <button class="modal-close" onclick="closeModal()">✕</button>
        <div class="modal-content" onclick="event.stopPropagation()">
            <img id="modalImg" src="" alt="Enlarged View">
        </div>
    </div>

    <script>
        function switchTab(scenarioId, tabName) {{
            const viewer = document.querySelector(`.image-viewer[data-scenario="${{scenarioId}}"]`);
            if (!viewer) return;

            viewer.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            viewer.querySelectorAll('.tab-pane').forEach(pane => pane.style.display = 'none');

            const targetPane = document.getElementById(`pane-${{scenarioId}}-${{tabName}}`);
            if (targetPane) targetPane.style.display = 'flex';

            event.target.classList.add('active');
        }}

        function filterCards(type) {{
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const cards = document.querySelectorAll('.test-card');
            cards.forEach(card => {{
                if (type === 'all') {{
                    card.style.display = 'block';
                }} else if (type === 'mismatch') {{
                    const isMismatch = card.querySelector('.badge-danger, .badge-warning');
                    card.style.display = isMismatch ? 'block' : 'none';
                }} else if (type === 'new') {{
                    const isNew = card.querySelector('.badge-info');
                    card.style.display = isNew ? 'block' : 'none';
                }} else if (type === 'match') {{
                    const isMatch = card.querySelector('.badge-success, .badge-info');
                    card.style.display = isMatch ? 'block' : 'none';
                }}
            }});
        }}

        function openModal(src, title) {{
            const modal = document.getElementById('imageModal');
            const img = document.getElementById('modalImg');
            img.src = src;
            img.alt = title;
            modal.classList.add('open');
        }}

        function closeModal() {{
            document.getElementById('imageModal').classList.remove('open');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>
"""

    with open(report_output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return report_output_path
