# Google Search Console verification

If Google asks you to upload an HTML file, place it here:

```
frontend/public/google<verification-code>.html
```

Or set the meta-tag method in `frontend/.env`:

```
NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=your-code-from-search-console
```

Then rebuild the frontend: `docker compose build frontend && docker compose up -d frontend`

## After deploy

1. Open https://search.google.com/search-console
2. Add property: `https://indiagovjob.online`
3. Verify via DNS TXT record (recommended) or meta tag above
4. Submit sitemap: `https://indiagovjob.online/sitemap.xml`
5. Request indexing for homepage and top job URLs
