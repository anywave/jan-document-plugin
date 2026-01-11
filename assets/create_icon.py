#!/usr/bin/env python
"""
Generate a simple icon for Jan Document Plugin.
Requires: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a simple document-style icon."""
    sizes = [16, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Calculate proportions
        margin = size // 8
        doc_width = size - margin * 2
        doc_height = size - margin * 2
        fold_size = size // 4

        # Draw document shape (white with blue border)
        # Main document body
        doc_points = [
            (margin, margin),  # Top left
            (size - margin - fold_size, margin),  # Before fold
            (size - margin, margin + fold_size),  # After fold
            (size - margin, size - margin),  # Bottom right
            (margin, size - margin),  # Bottom left
        ]

        # Fill with white
        draw.polygon(doc_points, fill=(255, 255, 255, 255))

        # Draw border
        border_color = (59, 130, 246, 255)  # Blue
        draw.line(doc_points + [doc_points[0]], fill=border_color, width=max(1, size // 32))

        # Draw fold
        fold_points = [
            (size - margin - fold_size, margin),
            (size - margin - fold_size, margin + fold_size),
            (size - margin, margin + fold_size),
        ]
        draw.polygon(fold_points, fill=(229, 231, 235, 255))  # Light gray
        draw.line(fold_points, fill=border_color, width=max(1, size // 32))

        # Draw text lines to represent document content
        line_margin = margin + size // 6
        line_height = size // 10
        line_color = (156, 163, 175, 255)  # Gray

        for i in range(3):
            y = line_margin + (i * line_height * 2)
            if y + line_height < size - margin - size // 8:
                line_width = doc_width - size // 4 if i == 2 else doc_width - size // 6
                draw.rectangle(
                    [margin + size // 8, y, margin + line_width, y + line_height],
                    fill=line_color
                )

        images.append(img)

    # Save as ICO
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'icon.ico')

    # Save the largest image as the base, with all sizes embedded
    images[0].save(
        icon_path,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )

    print(f"Icon created: {icon_path}")
    return icon_path


if __name__ == "__main__":
    create_icon()
