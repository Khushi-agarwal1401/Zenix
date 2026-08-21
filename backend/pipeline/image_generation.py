"""
Image Generation Module for Zenix AI.
Provides image generation using free APIs and fallbacks.
Supports: chart generation, diagram creation, placeholder images.
"""

import os
import json
import logging
import tempfile
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    """Result of image generation."""
    success: bool
    image_path: Optional[str]
    image_url: Optional[str]
    image_type: str  # "chart", "diagram", "placeholder", "generated"
    error: Optional[str] = None


class ImageGenerator:
    """
    Generate images using free APIs and local libraries.
    Supports charts, diagrams, and placeholder images.
    """

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="zenix_images_")
        self._matplotlib_available = None
        self._pillow_available = None

    def _check_matplotlib(self) -> bool:
        """Check if matplotlib is available."""
        if self._matplotlib_available is not None:
            return self._matplotlib_available
        try:
            import matplotlib
            self._matplotlib_available = True
        except ImportError:
            self._matplotlib_available = False
        return self._matplotlib_available

    def _check_pillow(self) -> bool:
        """Check if Pillow is available."""
        if self._pillow_available is not None:
            return self._pillow_available
        try:
            from PIL import Image
            self._pillow_available = True
        except ImportError:
            self._pillow_available = False
        return self._pillow_available

    def generate_chart(self, chart_type: str, data: Dict[str, Any],
                      title: str = "", labels: list = None) -> GeneratedImage:
        """
        Generate a chart using matplotlib.

        Args:
            chart_type: "bar", "line", "pie", "scatter"
            data: Chart data
            title: Chart title
            labels: Axis labels

        Returns:
            GeneratedImage with path to the chart
        """
        if not self._check_matplotlib():
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="chart",
                error="matplotlib not installed. Install with: pip install matplotlib"
            )

        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))

            if chart_type == "bar":
                x = list(range(len(data)))
                values = list(data.values())
                keys = list(data.keys())
                ax.bar(x, values, color='#FF6B35')
                ax.set_xticks(x)
                ax.set_xticklabels(keys, rotation=45, ha='right')
                ax.set_ylabel(labels[1] if labels and len(labels) > 1 else "Value")

            elif chart_type == "line":
                x = list(range(len(data)))
                values = list(data.values())
                keys = list(data.keys())
                ax.plot(x, values, marker='o', color='#FF6B35', linewidth=2)
                ax.set_xticks(x)
                ax.set_xticklabels(keys, rotation=45, ha='right')
                ax.set_ylabel(labels[1] if labels and len(labels) > 1 else "Value")

            elif chart_type == "pie":
                values = list(data.values())
                keys = list(data.keys())
                colors = ['#FF6B35', '#004E89', '#1A936F', '#F3DE2C', '#7B2D8E',
                         '#E63946', '#457B9D', '#2A9D8F']
                ax.pie(values, labels=keys, autopct='%1.1f%%', colors=colors[:len(keys)])
                ax.axis('equal')

            elif chart_type == "scatter":
                x = data.get('x', list(range(len(data.get('y', [])))))
                y = data.get('y', list(data.values()))
                ax.scatter(x, y, color='#FF6B35', s=100, alpha=0.7)
                if labels and len(labels) >= 2:
                    ax.set_xlabel(labels[0])
                    ax.set_ylabel(labels[1])

            else:
                return GeneratedImage(
                    success=False,
                    image_path=None,
                    image_url=None,
                    image_type="chart",
                    error=f"Unsupported chart type: {chart_type}"
                )

            ax.set_title(title or "Chart", fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()

            # Save chart
            chart_path = os.path.join(self.temp_dir, f"chart_{hash(title)}.png")
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

            return GeneratedImage(
                success=True,
                image_path=chart_path,
                image_url=None,
                image_type="chart",
            )

        except Exception as e:
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="chart",
                error=f"Chart generation failed: {str(e)}"
            )

    def generate_comparison_chart(self, data: Dict[str, list],
                                 title: str = "Comparison") -> GeneratedImage:
        """Generate a comparison bar chart."""
        if not self._check_matplotlib():
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="chart",
                error="matplotlib not installed"
            )

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            categories = list(data.keys())
            values = list(data.values())

            fig, ax = plt.subplots(figsize=(10, 6))

            x = np.arange(len(categories))
            width = 0.35

            if all(isinstance(v, list) and len(v) == 2 for v in values):
                # Grouped bar chart
                group1 = [v[0] for v in values]
                group2 = [v[1] for v in values]
                ax.bar(x - width/2, group1, width, label='Current', color='#FF6B35')
                ax.bar(x + width/2, group2, width, label='Previous', color='#004E89')
                ax.legend()
            else:
                # Simple bar chart
                ax.bar(x, values, color='#FF6B35')

            ax.set_xlabel('Categories')
            ax.set_ylabel('Values')
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()

            chart_path = os.path.join(self.temp_dir, f"comparison_{hash(title)}.png")
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

            return GeneratedImage(
                success=True,
                image_path=chart_path,
                image_url=None,
                image_type="chart",
            )

        except Exception as e:
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="chart",
                error=f"Comparison chart failed: {str(e)}"
            )

    def create_placeholder(self, text: str, width: int = 400,
                          height: int = 200, bg_color: str = "#FF6B35") -> GeneratedImage:
        """
        Create a placeholder image with text.

        Args:
            text: Text to display
            width: Image width
            height: Image height
            bg_color: Background color (hex)

        Returns:
            GeneratedImage with path to the placeholder
        """
        if not self._check_pillow():
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="placeholder",
                error="Pillow not installed. Install with: pip install Pillow"
            )

        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create image
            img = Image.new('RGB', (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Try to use a font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except (IOError, OSError):
                font = ImageFont.load_default()

            # Calculate text position (centered)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2

            # Draw text
            draw.text((x, y), text, fill="white", font=font)

            # Save image
            img_path = os.path.join(self.temp_dir, f"placeholder_{hash(text)}.png")
            img.save(img_path)

            return GeneratedImage(
                success=True,
                image_path=img_path,
                image_url=None,
                image_type="placeholder",
            )

        except Exception as e:
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="placeholder",
                error=f"Placeholder creation failed: {str(e)}"
            )

    def generate_flowchart(self, steps: list, title: str = "Flowchart") -> GeneratedImage:
        """
        Generate a simple flowchart.

        Args:
            steps: List of step descriptions
            title: Flowchart title

        Returns:
            GeneratedImage with path to the flowchart
        """
        if not self._check_matplotlib():
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="diagram",
                error="matplotlib not installed"
            )

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches

            fig, ax = plt.subplots(figsize=(10, max(6, len(steps) * 1.2)))

            # Draw flowchart boxes
            y_positions = list(range(len(steps) - 1, -1, -1))
            box_height = 0.6
            box_width = 0.8

            for i, (step, y) in enumerate(zip(steps, y_positions)):
                # Draw box
                rect = mpatches.FancyBboxPatch(
                    (0.1, y - box_height/2), box_width, box_height,
                    boxstyle="round,pad=0.1",
                    facecolor='#FF6B35' if i == 0 else '#004E89' if i == len(steps) - 1 else '#1A936F',
                    edgecolor='black',
                    linewidth=2
                )
                ax.add_patch(rect)

                # Add text
                ax.text(0.5, y, f"{i+1}. {step}", ha='center', va='center',
                       fontsize=10, fontweight='bold', color='white')

                # Draw arrow to next step
                if i < len(steps) - 1:
                    ax.annotate('', xy=(0.5, y_positions[i+1] + box_height/2),
                               xytext=(0.5, y - box_height/2),
                               arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

            ax.set_xlim(-0.1, 1.1)
            ax.set_ylim(-0.5, len(steps) + 0.5)
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            ax.axis('off')

            plt.tight_layout()

            diagram_path = os.path.join(self.temp_dir, f"flowchart_{hash(title)}.png")
            plt.savefig(diagram_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

            return GeneratedImage(
                success=True,
                image_path=diagram_path,
                image_url=None,
                image_type="diagram",
            )

        except Exception as e:
            return GeneratedImage(
                success=False,
                image_path=None,
                image_url=None,
                image_type="diagram",
                error=f"Flowchart generation failed: {str(e)}"
            )

    def get_supported_types(self) -> list:
        """Get list of supported image types."""
        return ["bar_chart", "line_chart", "pie_chart", "scatter_plot",
                "comparison_chart", "flowchart", "placeholder"]

    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


# Singleton instance
_image_generator = None


def get_image_generator() -> ImageGenerator:
    """Get or create the image generator singleton."""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
