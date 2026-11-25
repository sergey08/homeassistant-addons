// Experimental transport: TLS 1.2 ECDHE-PSK, no certificate/CA provisioning,
// no plaintext fallback, no Docker socket, and only the upstream worker socket.
// The same independently generated 256-bit PSK must be provisioned on both apps.
import tls from 'node:tls';
import net from 'node:net';
import {pathToFileURL} from 'node:url';
import {readFileSync} from 'node:fs';

const identity='nod-ha-workspace-v1';
const cipher='ECDHE-PSK-CHACHA20-POLY1305';
const tlsOptions={minVersion:'TLSv1.2',maxVersion:'TLSv1.2',ciphers:cipher};
export function parsePsk(value){
  if(typeof value!=='string'||!/^([a-f0-9]{64})$/.test(value)||/^0{64}$/.test(value))
    throw Error('Workspace transport requires a random 256-bit hexadecimal key');
  return Buffer.from(value,'hex');
}
function negotiated(socket){
  return socket.getProtocol()==='TLSv1.2'&&socket.getCipher()?.name===cipher;
}
export function createGateway({psk,socketPath='/run/nod-workspace/control.sock',maxConnections=4}){
  const key=parsePsk(psk);
  const connections=new Set();
  const server=tls.createServer({
    ...tlsOptions,handshakeTimeout:5000,
    pskCallback:(_socket,provided)=>provided===identity?key:null,
  },socket=>{
    if(!negotiated(socket)||connections.size>=maxConnections)return socket.destroy();
    connections.add(socket);
    const worker=net.connect(socketPath);
    const stop=()=>{socket.destroy();worker.destroy();};
    socket.on('error',stop);worker.on('error',stop);
    socket.on('close',()=>{connections.delete(socket);worker.destroy();});
    worker.on('close',()=>{if(!worker.readableEnded)socket.destroy();});
    socket.setTimeout(20000,stop);
    socket.pipe(worker);
    worker.pipe(socket);
  });
  server.on('tlsClientError',(_err,socket)=>socket.destroy());
  return server;
}
export function connectGateway({psk,host,port=9593}){
  const key=parsePsk(psk);
  // No X.509 certificates are used; the TLS handshake authenticates the
  // remote peer by proof of the PSK. Only the exact ECDHE-PSK cipher is accepted.
  const socket=tls.connect({...tlsOptions,host,port,rejectUnauthorized:false,
    pskCallback:()=>({psk:key,identity})});
  const timer=setTimeout(()=>socket.destroy(Error('Workspace handshake timed out')),6000);
  timer.unref();
  socket.once('secureConnect',()=>{
    clearTimeout(timer);
    if(!negotiated(socket))socket.destroy(Error('Unexpected workspace TLS parameters'));
  });
  socket.once('close',()=>clearTimeout(timer));
  return socket;
}
export async function runClient({psk,host,port,input=process.stdin,output=process.stdout}){
  const socket=connectGateway({psk,host,port});
  return new Promise(resolve=>{
    let done=false;
    const finish=code=>{
      if(done)return;
      done=true;
      input.unpipe(socket);
      input.pause();
      socket.destroy();
      resolve(code);
    };
    socket.on('error',()=>finish(1));
    socket.on('close',hadError=>finish(hadError?1:0));
    input.on('error',()=>finish(1));
    output.on('error',()=>finish(1));
    socket.once('secureConnect',()=>{
      if(!negotiated(socket))return finish(1);
      input.pipe(socket);
      socket.pipe(output,{end:false});
    });
  });
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  try{
    const mode=process.argv[2];
    // Secrets are read from an owner-controlled file, never CLI arguments.
    const config=JSON.parse(readFileSync(process.argv[3],'utf8'));
    if(mode==='gateway'){
      const gateway=createGateway({psk:config.psk});
      gateway.listen(9593,'0.0.0.0',()=>console.log('NOD_WORKSPACE_TRANSPORT_READY'));
      gateway.on('error',()=>{console.error('Workspace transport unavailable');process.exit(1);});
    }else if(mode==='client'){
      if(typeof config.host!=='string'||!/^[a-zA-Z0-9.-]+$/.test(config.host))throw Error();
      process.exitCode=await runClient({psk:config.psk,host:config.host,port:9593});
      process.stdin.destroy();
    }else throw Error();
  }catch{
    console.error('Workspace transport configuration or startup failed');
    process.exitCode=1;
  }
}
