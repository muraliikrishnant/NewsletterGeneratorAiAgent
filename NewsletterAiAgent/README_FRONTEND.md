TARS Newsletter Frontend

This is a minimal static frontend that calls a backend API for building, sending, and publishing newsletters.

Files:
- frontend/index.html: UI
- frontend/app.js: minimal JS to call /build, /send, /publish
- frontend/styles.css: basic styles

Deploying the frontend (quick):
1) Host static files on Vercel, Netlify, or GitHub Pages. For Vercel, connect the repo and set the output folder to `/frontend`.
2) Set an environment variable `API_BASE` in the frontend hosting (or edit `app.js` to hardcode the backend URL).
3) On Name.com, point your domain to the frontend host (CNAME/A depending on provider). Vercel provides exact DNS instructions.

Publishing to WordPress:
- The backend will expose a `/publish` endpoint that accepts a `token` and will publish the approved HTML to WordPress using Application Passwords (Basic auth). Configure WORDPRESS_URL, WP_USER, WP_APP_PASSWORD in backend env.

Security:
- Keep API keys in backend env only, not in frontend.

*** End ***