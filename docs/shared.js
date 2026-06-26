/* ── Mandi Intel — Shared JavaScript ─────────────────────────── */

/* 1. WebGL Shader Background */
function initShader() {
  const canvas = document.getElementById('shader-bg');
  if (!canvas) return;
  function syncSize() {
    const w = canvas.clientWidth || 1280;
    const h = canvas.clientHeight || 720;
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(syncSize).observe(canvas);
  syncSize();
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) return;
  const vs = `attribute vec2 a_position;
varying vec2 v_texCoord;
void main(){v_texCoord=a_position*0.5+0.5;gl_Position=vec4(a_position,0.0,1.0);}`;
  const fs = `precision highp float;
varying vec2 v_texCoord;
uniform float u_time;
void main(){
  vec2 uv=v_texCoord;
  vec3 c=vec3(0.031,0.047,0.078);
  vec2 p1=vec2(0.5+0.3*cos(u_time*0.2),0.5+0.2*sin(u_time*0.3));
  float d1=length(uv-p1);
  c+=vec3(0.95,0.63,0.38)*(0.08/(d1+0.4))*smoothstep(0.6,0.0,d1);
  vec2 p2=vec2(0.5+0.3*sin(u_time*0.25),0.5+0.3*cos(u_time*0.15));
  float d2=length(uv-p2);
  c+=vec3(0.16,0.61,0.56)*(0.08/(d2+0.5))*smoothstep(0.7,0.0,d2);
  vec2 p3=vec2(0.2+0.4*cos(u_time*0.1),0.8+0.3*sin(u_time*0.2));
  float d3=length(uv-p3);
  c+=vec3(0.38,0.71,0.79)*(0.06/(d3+0.4))*smoothstep(0.5,0.0,d3);
  float n=fract(sin(dot(uv,vec2(12.9898,78.233)))*43758.5453);
  c+=n*0.015;
  vec2 g=fract(uv*40.0);
  float dots=smoothstep(0.05,0.0,length(g-0.5));
  c+=dots*0.02;
  gl_FragColor=vec4(c,1.0);
}`;
  function cs(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);return s;}
  const prog=gl.createProgram();
  gl.attachShader(prog,cs(gl.VERTEX_SHADER,vs));
  gl.attachShader(prog,cs(gl.FRAGMENT_SHADER,fs));
  gl.linkProgram(prog);gl.useProgram(prog);
  const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
  const pos=gl.getAttribLocation(prog,'a_position');
  gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
  const uTime=gl.getUniformLocation(prog,'u_time');
  const uRes=gl.getUniformLocation(prog,'u_resolution');
  function render(t){
    if(typeof ResizeObserver==='undefined')syncSize();
    gl.viewport(0,0,canvas.width,canvas.height);
    if(uTime)gl.uniform1f(uTime,t*0.001);
    if(uRes)gl.uniform2f(uRes,canvas.width,canvas.height);
    gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
    requestAnimationFrame(render);
  }
  render(0);
}

/* 2. Scroll-Reveal Observer */
function initReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        entry.target.querySelectorAll('.counter').forEach(animateCounter);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

/* 3. Animated Counters */
function animateCounter(el) {
  if (el.dataset.done) return;
  el.dataset.done = '1';
  const target = parseFloat(el.dataset.target);
  const suffix = el.dataset.suffix || '';
  const prefix = el.dataset.prefix || '';
  const decimals = (el.dataset.decimals || '0') | 0;
  const duration = 2000;
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = target * ease;
    el.textContent = prefix + current.toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* 4. Mobile Nav Toggle */
function initMobileNav() {
  const btn = document.getElementById('nav-toggle');
  const menu = document.getElementById('mobile-menu');
  const close = document.getElementById('nav-close');
  if (!btn || !menu) return;
  btn.addEventListener('click', () => menu.classList.add('open'));
  if (close) close.addEventListener('click', () => menu.classList.remove('open'));
  menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => menu.classList.remove('open')));
}

/* 5. Init All */
document.addEventListener('DOMContentLoaded', () => {
  initShader();
  initReveal();
  initMobileNav();
});
