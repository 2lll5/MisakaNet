# Cloudflare Worker for MisakaNet

## Overview
Intelligent routing Worker that detects AI agents and returns optimized responses.

## Worker Code

Create `worker.js`:

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const userAgent = request.headers.get('User-Agent') || '';
    
    // 1. Detect AI agent type
    const agentType = detectAIAgent(userAgent);
    
    // 2. Return structured data for AI agents
    if (agentType && shouldReturnStructuredData(agentType, url.pathname)) {
      return returnStructuredResponse(request, agentType);
    }
    
    // 3. Handle API endpoints
    if (url.pathname.startsWith('/api/')) {
      return await handleAPIRequest(request);
    }
    
    // 4. Normal HTML response with AI-friendly headers
    const response = await fetch(request);
    
    // Add AI-friendly response headers
    const newResponse = new Response(response.body, response);
    newResponse.headers.set('X-AI-Agent-Support', 'true');
    newResponse.headers.set('X-Content-Signals-Policy', 'allow');
    newResponse.headers.set('X-Misaka-Status', 'verified');
    newResponse.headers.set('Vary', 'Accept');
    
    return newResponse;
  }
};

function detectAIAgent(userAgent) {
  const patterns = {
    'openai': /GPTBot|ChatGPT-User|OAI-SearchBot/i,
    'anthropic': /ClaudeBot|Claude-SearchBot|Claude-User/i,
    'google': /Googlebot|-Bot|Google-CloudVertexBot/i,
    'perplexity': /PerplexityBot|Perplexity-User/i,
    'meta': /facebookexternalagent|Meta-External|FacebookBot/i,
    'microsoft': /MSNBOT|Bingbot/i,
    'amazon': /Amazonbot/i,
    'apple': /Applebot/i,
  };
  
  for (const [type, pattern] of Object.entries(patterns)) {
    if (pattern.test(userAgent)) {
      return type;
    }
  }
  
  // Check for verified agent via auth headers
  const hasAuth = request.headers.get('Authorization') === 'Bearer verified-agent';
  if (hasAuth) {
    return 'deduced-verified';
  }
  
  return null;
}

function shouldReturnStructuredData(agentType, pathname) {
  const structuredEndpoints = ['/api', '/articles', '/docs', '/open'];
  return structuredEndpoints.some(path => pathname.includes(path));
}

async function returnStructuredResponse(request, agentType) {
  const url = new URL(request.url);
  
  // Return compact format for AI agents
  if (url.pathname === '/api/public-content') {
    return new Response(JSON.stringify({
      format: 'ai-optimized',
      timestamp: new Date().toISOString(),
      data: await fetchAccessibleData()
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  // Return simplified page content
  const html = await fetch(request.url).then(r => r.text());
  return new Response(html.replace('</head>', 
    '<link rel="alternate" type="application/ld+json" href="/api/schema">' +
    '</head>'), {
    headers: { 'Content-Type': 'text/html' }
  });
}

async function handleAPIRequest(request) {
  const url = new URL(request.url);
  
  // API version detection
  if (url.pathname === '/api/robots-txt') {
    return new Response(`User-agent: *
Allow: /public/
Allow: /open/
Allow: /docs/
Disallow: /api/private/
Sitemap: https://misakanet.org/sitemap.xml`, {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
  
  if (url.pathname === '/api/content-signals') {
    return new Response(JSON.stringify({
      version: '1.0',
      policy: 'allow',
      supportedUseCases: ['training', 'search', 'agent'],
      attributionRequired: false
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  if (url.pathname === '/api/schema') {
    return new Response(JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "MisakaNet",
      "url": "https://misakanet.org",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://misakanet.org/api/search?q={search_term_string}"
      }
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  // Default API routing
  return fetch(request);
}

async function fetchAccessibleData() {
  // Fetch from D1 or R2
  return [{ id: 1, title: 'Sample AI Knowledge' }];
}
```

## Deployment

### 1. Install Wrangler
```bash
npm install -g wrangler
```

### 2. Login to Cloudflare
```bash
wrangler login
```

### 3. Create Worker
```bash
# Create worker project
wrangler init misaka-net-ai-routing

# Or deploy directly
wrangler deploy --name misaka-net-ai-routing
```

### 4. Configure Routes
In Cloudflare Dashboard > Workers & Pages:
1. Select your worker
2. Go to Triggers
3. Add route: `misakanet.org/api/*`
4. Add route: `misakanet.org/open/*`
5. Add route: `misakanet.org/docs/*`

### 5. Test
```bash
# Test AI agent detection
curl -H "User-Agent: GPTBot/1.0" https://misakanet.org/api/content-signals

# Test normal access
curl https://misakanet.org/

# Test robots.txt
curl https://misakanet.org/api/robots-txt
```

## Features

- **AI Agent Detection**: Identifies GPTBot, ClaudeBot, etc.
- **Structured Data**: Returns JSON for AI agents
- **Response Headers**: Adds AI-friendly headers
- **API Routing**: Handles /api/* endpoints
- **Caching**: Leverages Cloudflare edge caching

## Monitoring

Monitor in:
- Workers & Pages > Analytics
- Workers & Pages > Logs
- Security > Bots > Analytics
