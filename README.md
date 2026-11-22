# Ball Escape Auto Shorts

This repository generates a vertical physics-style Ball Escape short and schedules it through Metricool.

## Schedule
- GitHub Actions runs every 2 hours at minute 15 (UTC).
- The current renderer outputs 720x1280, 30 FPS, 30 seconds.
- A public GitHub Release asset is created for each rendered MP4.
- Metricool schedules the video to YouTube Shorts and TikTok in the Asia/Baghdad timezone.

## One-time Metricool setup
1. Metricool API access is available on Advanced and Custom plans. In Metricool, open Account Settings → API and copy the REST API access token.
2. In this GitHub repository, open Settings → Secrets and variables → Actions → New repository secret.
3. Add a secret named METRICOOL_API_TOKEN and paste the Metricool token as its value. Never put the token in source code or commit it.
4. Ensure GitHub Actions is enabled for this repository.

The connected Metricool brand configured here is blogId 8234676 and userId 6485386. Do not change these unless the target brand changes.

If METRICOOL_API_TOKEN is missing, generation and artifact/release creation still run, but publication is skipped.

## Manual run
Open the Actions tab, choose “Ball Escape - Generate and Publish”, then select “Run workflow”.

## Files
- src/simulator.py — procedural ring/ball simulation and original synthesized impact sounds
- src/publish_metricool.py — Metricool scheduler integration
- .github/workflows/auto_publish.yml — two-hour generation and publication workflow
