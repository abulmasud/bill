#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Render সার্ভারে Chromium ব্রাউজার ডাউনলোড করার কমান্ড
playwright install chromium