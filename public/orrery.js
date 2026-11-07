
'use strict';
const canvas=document.getElementById('c'),ctx=canvas.getContext('2d'),seek=document.getElementById('seek'),play=document.getElementById('play'),reset=document.getElementById('reset'),speed=document.getElementById('speed'),clock=document.getElementById('clock'),stage=document.getElementById('stage'),read=document.getElementById('read');
let W=0,H=0,dpr=1,t=0,running=false,last=0;
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),smooth=(a,b,x)=>{let u=clamp((x-a)/(b-a));return u*u*(3-2*u)};
function resize(){dpr=Math.min(devicePixelRatio||1,2);W=innerWidth;H=innerHeight;canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0)}addEventListener('resize',resize);resize();
function rot(p,ay,ax){let [x,y,z]=p,c=Math.cos(ay),s=Math.sin(ay);[x,z]=[x*c+z*s,-x*s+z*c];c=Math.cos(ax);s=Math.sin(ax);return [x,y*c-z*s,y*s+z*c]}
function proj(p){let q=rot(p,t*.12+.3,-.27+Math.sin(t*.035)*.1),persp=4.4/(4.4+q[2]);let sc=Math.min(W*.24,H*.35);return [W*.52+q[0]*sc*persp,H*.51-q[1]*sc*persp,persp]}
function line(a,b,color,width=1,alpha=1){let A=proj(a),B=proj(b);ctx.strokeStyle=color;ctx.globalAlpha=alpha;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);ctx.stroke();ctx.globalAlpha=1}
function dot(p,r,col,glow=0){let [x,y,k]=proj(p);ctx.beginPath();ctx.arc(x,y,r*k,0,Math.PI*2);ctx.fillStyle=col;ctx.shadowBlur=glow;ctx.shadowColor=col;ctx.fill();ctx.shadowBlur=0}
function label(p,s,color='#b5e4ee'){let q=proj(p);ctx.fillStyle=color;ctx.font='11px ui-monospace,monospace';ctx.fillText(s,q[0]+7,q[1]-8)}
function cube(a,alpha){let v=[];for(let x of [-a,a])for(let y of [-a,a])for(let z of [-a,a])v.push([x,y,z]);for(let i=0;i<8;i++)for(let j=i+1;j<8;j++){let diff=0;for(let k=0;k<3;k++)diff+=v[i][k]!==v[j][k]?1:0;if(diff===1)line(v[i],v[j],'#6ce7f5',1.25,alpha)} }
function sphere(R,alpha){for(let lat=-4;lat<=4;lat++){let phi=lat*Math.PI/10;let r=R*Math.cos(phi),y=R*Math.sin(phi);for(let j=0;j<72;j++){let a=j*Math.PI/36,b=(j+1)*Math.PI/36;line([r*Math.cos(a),y,r*Math.sin(a)],[r*Math.cos(b),y,r*Math.sin(b)],'#3eb3c8',.75,alpha*.65)}}for(let mer=0;mer<12;mer++){let a=mer*Math.PI/6;for(let j=0;j<48;j++){let u=-Math.PI/2+j*Math.PI/48,v=u+Math.PI/48;line([R*Math.cos(u)*Math.cos(a),R*Math.sin(u),R*Math.cos(u)*Math.sin(a)],[R*Math.cos(v)*Math.cos(a),R*Math.sin(v),R*Math.cos(v)*Math.sin(a)],'#59cbdc',.75,alpha*.65)}}}
const names=['TAP','SURFACE','GAIN','HABITAT','ENGINE','BUSINESS'];const axes=[[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];
function loads(time){let agreement=smooth(27,43,time);return axes.map((_,i)=>.52+(1-agreement)*(.20*Math.sin(time*.31+i*1.73)+.07*Math.cos(time*.19+i)) + agreement*.002*Math.sin(time*.7+i))}
function grid(){let extent=5;for(let k=-extent;k<=extent;k++){line([-extent,-1.65,k],[extent,-1.65,k],'#1a4557',.6,.35);line([k,-1.65,-extent],[k,-1.65,extent],'#1a4557',.6,.35)}}
function temporal(alpha){let n=110;for(let j=0;j<n;j++){let u=j/n,v=(j+1)/n;let past=u=>[-1.1-2*u, .12*Math.sin(u*13),-.15-u*.6];line(past(u),past(v),'#eab36e',1.5,alpha*(1-u*.5));let future=u=>[1.1+2.2*u,.27*Math.sin(13*u)*Math.exp(-u),.2*Math.cos(11*u)];let fragmentation=Math.exp(-2.2*u);line(future(u),future(v),u>.73?'#e27b76':'#f0a15b',1.5,alpha*fragmentation)} }
function melt(alpha){let N=20;for(let i=0;i<N;i++)for(let j=0;j<N;j++){let u=i/N,v=j/N;let rad=1.4+1.8*u;let decay=Math.exp(-2.4*u);let wave=Math.sin(17*v+u*11+t*.12);let p=[1.2+rad*u, (v-.5)*1.5*decay+wave*.13*u,Math.sin(v*12+t*.05)*.4*u];let q=[p[0]+.055,p[1]+.03*decay,p[2]+.02];line(p,q,'#e99b65',1,alpha*decay)}}
function draw(){ctx.fillStyle='#030a14';ctx.fillRect(0,0,W,H);let bg=ctx.createRadialGradient(W*.52,H*.52,20,W*.52,H*.52,Math.max(W,H)*.6);bg.addColorStop(0,'#10263a');bg.addColorStop(1,'#030a14');ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);grid();let born=smooth(8,17,t),conv=smooth(28,45,t),sphereA=smooth(43,58,t),cubeA=born*(1-smooth(48,70,t));if(cubeA>.001)cube(1.15,cubeA);let L=loads(t),D=Math.max(...L)-Math.min(...L),valid=D<=.01 && t>=43;
if(t<13){let r=Math.max(0,(t-1)*.2);for(let i=0;i<4;i++){let a=r-i*.32;if(a>0)for(let j=0;j<80;j++){let th=j*Math.PI/40,th2=(j+1)*Math.PI/40;line([a*Math.cos(th),a*Math.sin(th),0],[a*Math.cos(th2),a*Math.sin(th2),0],'#eebd78',1,.35)}}}
if(born>0&&sphereA<.99){axes.forEach((a,i)=>{let k=1.15,from=a.map(v=>v*k),to=a.map(v=>v*(1.15-conv*1.15));line(from,to,i%2?'#6bd7eb':'#e7ae60',2,born*(1-sphereA));dot(to,2.5,'#fff',0)})}
if(sphereA>0){sphere(1.05,sphereA);axes.forEach((a,i)=>{let oscill=.11*Math.sin(t*.55+i*1.1),len=1.5+.35*L[i]+oscill;let p=a.map(v=>v*1.05),q=a.map(v=>v*len);line(p,q,'#efb56c',2.4,sphereA);dot(q,3.3,'#f7c985',10*sphereA);if(W>650)label(q,names[i],'#b3dce4')});let pulse=(Math.sin(t*2.6)+1)*.5;dot([0,0,0],4+pulse*3,'#fff',15)}
if(t>65){let a=smooth(65,75,t);temporal(a);melt(a);dot([-3.1,0,-.75],3,'#fff',8)}
if(t<43)dot([0,0,0],3+t*.025,'#fff',16);
let s=t<12?'I · SENTINEL':t<27?'II · SIX-FACED CUBE':t<45?'III · CONVERGENCE':t<65?'IV · SPHERE':t<82?'V · SCRIPTED TEMPORAL ILLUSTRATION':'VI · CONCEPTUAL DECOMPOSITION';stage.textContent=s;read.innerHTML='t = '+t.toFixed(2)+' s<br>LOAD SPREAD D = '+D.toFixed(5)+'<br>TOLERANCE ε = 0.01000<br>SCRIPTED ALIGNMENT = '+(valid?'ILLUSTRATIVE TOLERANCE MET':'SCRIPTED APPROACH')+'<br>GATE = CLOSED · SYNTHETIC<br>CENTRE = [1024,1024,0]';clock.textContent=t.toFixed(1)+'s';seek.value=t.toFixed(2)}
let animation=null;
function frame(now){if(!running)return;if(!last)last=now;const dt=Math.min((now-last)/1000,.08);last=now;t=Math.min(110,t+dt*Number(speed.value));draw();if(t<110)animation=requestAnimationFrame(frame);else stop();}
function stop(){running=false;if(animation!==null)cancelAnimationFrame(animation);animation=null;last=0;play.textContent='Play';}
function start(){if(running)return;running=true;last=0;play.textContent='Pause';animation=requestAnimationFrame(frame);}
play.onclick=()=>running?stop():start();reset.onclick=()=>{stop();t=0;draw();};seek.oninput=()=>{stop();t=Number(seek.value);draw();};
addEventListener('resize',draw);addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
canvas.tabIndex=0;canvas.setAttribute('aria-label','Scripted synthetic Orrery illustration. Space plays or pauses. Timeline is scenario time, not recorded history.');
canvas.onkeydown=e=>{if(e.code==='Space'){e.preventDefault();running?stop():start();}};draw();
