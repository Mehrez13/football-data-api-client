export default function middleware(request) {
  const expectedUser = process.env.DASHBOARD_USER;
  const expectedPassword = process.env.DASHBOARD_PASSWORD;

  if (!expectedUser || !expectedPassword) {
    return new Response(
      "Auth non configuree : definis DASHBOARD_USER et DASHBOARD_PASSWORD dans les variables d'environnement du projet Vercel.",
      { status: 500 }
    );
  }

  const authHeader = request.headers.get("authorization");
  const expected = "Basic " + btoa(`${expectedUser}:${expectedPassword}`);

  if (authHeader === expected) {
    return;
  }

  return new Response("Authentification requise.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Acces prive"' },
  });
}

export const config = {
  matcher: "/:path*",
};
