# Private mobile testing through GitHub Codespaces

This is a **preview of Draft PR #6**, not a public deployment.

1. Open https://github.com/senddownrain/medjugorje-messages/pull/6
2. From the repository's **Code → Codespaces** menu, create a codespace using the `feat/pwa-first-screen` branch. On small mobile screens, creating a codespace may be easier in desktop-mode browser or on a computer.
3. The devcontainer installs Node dependencies and starts Vite on port `5173`.
4. In Codespaces open the **PORTS** tab. Keep port 5173 set to **Private**, then open its forwarded HTTPS link.
5. Append `/medjugorje-messages/` to the forwarded URL if it is not already present. On the phone, sign in to the **same GitHub account** that owns the codespace.
6. Test the reading view, filters, seven interface languages, independent message-language selection and light/dark settings.

**Important:** only RU/BE/UK texts are in the current JSON files. Selecting HR/EN/SK/LV must show a clear "archive being prepared" message, never invented translations. The code has seven language interface labels now; source texts for four more languages must still be imported.

This development preview uses a local Vite server, and its service worker is not enabled in dev mode. Full offline installation tests will be performed after a separate HTTPS production-style preview, before public release.

To stop cloud resource usage, **Stop codespace** in GitHub when finished. Codespaces availability and quotas depend on your GitHub plan and settings.

Fallback on a computer:

    npm install
    npm run dev

Open http://localhost:5173/medjugorje-messages/ on your computer; to test on the phone on the same Wi-Fi, use the computer's LAN IP and port 5173. This is a UI test, not an install/offline test.

## If Codespaces opens only the VS Code editor

A `*.github.dev` URL is the Codespaces **editor**, not the website. In its terminal, check `git branch --show-current` and ensure this PWA branch is selected. Then run `npm install` if needed and `npm run dev`; open **PORTS → 5173 → Open in Browser**. The forwarded site URL uses a different `*-5173.app.github.dev` hostname; visit `/medjugorje-messages/` on that site. Port visibility may remain **Private**; log into the same GitHub account in the phone browser. A localhost link from the terminal will not work directly in a different device.

While this is a draft, the branch may not contain data merged later into `main`. PWA preview and public hosting are separate operations.
