// Fixed public probe, deliberately no page text, addresses or secrets in logs.
// Run only when remote access is configured. It does not control the worker.
import {Resolver,lookup} from 'node:dns/promises';
import tls from 'node:tls';
const deadline=setTimeout(()=>{console.log('NOD_BROWSER_EGRESS_PROBE_TIMEOUT');process.exit(1)},18000);
try{
  try{
    await Promise.race([lookup('example.com',{family:4}),new Promise((_,reject)=>setTimeout(()=>reject(Error()),3000))]);
    console.log('NOD_BROWSER_SYSTEM_DNS_OK');
  }catch{console.log('NOD_BROWSER_SYSTEM_DNS_FAILED');}
  const dns=new Resolver({timeout:2500,tries:2});
  dns.setServers(['1.1.1.1','8.8.8.8']);
  let addresses;
  try{
    addresses=await dns.resolve4('example.com');
    if(!addresses.length)throw Error();
    console.log('NOD_BROWSER_PUBLIC_DNS_OK');
  }catch{console.log('NOD_BROWSER_PUBLIC_DNS_FAILED');process.exit(1);}
  try{
    await new Promise((resolve,reject)=>{
      const socket=tls.connect({host:addresses[0],port:443,servername:'example.com',rejectUnauthorized:true});
      socket.setTimeout(5000,()=>{socket.destroy();reject(Error());});
      socket.once('secureConnect',()=>{socket.destroy();resolve();});
      socket.once('error',reject);
    });
    console.log('NOD_BROWSER_PUBLIC_HTTPS_OK');
  }catch{console.log('NOD_BROWSER_PUBLIC_HTTPS_FAILED');process.exitCode=1;}
}finally{clearTimeout(deadline);}
