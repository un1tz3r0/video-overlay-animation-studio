# Deploying to Cloudflare

`deploy/wrangler.toml` publishes `dist/` as a Worker with static assets and no code.

1. Set `name` in `deploy/wrangler.toml`; it becomes `https://<name>.<account>.workers.dev`.
2. Log in once: `npx wrangler login`.
3. Build and deploy:

   ```sh
   npm run build && npm run deploy:cloudflare
   ```

A custom domain is added under **Workers & Pages → your worker → Settings → Domains & Routes**.

For Cloudflare Pages instead, `npx wrangler pages deploy dist --project-name <name>` uploads the same
folder.
