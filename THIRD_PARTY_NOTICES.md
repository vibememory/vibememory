# Third-party notices

The MIT license in this repository covers Vibe Memory project code. It does not grant trademark rights or relicense third-party assets and dependencies.

## Service identification assets

The Claude Code, Codex, OpenClaw, and Hermes icons identify the respective services. The trademarks and original artwork belong to their respective owners. They are not Vibe Memory marks, and their inclusion does not imply endorsement or a special integration partnership.

The unmodified source URLs, retrieval timestamps, and SHA-256 checksums are recorded in [`landing/brand-assets.json`](landing/brand-assets.json). Assets were obtained from the services' official sites or the official OpenAI publisher's Visual Studio Marketplace distribution.

## Font

The bundled `landing/dist/assets/vibe-sans.woff2` is a subset of Noto Sans KR from the [Noto CJK project](https://github.com/notofonts/noto-cjk). Its SIL Open Font License is included at [`landing/dist/assets/OFL.txt`](landing/dist/assets/OFL.txt).

## Dependencies and embedding model

Python and frontend tooling dependencies retain their own licenses. Exact package versions are recorded in `uv.lock` and `landing/package-lock.json`. Container base images retain their own licenses.

The default embedding model, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, is downloaded at runtime rather than distributed in this repository. Review its model card and license before changing or redistributing it.
