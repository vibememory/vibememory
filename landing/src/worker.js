// Only the selected API namespaces reach the private tunnel. All other paths are static assets.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/auth/') || url.pathname.startsWith('/v1/') || ['/health','/openapi.json'].includes(url.pathname)) {
      try {
        const target = new URL('http://127.0.0.1:8080');
        target.pathname = url.pathname; target.search = url.search;
        const headers = new Headers(request.headers);
        headers.delete('Host'); headers.delete('Forwarded');
        headers.delete('X-Forwarded-Host'); headers.delete('X-Forwarded-Proto');
        const upstream = await env.MEMORY_ORIGIN.fetch(new Request(target, {
          method: request.method, headers,
          body: ['GET','HEAD'].includes(request.method) ? undefined : request.body,
          redirect: 'manual'
        }));
        const response = new Response(upstream.body, upstream);
        response.headers.set('Cache-Control', 'no-store');
        response.headers.set('X-Content-Type-Options', 'nosniff');
        return response;
      } catch {
        return Response.json({detail:'기억 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'}, {status:503, headers:{'Cache-Control':'no-store'}});
      }
    }
    return env.ASSETS.fetch(request);
  }
};
