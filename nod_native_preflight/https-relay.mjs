import {createServer} from 'node:https';
import {request} from 'node:http';
import {isIP} from 'node:net';

function ipv4(value) {
  if (value?.startsWith('::ffff:')) value=value.slice(7);
  if(isIP(value)!==4) return null;
  return value.split('.').reduce((n,octet)=>(n*256+Number(octet))>>>0,0);
}

export function privateNetwork(cidr) {
  const [address,prefix,...rest]=String(cidr).split('/');
  const base=ipv4(address), bits=Number(prefix);
  if(rest.length || base===null || !/^\d+$/.test(prefix || '') || bits<24 || bits>32)
    throw new Error('Expected an IPv4 private CIDR with prefix 24–32');
  if(!/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(address))
    throw new Error('Only RFC1918 networks are permitted');
  const mask=(0xffffffff << (32-bits))>>>0;
  if(((base&mask)>>>0)!==base) throw new Error('Use the network address in the CIDR');
  return value=>{const ip=ipv4(value);return ip!==null && ((ip&mask)>>>0)===base;};
}

function end(res,status) {
  res.writeHead(status,{'Cache-Control':'no-store','Content-Type':'text/plain; charset=utf-8'});
  res.end(status===403?'Forbidden':'Unavailable');
}

function cleanHeaders(headers) {
  const out={...headers};
  const named=String(out.connection || '').split(',').map(x=>x.trim().toLowerCase()).filter(Boolean);
  for(const key of [...named,'connection','keep-alive','proxy-authorization','proxy-authenticate',
    'te','trailer','transfer-encoding','upgrade','forwarded','x-forwarded-for','x-forwarded-host',
    'x-forwarded-proto','x-real-ip']) delete out[key];
  return out;
}

// The caller must provision a dedicated certificate and restrict the listening network.
// No owner token injection, origin rewriting, or public forwarding.
export function createNodRelay({key,cert,origin,allowPeer}) {
  const url=new URL(origin);
  if(url.protocol!=='https:' || url.origin!==origin || typeof allowPeer!=='function')
    throw new Error('Expected a dedicated HTTPS origin and peer allowlist');
  const server=createServer({key,cert,minVersion:'TLSv1.2'},(req,res)=>{
    if(!allowPeer(req.socket.remoteAddress) || req.headers.host!==url.host ||
      (req.headers.origin && req.headers.origin!==origin)) return end(res,403);
    if(!req.url?.startsWith('/') || req.url.startsWith('//') || /[\\\\]/.test(req.url) ||
      /%(?:2f|5c|2e)/i.test(req.url.split('?')[0])) return end(res,403);
    // Webhook endpoints are not part of the initial private interactive deployment.
    const pathname=new URL(req.url,origin).pathname;
    if(pathname==='/api/webhooks' || pathname.startsWith('/api/webhooks/')) return end(res,403);
    const headers=cleanHeaders(req.headers);
    // Forward the validated original authority. Never add credentials.
    headers.host=url.host;
    const upstream=request({hostname:'127.0.0.1',port:4310,path:req.url,
      method:req.method,headers},reply=>{
      res.writeHead(reply.statusCode,cleanHeaders(reply.headers));
      reply.pipe(res);
      reply.on('error',()=>res.destroy());
    });
    upstream.on('error',()=>{if(!res.headersSent)end(res,502);else res.destroy();});
    req.on('aborted',()=>upstream.destroy());
    res.on('close',()=>{if(!res.writableEnded)upstream.destroy();});
    req.pipe(upstream);
  });
  server.headersTimeout=10000;
  server.requestTimeout=120000;
  server.maxHeadersCount=64;
  server.on('upgrade',(_req,socket)=>socket.destroy());
  return server;
}
