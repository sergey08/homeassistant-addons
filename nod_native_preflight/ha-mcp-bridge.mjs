// Fixed destination adapter: Nod's encrypted bearer credential is HA-MCP's secret path.
import {createServer,request} from 'node:http';
import {pathToFileURL} from 'node:url';
const target='81f33d0f-ha-mcp';
const port=9583;
const allowed=['accept','content-type','mcp-session-id','mcp-protocol-version','last-event-id'];
const maxBody=8*1024*1024;
export function createHaMcpBridge({upstreamHost=target,upstreamPort=port}={}){
  return createServer((req,res)=>{
    const reject=(code)=>{res.writeHead(code,{'Cache-Control':'no-store','Content-Type':'text/plain'});res.end('HA MCP adapter rejected request');};
    if(req.socket.remoteAddress!=='127.0.0.1'||!/^127\.0\.0\.1:\d+$/.test(req.headers.host||'')||req.url!=='/mcp'||!['GET','POST','DELETE'].includes(req.method)||req.headers.origin||req.headers.upgrade){reject(403);return;}
    const match=/^Bearer \/?([A-Za-z0-9_-]{16,256})$/.exec(req.headers.authorization||'');
    if(!match){reject(401);return;}
    if(Number(req.headers['content-length']||0)>maxBody){reject(413);return;}
    const headers=Object.fromEntries(allowed.filter(k=>typeof req.headers[k]==='string').map(k=>[k,req.headers[k]]));
    // Buffer bounded JSON requests; do not send a truncated tool call upstream.
    let size=0, chunks=[];
    req.on('data',chunk=>{
      size+=chunk.length;
      if(size>maxBody){chunks=[];if(!res.headersSent)reject(413);return;}
      chunks.push(chunk);
    });
    req.on('error',()=>{if(!res.headersSent)reject(400);});
    req.on('end',()=>{
      if(res.headersSent||size>maxBody)return;
      if(size)headers['content-length']=String(size);
      const out=request({hostname:upstreamHost,port:upstreamPort,path:'/'+match[1],method:req.method,headers},incoming=>{
        // No redirect following, cookie forwarding or error-body exposure.
        const code=incoming.statusCode||502;
        if(code<200||code>=300){incoming.resume();reject(code>=300&&code<400?502:code);return;}
        const h=Object.fromEntries(['content-type','mcp-session-id','mcp-protocol-version','cache-control'].filter(k=>typeof incoming.headers[k]==='string').map(k=>[k,incoming.headers[k]]));
        h['cache-control']='no-store';
        res.writeHead(code,h);incoming.pipe(res);
        incoming.on('error',()=>res.destroy());
        res.on('close',()=>incoming.destroy());
      });
      out.setTimeout(600000,()=>out.destroy());
      out.on('error',()=>{if(!res.headersSent)reject(502);else res.destroy();});
      res.on('close',()=>out.destroy());
      out.end(Buffer.concat(chunks));
    });
  });
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const server=createHaMcpBridge();
  server.listen(9591,'127.0.0.1',()=>console.log('NOD_NATIVE_HA_MCP_BRIDGE_LISTENING'));
}
