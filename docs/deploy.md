# Deploy Notes

## Current Target
- Domain: `https://ai-and-marketing.jp/`
- Server: `violetsheep5.sakura.ne.jp`
- Remote publish root: `~/www/`
- SSH alias is expected in `~/.ssh/config`

## Important Caution
- This site is deployed into `~/www/`, which already contains other files and directories.
- Do **not** run `rsync --delete` against the whole `~/www/` unless you have explicitly reviewed the full target set.
- Prefer syncing only the files or directories you actually changed.

## Local Preview
From the project root:

```bash
/Users/mizumayuuki/Downloads/aima_co/open.command
```

This starts a local server at `http://localhost:3000`.

## Basic Deploy Flow
1. Confirm the changed local files.
2. Create any missing remote directories.
3. `rsync` changed HTML/XML/TXT files to `~/www/`.
4. `rsync` changed asset directories to the matching path under `~/www/images/`.
5. Verify the live page with `curl`.

## Example: Article Deploy
For `blog-kakuyasu-llmo-daiko.html` and its assets:

```bash
ssh violetsheep5.sakura.ne.jp 'mkdir -p ~/www/images/blog-kakuyasu-llmo-daiko'

rsync -avz \
  blog-kakuyasu-llmo-daiko.html \
  blog.html \
  blog-llmo-taisaku.html \
  sitemap.xml \
  robots.txt \
  violetsheep5.sakura.ne.jp:~/www/

rsync -avz \
  images/blog-kakuyasu-llmo-daiko/ \
  violetsheep5.sakura.ne.jp:~/www/images/blog-kakuyasu-llmo-daiko/
```

## Verification Commands
Check that the files exist on the server:

```bash
ssh violetsheep5.sakura.ne.jp \
  'ls -lh ~/www/blog-kakuyasu-llmo-daiko.html ~/www/blog.html ~/www/sitemap.xml ~/www/images/blog-kakuyasu-llmo-daiko/eyecatch.webp'
```

Check the live response:

```bash
curl -I https://ai-and-marketing.jp/blog-kakuyasu-llmo-daiko.html
curl -L -s https://ai-and-marketing.jp/blog-kakuyasu-llmo-daiko.html | rg 'FAQPage|og:image|max-image-preview'
```

## When SEO Files Change
If any of the following change, include them in the deploy set:
- `sitemap.xml`
- `robots.txt`
- article HTML files
- article OGP / eyecatch images
- `blog.html`

## Notes
- Current article assets live under `images/{slug}/`.
- For new articles, create the remote image directory first if it does not exist.
- If you only changed one asset file, you can sync that single file instead of the whole directory.
