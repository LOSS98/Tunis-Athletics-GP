#!/usr/bin/env python3
import subprocess
import sys
import os


def build_css(watch=False):
    try:
        cmd = [
            "npx", "tailwindcss",
            "-i", "./static/css/tailwind.css",
            "-o", "./static/css/tailwind.min.css"
        ]

        if watch:
            cmd.append("--watch")
            print("🔄 Watching for CSS changes... (Press Ctrl+C to stop)")
        else:
            cmd.append("--minify")
            print("🏗️  Building CSS...")

        subprocess.run(cmd, check=True)

        if not watch:
            print("✅ CSS built successfully!")

    except subprocess.CalledProcessError as e:
        print(f"❌ CSS build failed: {e}")
        return False
    except FileNotFoundError:
        print("❌ Tailwind CLI not found. Run 'npm install' first.")
        return False
    except KeyboardInterrupt:
        if watch:
            print("\n👋 CSS watch stopped.")
        return True


if __name__ == "__main__":
    watch_mode = len(sys.argv) > 1 and sys.argv[1] == "watch"
    build_css(watch=watch_mode)