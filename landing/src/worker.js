// Only the selected API namespaces reach the private tunnel. All other paths are static assets.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const sessionCookie = request.headers.get('Cookie') || '';
    const hasSession = /(?:^|;\s*)vm_session=/.test(sessionCookie);
    if (url.pathname === '/' && ['GET', 'HEAD'].includes(request.method) && hasSession) {
      try {
        const target = new URL('http://127.0.0.1:8080/auth/me');
        const headers = new Headers(request.headers);
        headers.delete('Host'); headers.delete('Forwarded');
        headers.set('X-Forwarded-Host', url.host);
        headers.set('X-Forwarded-Proto', url.protocol.slice(0, -1));
        const session = await env.MEMORY_ORIGIN.fetch(new Request(target, {
          method: 'GET', headers, redirect: 'manual'
        }));
        const signedIn = session.ok;
        await session.body?.cancel();
        if (signedIn) {
          return new Response(null, {
            status: 302,
            headers: {'Location':'/console', 'Cache-Control':'no-store',
              'Strict-Transport-Security':'max-age=31536000; includeSubDomains'}
          });
        }
      } catch { /* A session-check failure must not make the public landing unavailable. */ }
    }
    const apiPath = url.pathname.startsWith('/auth/')
      || url.pathname.startsWith('/v1/')
      || url.pathname.startsWith('/oauth/')
      || url.pathname.startsWith('/.well-known/')
      || ['/mcp','/health','/openapi.json'].includes(url.pathname);
    if (apiPath) {
      try {
        const target = new URL('http://127.0.0.1:8080');
        target.pathname = url.pathname; target.search = url.search;
        const headers = new Headers(request.headers);
        headers.delete('Host'); headers.delete('Forwarded');
        headers.set('X-Forwarded-Host', url.host);
        headers.set('X-Forwarded-Proto', url.protocol.slice(0, -1));
        const upstream = await env.MEMORY_ORIGIN.fetch(new Request(target, {
          method: request.method, headers,
          body: ['GET','HEAD'].includes(request.method) ? undefined : request.body,
          redirect: 'manual'
        }));
        const response = new Response(upstream.body, upstream);
        response.headers.set('Cache-Control', 'no-store');
        response.headers.set('X-Content-Type-Options', 'nosniff');
        response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
        return response;
      } catch {
        return Response.json({detail:'기억 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'}, {status:503, headers:{'Cache-Control':'no-store','Strict-Transport-Security':'max-age=31536000; includeSubDomains'}});
      }
    }
    return env.ASSETS.fetch(request);
  }
};
