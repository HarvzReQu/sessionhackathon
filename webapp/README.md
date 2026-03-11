# DOOMDADA Web Lobby (Kahoot Style)

This is a web MVP for your bootcamp workshop:
- Students open your site (`doomdada.com`)
- They join with a lobby code
- Admin can see live visitor counts (players + spectators)

## Features
- Admin page creates room code
- Student join page accepts room code + name + role
- Live stats for admin: total visitors, players, spectators, participant list
- Public stats for students after joining

## Quick Start (Local)
1. Open terminal in project root.
2. Install dependencies:
   - `pip install -r webapp/requirements.txt`
3. Run server:
   - `uvicorn webapp.app:app --reload --host 0.0.0.0 --port 8000`
4. Open:
   - Student page: `http://localhost:8000/`
   - Admin page: `http://localhost:8000/admin`

## Production Domain (doomdada.com)
Use a reverse proxy (Nginx/Caddy) to route your domain to this app.

Recommended:
- Deploy API+pages on Render/Railway/Fly.io
- Point `doomdada.com` DNS to deployment
- Use HTTPS certificate (auto via platform)

## Deploy On Render (Fastest)
1. Push this repository to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select your GitHub repository.
4. Render will detect `render.yaml` at the project root and create the service automatically.
5. Wait for the first deploy to complete, then open the generated URL.
6. Test:
   - Admin: `/admin`
   - Player: `/`

### Custom Domain
1. In Render service settings, add your custom domain.
2. Add the DNS records exactly as Render shows in your registrar.
3. Wait for SSL to be issued, then test both pages again.

## Notes
- This MVP uses in-memory storage. If server restarts, lobbies reset.
- For real workshop usage, add PostgreSQL/Redis persistence and authentication.
- Admin token is currently shown only in browser memory. Add secure auth before public launch.
- Desktop Tkinter game launch is only attempted on localhost; public players use the browser game flow.
