"""
Image Comparison Engine for Visual Screenshot Testing.
Performs fast pixel-level comparison, mismatch calculations, and generates
visual difference highlight images.
"""

from dataclasses import dataclass
import os
from typing import Optional, Tuple
from PIL import Image, ImageChops


@dataclass
class ComparisonResult:
    scenario_id: str
    status: str  # "MATCH", "MISMATCH", "SIZE_MISMATCH", "NEW_BASELINE", "ERROR"
    is_match: bool
    diff_percent: float
    diff_pixels: int
    total_pixels: int
    baseline_size: Optional[Tuple[int, int]] = None
    current_size: Optional[Tuple[int, int]] = None
    baseline_path: Optional[str] = None
    current_path: Optional[str] = None
    diff_path: Optional[str] = None
    message: str = ""


class ImageComparator:
    """Compares baseline vs current images with pixel-level precision and diff image rendering."""

    def __init__(
        self,
        mismatch_threshold_percent: float = 0.1,
        color_tolerance: int = 10,
        highlight_color: Tuple[int, int, int, int] = (255, 0, 85, 220),
    ):
        """
        :param mismatch_threshold_percent: Maximum allowed pixel mismatch percentage (e.g. 0.1%).
        :param color_tolerance: Per-pixel channel tolerance to prevent subpixel font antialiasing false positives.
        :param highlight_color: RGBA color used to highlight mismatched pixels in the diff image.
        """
        self.mismatch_threshold_percent = mismatch_threshold_percent
        self.color_tolerance = color_tolerance
        self.highlight_color = highlight_color

    def compare(
        self,
        scenario_id: str,
        current_path: str,
        baseline_path: Optional[str],
        diff_output_path: Optional[str] = None,
    ) -> ComparisonResult:
        """Compares current screenshot against baseline screenshot."""
        if not os.path.exists(current_path):
            return ComparisonResult(
                scenario_id=scenario_id,
                status="ERROR",
                is_match=False,
                diff_percent=100.0,
                diff_pixels=0,
                total_pixels=0,
                current_path=current_path,
                baseline_path=baseline_path,
                message=f"Current screenshot not found at {current_path}",
            )

        if not baseline_path or not os.path.exists(baseline_path):
            # No baseline yet
            with Image.open(current_path) as cur_img:
                cur_size = cur_img.size
                total_pixels = cur_size[0] * cur_size[1]

            return ComparisonResult(
                scenario_id=scenario_id,
                status="NEW_BASELINE",
                is_match=True,
                diff_percent=0.0,
                diff_pixels=0,
                total_pixels=total_pixels,
                current_size=cur_size,
                current_path=current_path,
                baseline_path=baseline_path,
                message="No existing baseline found. Marked as new baseline.",
            )

        try:
            with Image.open(baseline_path) as b_img_raw, Image.open(current_path) as c_img_raw:
                b_size = b_img_raw.size
                c_size = c_img_raw.size

                b_img = b_img_raw.convert("RGB")
                c_img = c_img_raw.convert("RGB")

                size_mismatch = b_size != c_size

                # Align onto max dimensions canvas if sizes differ
                max_w = max(b_size[0], c_size[0])
                max_h = max(b_size[1], c_size[1])

                if size_mismatch:
                    canvas_b = Image.new("RGB", (max_w, max_h), (255, 255, 255))
                    canvas_c = Image.new("RGB", (max_w, max_h), (255, 255, 255))
                    canvas_b.paste(b_img, (0, 0))
                    canvas_c.paste(c_img, (0, 0))
                    comp_b = canvas_b
                    comp_c = canvas_c
                else:
                    comp_b = b_img
                    comp_c = c_img

                total_pixels = max_w * max_h

                # Compute fast difference
                raw_diff = ImageChops.difference(comp_b, comp_c)
                diff_gray = raw_diff.convert("L")

                # Apply noise tolerance threshold
                thresholded = diff_gray.point(lambda p: 255 if p > self.color_tolerance else 0)
                hist = thresholded.histogram()
                diff_pixels = hist[255] if len(hist) > 255 else 0

                diff_percent = (diff_pixels / total_pixels) * 100.0 if total_pixels > 0 else 0.0

                is_match = (not size_mismatch) and (diff_percent <= self.mismatch_threshold_percent)
                status = "MATCH" if is_match else ("SIZE_MISMATCH" if size_mismatch else "MISMATCH")

                # Generate diff visual image if there's any mismatch or diff_output_path is provided
                diff_path = None
                if diff_output_path and (diff_pixels > 0 or size_mismatch):
                    os.makedirs(os.path.dirname(os.path.abspath(diff_output_path)), exist_ok=True)
                    mask = thresholded.convert("1")

                    # Current screenshot as RGBA base, dimmed slightly for maximum contrast
                    current_rgba = comp_c.convert("RGBA")
                    dimmed = Image.blend(
                        current_rgba,
                        Image.new("RGBA", (max_w, max_h), (15, 23, 42, 255)),
                        0.25
                    )
                    highlight = Image.new("RGBA", (max_w, max_h), self.highlight_color)
                    dimmed.paste(highlight, (0, 0), mask)
                    dimmed.save(diff_output_path, "PNG")
                    diff_path = diff_output_path

                message = (
                    f"Match ({diff_percent:.3f}% diff)"
                    if is_match
                    else (
                        f"Size mismatch: baseline {b_size[0]}x{b_size[1]} vs current {c_size[0]}x{c_size[1]}"
                        if size_mismatch
                        else f"Visual mismatch: {diff_percent:.3f}% ({diff_pixels:,} px differs)"
                    )
                )

                return ComparisonResult(
                    scenario_id=scenario_id,
                    status=status,
                    is_match=is_match,
                    diff_percent=diff_percent,
                    diff_pixels=diff_pixels,
                    total_pixels=total_pixels,
                    baseline_size=b_size,
                    current_size=c_size,
                    baseline_path=baseline_path,
                    current_path=current_path,
                    diff_path=diff_path,
                    message=message,
                )

        except Exception as e:
            return ComparisonResult(
                scenario_id=scenario_id,
                status="ERROR",
                is_match=False,
                diff_percent=100.0,
                diff_pixels=0,
                total_pixels=0,
                baseline_path=baseline_path,
                current_path=current_path,
                message=f"Error comparing images: {str(e)}",
            )
