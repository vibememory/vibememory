# Third-party notices

The MIT license in this repository covers Vibe Memory project code. It does not grant trademark rights or relicense third-party assets and dependencies.

## Service identification assets

The Claude Code, Codex, OpenClaw, and Hermes icons identify the respective services. The trademarks and original artwork belong to their respective owners. They are not Vibe Memory marks, and their inclusion does not imply endorsement or a special integration partnership.

The unmodified source URLs, retrieval timestamps, and SHA-256 checksums are recorded in [`landing/brand-assets.json`](landing/brand-assets.json). Assets were obtained from the services' official sites or the official OpenAI publisher's Visual Studio Marketplace distribution.

## Font

The bundled `landing/dist/assets/vibe-sans.woff2` is a subset of Noto Sans KR from the [Noto CJK project](https://github.com/notofonts/noto-cjk). Its SIL Open Font License is included at [`landing/dist/assets/OFL.txt`](landing/dist/assets/OFL.txt).

## Cytoscape.js

The web console uses [Cytoscape.js](https://js.cytoscape.org/) 3.34.4 for relationship graph visualization.

Copyright (c) 2016-2026, The Cytoscape Consortium.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Dependencies and embedding model

Python and frontend tooling dependencies retain their own licenses. Exact package versions are recorded in `uv.lock` and `landing/package-lock.json`. Container base images retain their own licenses. The Compose stack uses the PostgreSQL-licensed PostgreSQL server and the PostgreSQL-licensed pgvector extension; they are distributed by their respective container image maintainers.

The default embedding model, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, is downloaded at runtime rather than distributed in this repository. Review its model card and license before changing or redistributing it.
