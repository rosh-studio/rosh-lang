#!/usr/bin/env python3
"""
Generate 2D sprite thumbnails from 3D GLB models.

This script scans the assets/3d_glb/ folder and generates PNG thumbnails
for use in 2D game engines (Phaser, Pygame).

Usage:
    python scripts/generate-2d-sprites.py

Requirements:
    pip install trimesh pyglet pillow numpy

The script will:
1. Load each GLB model
2. Render from a standard front-facing angle
3. Save as PNG to assets/sprites/generated/
4. Print suggested known_objects.toml updates
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import trimesh
    except ImportError:
        missing.append("trimesh")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def render_glb_to_png(glb_path: Path, output_path: Path, size: int = 128) -> bool:
    """
    Render a GLB model to a PNG thumbnail.

    Uses trimesh to load the model and render a simple view.
    """
    import trimesh
    import numpy as np
    from PIL import Image

    try:
        # Load the GLB file
        scene = trimesh.load(str(glb_path))

        # Convert scene to mesh if needed
        if isinstance(scene, trimesh.Scene):
            # Combine all meshes in the scene
            meshes = []
            for name, geom in scene.geometry.items():
                if isinstance(geom, trimesh.Trimesh):
                    meshes.append(geom)
            if not meshes:
                print(f"  No meshes found in {glb_path.name}")
                return False
            mesh = trimesh.util.concatenate(meshes)
        else:
            mesh = scene

        # Center and normalize the mesh
        mesh.vertices -= mesh.centroid
        scale = 1.0 / max(mesh.extents)
        mesh.vertices *= scale

        # Try to render using pyrender if available
        try:
            import pyrender

            # Create scene
            pr_scene = pyrender.Scene(bg_color=[0, 0, 0, 0])  # Transparent background

            # Create mesh with default material
            pr_mesh = pyrender.Mesh.from_trimesh(mesh)
            pr_scene.add(pr_mesh)

            # Add light
            light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=3.0)
            pr_scene.add(light, pose=np.eye(4))

            # Add camera - front view
            camera = pyrender.OrthographicCamera(xmag=0.8, ymag=0.8)
            camera_pose = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 2],
                [0, 0, 0, 1]
            ])
            pr_scene.add(camera, pose=camera_pose)

            # Render
            renderer = pyrender.OffscreenRenderer(size, size)
            color, depth = renderer.render(pr_scene, flags=pyrender.RenderFlags.RGBA)
            renderer.delete()

            # Save image
            img = Image.fromarray(color)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(output_path))
            return True

        except ImportError:
            # Fall back to simple silhouette rendering
            return render_silhouette(mesh, output_path, size)

    except Exception as e:
        print(f"  Error processing {glb_path.name}: {e}")
        return False


def render_silhouette(mesh, output_path: Path, size: int = 128) -> bool:
    """
    Render a simple 2D silhouette of the mesh.

    Projects vertices onto XY plane and creates a filled shape.
    """
    import numpy as np
    from PIL import Image, ImageDraw

    try:
        # Get 2D projection of vertices (front view - XY plane)
        vertices_2d = mesh.vertices[:, :2]  # Take X and Y

        # Normalize to image coordinates
        min_coords = vertices_2d.min(axis=0)
        max_coords = vertices_2d.max(axis=0)
        range_coords = max_coords - min_coords

        # Add padding
        padding = 0.1
        vertices_2d = (vertices_2d - min_coords) / range_coords
        vertices_2d = vertices_2d * (1 - 2 * padding) + padding
        vertices_2d *= size

        # Flip Y for image coordinates
        vertices_2d[:, 1] = size - vertices_2d[:, 1]

        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw convex hull as filled shape
        from scipy.spatial import ConvexHull
        try:
            hull = ConvexHull(vertices_2d)
            hull_points = [(vertices_2d[i, 0], vertices_2d[i, 1]) for i in hull.vertices]

            # Use a nice color based on mesh (could extract from texture)
            fill_color = (200, 180, 150, 255)  # Beige/stone color
            outline_color = (100, 80, 60, 255)

            draw.polygon(hull_points, fill=fill_color, outline=outline_color)
        except Exception:
            # If convex hull fails, draw points
            for x, y in vertices_2d:
                draw.ellipse([x-1, y-1, x+1, y+1], fill=(200, 180, 150, 255))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))
        return True

    except Exception as e:
        print(f"  Silhouette error: {e}")
        return False


def main():
    """Main entry point."""
    print("=" * 60)
    print("Rosh 2D Sprite Generator")
    print("Generating thumbnails from 3D GLB models")
    print("=" * 60)

    if not check_dependencies():
        sys.exit(1)

    # Find all GLB files
    glb_dir = PROJECT_ROOT / "assets" / "3d_glb"
    output_dir = PROJECT_ROOT / "assets" / "sprites" / "generated"

    if not glb_dir.exists():
        print(f"GLB directory not found: {glb_dir}")
        sys.exit(1)

    glb_files = sorted(glb_dir.glob("*.glb"))
    print(f"\nFound {len(glb_files)} GLB models")
    print(f"Output directory: {output_dir}\n")

    # Process each GLB file
    success = []
    failed = []
    toml_updates = []

    for glb_path in glb_files:
        name = glb_path.stem
        output_path = output_dir / f"{name}.png"

        print(f"Processing: {name}")

        if render_glb_to_png(glb_path, output_path):
            print(f"  -> {output_path.relative_to(PROJECT_ROOT)}")
            success.append(name)
            toml_updates.append(f'[{name}.2d]\nsprite = "sprites/generated/{name}.png"')
        else:
            failed.append(name)

    # Summary
    print("\n" + "=" * 60)
    print(f"Generated: {len(success)} sprites")
    if failed:
        print(f"Failed: {len(failed)} - {', '.join(failed)}")

    # Print TOML suggestions
    if toml_updates:
        print("\n" + "=" * 60)
        print("Add to known_objects.toml:")
        print("-" * 60)
        for update in toml_updates[:5]:  # Show first 5
            print(update)
            print()
        if len(toml_updates) > 5:
            print(f"... and {len(toml_updates) - 5} more")

    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
