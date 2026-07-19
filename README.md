# bettersandeep.com

Personal website of Sandeep Singh, live at [bettersandeep.com](https://bettersandeep.com).

Built with [Hugo](https://gohugo.io/) using the [hugo-coder](https://github.com/luizdepra/hugo-coder) theme, deployed on Cloudflare Workers.

## Stack

- Hugo (extended) for the static site
- hugo-coder theme, pulled in as a git submodule at `themes/hugo-coder`
- Cloudflare Workers for hosting, configured via `wrangler.toml`
- `build.sh` installs Hugo and builds the site on Cloudflare's build machines

## Local development

```sh
git clone --recurse-submodules https://github.com/bettersandeep/bettersandeep-com.git
cd bettersandeep-com
hugo server
```

The site is served at http://localhost:1313 with live reload.
If you cloned without submodules, run `git submodule update --init` first.

Requires Hugo extended (`brew install hugo` on macOS).

## Writing content

```sh
hugo new content posts/my-post-title.md
```

New content is created as a draft (see `archetypes/default.md`).
Set `draft = false` in the front matter to publish.
Preview drafts locally with `hugo server -D`.

## Deployment

Cloudflare Workers builds and deploys on every push to `main`.
The build command in `wrangler.toml` runs `build.sh`, which ends with `hugo --gc --minify` and serves the resulting `public/` directory as static assets.
There is nothing to deploy manually.

## Configuration

All site config lives in `hugo.toml`: title, social links, menu entries and theme params.
